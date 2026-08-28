"""P20 RRHH clínico y costeo."""
from datetime import datetime, timezone
import re
import unicodedata
from uuid import uuid4

import pandas as pd

from nucleo.utilidades.ParquetStore import ParquetStore

EMPLEADO_COLUMNAS = [
    "id_empleado", "codigo", "nombre", "apellido", "documento", "email",
    "telefono", "cargo", "area", "sede", "fecha_ingreso", "estado_laboral",
    "rol_sugerido", "estado_cuenta", "creado_en", "actualizado_en",
]
empleados = ParquetStore(
    "rrhh/empleados.parquet", EMPLEADO_COLUMNAS, "id_empleado", "empleados",
    modo_borrado="estado_laboral", valor_anulado="desvinculado",
)

cargos = ParquetStore(
    "negocio/dim_cargo.parquet",
    ["id_cargo", "nombre", "activo", "creado_en", "actualizado_en"],
    "id_cargo", "cargos", modo_borrado="activo",
)
turnos = ParquetStore(
    "negocio/dim_turno.parquet",
    ["id_turno", "nombre", "hora_inicio", "hora_fin", "activo", "creado_en", "actualizado_en"],
    "id_turno", "turnos", modo_borrado="activo",
)
personal = ParquetStore(
    "negocio/oper_personal_costo.parquet",
    ["id_personal_costo", "id_personal", "id_cargo", "costo_hora", "fecha_vigencia",
     "activo", "creado_en", "actualizado_en"],
    "id_personal_costo", "personal", modo_borrado="activo",
)
bridge_turno = ParquetStore(
    "negocio/bridge_personal_turno.parquet",
    ["id_bridge", "id_personal", "id_turno", "fecha", "activo", "creado_en", "actualizado_en"],
    "id_bridge", "asignaciones", modo_borrado="activo",
)
productividad = ParquetStore(
    "negocio/agg_productividad_medica.parquet",
    ["id_agg", "id_personal", "periodo", "num_consultas", "num_procedimientos",
     "ingreso_generado", "creado_en", "actualizado_en"],
    "id_agg", "productividad", modo_borrado="activo",
)

def _texto(valor) -> str:
    if valor is None or pd.isna(valor):
        return ""
    return str(valor).strip()


def _clave(valor) -> str:
    texto = unicodedata.normalize("NFKD", _texto(valor).lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def sugerir_rol(cargo: str, area: str = "") -> str:
    texto = f"{_clave(cargo)} {_clave(area)}"
    reglas = (
        (("administrador", "direccion", "gerencia", "rrhh", "recepcion"), "administrador"),
        (("farmacia", "farmaceut"), "farmaceutico"),
        (("enfermer", "auxiliar de enfer"), "enfermero"),
        (("medic", "doctor", "endocrin", "diabetolog"), "medico"),
        (("analista", "estadistica", "datos", "laboratorio"), "analista"),
    )
    for palabras, rol in reglas:
        if any(p in texto for p in palabras):
            return rol
    return "pendiente_revision"


def listar_empleados(offset: int = 0, limit: int = 100) -> dict:
    return empleados.listar(offset, limit, incluir_inactivos=True)


def resumen_empleados() -> dict:
    filas = empleados.extraer().to_dict(orient="records")
    return {
        "total": len(filas),
        "activos": sum(_clave(f.get("estado_laboral")) == "activo" for f in filas),
        "sin_cuenta": sum(_clave(f.get("estado_cuenta")) == "sin_cuenta" for f in filas),
        "roles_por_revisar": sum(_clave(f.get("rol_sugerido")) == "pendiente_revision" for f in filas),
    }


def _validar_empleado(datos: dict, id_actual: str = "") -> dict:
    limpio = {k: _texto(v) for k, v in datos.items()}
    if not limpio.get("codigo") or not limpio.get("nombre"):
        return {"error": "Código y nombre son obligatorios"}
    email = limpio.get("email", "").lower()
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return {"error": "El correo no es válido"}
    for fila in empleados.extraer().to_dict(orient="records"):
        if str(fila.get("id_empleado")) == str(id_actual):
            continue
        if _clave(fila.get("codigo")) == _clave(limpio["codigo"]):
            return {"error": "Ya existe un empleado con ese código"}
        if email and _clave(fila.get("email")) == _clave(email):
            return {"error": "Ya existe un empleado con ese correo"}
    limpio["email"] = email
    limpio["estado_laboral"] = limpio.get("estado_laboral") or "activo"
    limpio["rol_sugerido"] = limpio.get("rol_sugerido") or sugerir_rol(
        limpio.get("cargo", ""), limpio.get("area", "")
    )
    return limpio


def crear_empleado(datos: dict) -> dict:
    limpio = _validar_empleado(datos)
    if limpio.get("error"):
        return limpio
    limpio["estado_cuenta"] = "sin_cuenta"
    return empleados.crear(limpio)


def actualizar_empleado(id_empleado: str, datos: dict) -> dict:
    limpio = _validar_empleado(datos, id_empleado)
    if limpio.get("error"):
        return limpio
    limpio.pop("estado_cuenta", None)
    resultado = empleados.actualizar(id_empleado, limpio)
    if not resultado.get("error") and limpio.get("estado_laboral") in ("inactivo", "desvinculado"):
        try:
            from paquetes.usuarios.UsuariosServicio import desactivar_usuario, obtener_usuarios
            email = limpio.get("email", "").lower()
            usuario = next((u for u in obtener_usuarios() if str(u.get("email", "")).lower() == email), None)
            if usuario:
                desactivar_usuario(str(usuario["id"]))
                empleados.actualizar(id_empleado, {"estado_cuenta": "suspendida"})
        except Exception:
            pass
    return resultado


def provisionar_empleados(ids: list[str], actor: str) -> dict:
    """Crea solo las cuentas seleccionadas y nunca expone contraseñas."""
    if not ids:
        return {"error": "Seleccione al menos un empleado"}
    if len(ids) > 100:
        return {"error": "Máximo 100 empleados por lote"}
    from paquetes.autenticacion.SolicitudesAccesoServicio import _enviar_credenciales, _password_temporal
    from paquetes.usuarios.UsuariosServicio import (
        crear_usuario, obtener_usuarios, restablecer_password_temporal_por_email,
    )

    df = empleados.extraer()
    existentes = {str(u.get("email", "")).lower() for u in obtener_usuarios()}
    creadas = enviadas = 0
    errores = []
    roles = {"administrador", "medico", "enfermero", "farmaceutico", "analista"}
    for id_empleado in dict.fromkeys(ids):
        idx = df.index[df["id_empleado"].astype(str) == str(id_empleado)].tolist()
        if not idx:
            errores.append({"id": id_empleado, "error": "Empleado no encontrado"}); continue
        i = idx[0]
        fila = df.loc[i]
        email = _texto(fila.get("email")).lower()
        rol = _texto(fila.get("rol_sugerido")).lower()
        if _clave(fila.get("estado_laboral")) != "activo":
            errores.append({"id": id_empleado, "error": "El empleado no está activo"}); continue
        if not email or rol not in roles:
            errores.append({"id": id_empleado, "error": "Revise el correo y el rol"}); continue
        if email in existentes:
            if _clave(fila.get("estado_cuenta")) == "pendiente_envio":
                password = _password_temporal()
                reset = restablecer_password_temporal_por_email(email, password)
                if reset.get("error"):
                    errores.append({"id": id_empleado, "error": reset["error"]}); continue
                envio = _enviar_credenciales(email, _texto(fila.get("nombre")), password, rol)
                if envio.get("ok"):
                    enviadas += 1
                    df.at[i, "estado_cuenta"] = "activa"
                else:
                    errores.append({"id": id_empleado, "error": envio.get("error") or "No se envió el correo"})
            else:
                df.at[i, "estado_cuenta"] = "activa"
            continue
        password = _password_temporal()
        creado = crear_usuario(
            f"{_texto(fila.get('nombre'))} {_texto(fila.get('apellido'))}".strip(),
            email, password, rol, debe_cambiar_password=True,
        )
        if creado.get("error"):
            errores.append({"id": id_empleado, "error": creado["error"]}); continue
        creadas += 1
        envio = _enviar_credenciales(email, _texto(fila.get("nombre")), password, rol)
        if envio.get("ok"):
            enviadas += 1
            df.at[i, "estado_cuenta"] = "activa"
        else:
            df.at[i, "estado_cuenta"] = "pendiente_envio"
            errores.append({"id": id_empleado, "error": envio.get("error") or "No se envió el correo"})
        df.at[i, "actualizado_en"] = datetime.now(timezone.utc).isoformat()
        existentes.add(email)
    empleados.cargar(df.reindex(columns=EMPLEADO_COLUMNAS))
    empleados.auditar(actor, "provision", f"Cuentas: {creadas}; correos: {enviadas}", "rrhh")
    return {"seleccionados": len(ids), "cuentas_creadas": creadas, "correos_enviados": enviadas,
            "errores": errores, "fallidos": len(errores)}


def crear_asignacion(datos: dict) -> dict:
    if not empleados.obtener(str(datos.get("id_personal", ""))).get("id_empleado"):
        return {"error": "Empleado no encontrado"}
    if not turnos.obtener(str(datos.get("id_turno", ""))).get("id_turno"):
        return {"error": "Turno no encontrado"}
    existentes = bridge_turno.extraer()
    if not existentes.empty:
        duplicada = existentes[
            (existentes["id_personal"].astype(str) == str(datos.get("id_personal")))
            & (existentes["fecha"].astype(str) == str(datos.get("fecha")))
            & (existentes["activo"].astype(str).str.lower().isin(["true", "1", "si", "sí"]))
        ]
        if not duplicada.empty:
            return {"error": "El empleado ya tiene un turno asignado en esa fecha"}
    return bridge_turno.crear(datos)


def importar_empleados(filas: list[dict]) -> dict:
    """Crea o actualiza el directorio; no crea cuentas ni credenciales."""
    df = empleados.extraer()
    ahora = datetime.now(timezone.utc).isoformat()
    creados = actualizados = 0
    errores = []
    por_codigo = {_clave(r.get("codigo")): i for i, r in df.iterrows() if _clave(r.get("codigo"))}
    por_email = {_clave(r.get("email")): i for i, r in df.iterrows() if _clave(r.get("email"))}

    for numero, origen in enumerate(filas, start=2):
        fila = {_clave(k).replace(" ", "_"): _texto(v) for k, v in origen.items()}
        alias = {
            "correo_institucional": "email", "fecha_de_ingreso": "fecha_ingreso",
            "estado_laboral": "estado_laboral", "rol_sugerido": "rol_sugerido",
        }
        for visible, tecnico in alias.items():
            if visible in fila and tecnico not in fila:
                fila[tecnico] = fila[visible]
        codigo, nombre, email = fila.get("codigo", ""), fila.get("nombre", ""), fila.get("email", "")
        if not codigo or not nombre:
            errores.append({"fila": numero, "error": "codigo y nombre son obligatorios"})
            continue
        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            errores.append({"fila": numero, "error": "email no válido"})
            continue
        datos = {col: fila.get(col, "") for col in EMPLEADO_COLUMNAS}
        datos.update({
            "codigo": codigo, "nombre": nombre, "email": email.lower(),
            "estado_laboral": fila.get("estado_laboral") or "activo",
            "rol_sugerido": fila.get("rol_sugerido") or sugerir_rol(fila.get("cargo", ""), fila.get("area", "")),
            "actualizado_en": ahora,
        })
        indice = por_codigo.get(_clave(codigo))
        if indice is None and email:
            indice = por_email.get(_clave(email))
        if indice is None:
            datos.update({"id_empleado": str(uuid4()), "estado_cuenta": "sin_cuenta", "creado_en": ahora})
            df = pd.concat([df, pd.DataFrame([datos])], ignore_index=True)
            indice = len(df) - 1
            creados += 1
        else:
            for col, valor in datos.items():
                if col not in ("id_empleado", "creado_en", "estado_cuenta"):
                    df.at[indice, col] = valor
            actualizados += 1
        por_codigo[_clave(codigo)] = indice
        if email:
            por_email[_clave(email)] = indice

    if creados or actualizados:
        empleados.cargar(df.reindex(columns=EMPLEADO_COLUMNAS))
    return {
        "recibidos": len(filas), "creados": creados, "actualizados": actualizados,
        "rechazados": len(errores), "errores": errores[:50],
    }

def seed():
    if not (cargos.listar(limit=1).get("cargos") or []):
        for n in ["medico_general", "endocrinologo", "enfermero", "farmaceutico", "administrativo"]:
            cargos.crear({"nombre": n, "activo": True})
    if not (turnos.listar(limit=1).get("turnos") or []):
        for n, hi, hf in [("mañana", "07:00", "15:00"), ("tarde", "15:00", "23:00"), ("noche", "23:00", "07:00")]:
            turnos.crear({"nombre": n, "hora_inicio": hi, "hora_fin": hf, "activo": True})

def costeo() -> dict:
    return personal.listar(limit=200, incluir_inactivos=True)

def productividad_resumen() -> dict:
    return productividad.listar(limit=200, incluir_inactivos=True)


def resumen_operativo() -> dict:
    """Informe simple: personal costeado, turnos y actividad del periodo."""
    _tope = 10**9
    per = personal.listar(limit=_tope, incluir_inactivos=True).get("personal") or []
    asg = bridge_turno.listar(limit=_tope, incluir_inactivos=True).get("asignaciones") or []
    prod = productividad.listar(limit=_tope, incluir_inactivos=True).get("productividad") or []
    costo_prom = round(sum(float(p.get("costo_hora") or 0) for p in per) / len(per), 2) if per else 0.0
    return {
        "tipo": "informe_simple",
        "personal_costeado": len(per),
        "asignaciones_turno": len(asg),
        "costo_hora_promedio": costo_prom,
        "consultas_periodo": int(sum(int(p.get("num_consultas") or 0) for p in prod)),
        "ingreso_generado": round(sum(float(p.get("ingreso_generado") or 0) for p in prod), 2),
    }
