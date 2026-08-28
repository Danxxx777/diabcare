import uuid
import pandas as pd
from datetime import datetime
from nucleo.utilidades.ParquetCache import leer, escribir
from nucleo.utilidades.Validaciones import rango_fechas_ok

BUCKET_APP = "diabcare-app"
ARCHIVO = "operativo/admisiones.parquet"
COLUMNAS = [
    "id_admision", "id_paciente", "paciente_nombre", "documento", "tipo", "via_llegada",
    "servicio",
    "medico_id", "medico_nombre", "sede", "habitacion", "estado", "motivo",
    "fecha_ingreso", "fecha_egreso", "notas", "creado_en", "actualizado_en",
]
ESTADOS = {"programada", "activa", "alta", "cancelada"}
TIPOS = {"ambulatoria", "urgencia", "hospitalizacion"}
VIAS = {"propia", "ambulancia", "referido"}
CAMAS = [f"H-{piso}{numero:02d}" for piso in (1, 2) for numero in range(1, 7)]


def listar_camas() -> dict:
    df = _extraer(copiar=False)
    ocupadas = {}
    por_admision = {}
    try:
        from paquetes.instrumental import InstrumentalServicio as instrumental
        for item in instrumental.listar(limit=500, estado="asignado").get("instrumentos", []):
            aid = str(item.get("id_admision") or "")
            if aid:
                por_admision.setdefault(aid, []).append(str(item.get("nombre") or item.get("codigo") or "Equipo"))
    except Exception:
        pass
    fuera_catalogo = 0
    if not df.empty:
        activas = df[(df["estado"].astype(str) == "activa") & df["habitacion"].astype(str).ne("")]
        for _, fila in activas.iterrows():
            codigo = str(fila.get("habitacion") or "").strip()
            if codigo not in CAMAS:
                # Camas historicas o de otra sede: no restan al catalogo local
                fuera_catalogo += 1
                continue
            aid = str(fila.get("id_admision") or "")
            equipos = por_admision.get(aid, [])
            ocupadas[codigo] = {
                "id_admision": aid, "id_paciente": str(fila.get("id_paciente") or ""),
                "paciente": str(fila.get("paciente_nombre") or ""),
                "servicio": str(fila.get("servicio") or ""),
                "medico": str(fila.get("medico_nombre") or ""),
                "dias": _dias_estancia(fila.get("fecha_ingreso")),
                "instrumental_total": len(equipos), "instrumental": equipos,
            }
    camas = [{"codigo": c, "piso": c[2], "estado": "ocupada" if c in ocupadas else "disponible", **ocupadas.get(c, {})} for c in CAMAS]
    return {
        "total": len(camas), "ocupadas": len(ocupadas),
        "disponibles": len(camas) - len(ocupadas),
        "fuera_catalogo": fuera_catalogo, "camas": camas,
    }


def _dias_estancia(fecha_ingreso) -> int:
    texto = str(fecha_ingreso or "")[:10]
    try:
        return max(0, (datetime.now().date() - datetime.strptime(texto, "%Y-%m-%d").date()).days)
    except ValueError:
        return 0


def _validar_cama(datos: dict, df: pd.DataFrame, excluir_id: str = "") -> str:
    tipo = str(datos.get("tipo") or "ambulatoria")
    estado = str(datos.get("estado") or "activa")
    cama = str(datos.get("habitacion") or "").strip()
    # Una hospitalizacion activa SI puede estar sin cama: queda "pendiente de cama"
    # y aparece en la lista de espera del modulo de habitaciones, que es quien
    # asigna. Obligar aqui a elegir cama repartia el flujo entre dos pantallas.
    if cama and tipo != "hospitalizacion":
        return "Solo una hospitalización puede tener una cama asignada"
    if cama and cama not in CAMAS:
        return "La cama seleccionada no pertenece al catálogo"
    if cama and estado == "activa" and not df.empty:
        ocupada = df[(df["estado"].astype(str) == "activa") & (df["habitacion"].astype(str) == cama)]
        if excluir_id:
            ocupada = ocupada[ocupada["id_admision"].astype(str) != str(excluir_id)]
        if not ocupada.empty:
            return f"La cama {cama} ya está ocupada"
    return ""


def _extraer(copiar: bool = True) -> pd.DataFrame:
    df = leer(BUCKET_APP, ARCHIVO, COLUMNAS, copiar=copiar)
    return df if not df.empty else pd.DataFrame(columns=COLUMNAS)


def _cargar(df: pd.DataFrame):
    cols = [c for c in COLUMNAS if c in df.columns]
    escribir(BUCKET_APP, ARCHIVO, df[cols] if cols else df)


def _enriquecer_paciente(datos: dict) -> dict:
    pid = datos.get("id_paciente")
    if not pid:
        return datos
    try:
        from paquetes.clinico.pacientes.PacientesServicio import obtener
        p = obtener(str(pid))
        if "error" not in p:
            datos.setdefault("paciente_nombre", p.get("nombre_completo", ""))
            datos.setdefault("documento", p.get("documento", ""))
    except Exception:
        pass
    return datos


def resumen() -> dict:
    vacio = {"total": 0, "activas": 0, "internados": 0, "altas": 0, "ingresos_hoy": 0}
    df = _extraer(copiar=False)
    if df.empty:
        return vacio
    activas = int((df["estado"] == "activa").sum()) if "estado" in df.columns else 0
    altas = int((df["estado"] == "alta").sum()) if "estado" in df.columns else 0
    internados = int(((df["estado"] == "activa") & (df["tipo"] == "hospitalizacion")).sum()) if "tipo" in df.columns else 0
    hoy = datetime.now().strftime("%Y-%m-%d")
    ingresos_hoy = int(df["fecha_ingreso"].astype(str).str[:10].eq(hoy).sum()) if "fecha_ingreso" in df.columns else 0
    return {
        "total": len(df), "activas": activas, "internados": internados,
        "altas": altas, "ingresos_hoy": ingresos_hoy,
    }


def listar(offset: int = 0, limit: int = 50, estado: str = "", q: str = "", tipo: str = "") -> dict:
    from nucleo.utilidades.Busqueda import rankear_dataframe

    df = _extraer(copiar=False)
    if df.empty:
        return {"total": 0, "admisiones": []}
    if estado:
        df = df[df["estado"] == estado]
    if tipo:
        df = df[df["tipo"] == tipo]
    if q:
        df = rankear_dataframe(
            df, q,
            ["paciente_nombre", "documento", "medico_nombre", "servicio", "tipo", "estado", "motivo", "sede"],
        )
    elif "fecha_ingreso" in df.columns:
        df = df.sort_values("fecha_ingreso", ascending=False)
    total = len(df)
    chunk = df.iloc[offset:offset + limit]
    rows = chunk.fillna("").to_dict(orient="records")
    ids = {str(r.get("id_paciente") or "") for r in rows if r.get("id_paciente")}
    mapa = {}
    if ids:
        try:
            from nucleo.utilidades.PacientesLookup import mapa_pacientes
            mapa = mapa_pacientes(ids)
        except Exception:
            mapa = {}
    out = []
    for r in rows:
        x = dict(r)
        x["id_admision"] = str(x.get("id_admision") or "")
        x["id_paciente"] = str(x.get("id_paciente") or "")
        pid = str(x.get("id_paciente") or "")
        p = mapa.get(pid) or {}
        if p.get("nombre_completo") and not str(x.get("paciente_nombre") or "").strip():
            x["paciente_nombre"] = p["nombre_completo"]
        if p.get("documento") and not str(x.get("documento") or "").strip():
            x["documento"] = p["documento"]
        x["tiene_foto"] = bool(p.get("tiene_foto"))
        out.append(x)
    return {"total": total, "admisiones": out}


def obtener(id_admision: str) -> dict:
    df = _extraer()
    fila = df[df["id_admision"].astype(str) == str(id_admision)]
    if fila.empty:
        return {"error": "Admisión no encontrada"}
    return fila.fillna("").iloc[0].to_dict()


def crear(datos: dict) -> dict:
    datos = _enriquecer_paciente(dict(datos))
    if not datos.get("id_paciente"):
        return {"error": "id_paciente es obligatorio"}
    tipo = str(datos.get("tipo") or "ambulatoria")
    if tipo not in TIPOS:
        return {"error": f"tipo inválido. Use: {', '.join(sorted(TIPOS))}"}
    via = str(datos.get("via_llegada") or "propia").lower()
    if via not in VIAS:
        return {"error": "Vía de llegada inválida. Use: propia, ambulancia o referido."}
    if via == "ambulancia" and tipo == "ambulatoria":
        tipo = "urgencia"
    estado = str(datos.get("estado") or "activa")
    if estado not in ESTADOS:
        return {"error": f"estado inválido. Use: {', '.join(sorted(ESTADOS))}"}
    df = _extraer()
    error_cama = _validar_cama({**datos, "tipo": tipo, "estado": estado}, df)
    if error_cama:
        return {"error": error_cama}
    now = datetime.utcnow().isoformat()
    ingreso = str(datos.get("fecha_ingreso") or now[:10])
    egreso = str(datos.get("fecha_egreso") or "")
    err_f = rango_fechas_ok(ingreso, egreso)
    if err_f:
        return {"error": err_f}
    nuevo = {
        "id_admision": str(uuid.uuid4()),
        "id_paciente": str(datos["id_paciente"]),
        "paciente_nombre": str(datos.get("paciente_nombre") or ""),
        "documento": str(datos.get("documento") or ""),
        "tipo": tipo,
        "via_llegada": via,
        "servicio": str(datos.get("servicio") or "Medicina interna"),
        "medico_id": str(datos.get("medico_id") or ""),
        "medico_nombre": str(datos.get("medico_nombre") or ""),
        "sede": str(datos.get("sede") or "Sede principal"),
        "habitacion": str(datos.get("habitacion") or ""),
        "estado": estado,
        "motivo": str(datos.get("motivo") or ""),
        "fecha_ingreso": ingreso,
        "fecha_egreso": egreso,
        "notas": str(datos.get("notas") or ""),
        "creado_en": now,
        "actualizado_en": now,
    }
    _cargar(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True))
    try:
        from paquetes.notificaciones.NotificacionesServicio import emitir_a_roles
        pac = nuevo.get("paciente_nombre") or nuevo.get("id_paciente") or "Paciente"
        emitir_a_roles(
            "Nueva admisión hospitalaria",
            f"{pac}: ingreso {nuevo.get('tipo')} · {nuevo.get('servicio')} · "
            f"médico {nuevo.get('medico_nombre') or 'por asignar'}.",
            "info",
            roles=["medico", "enfermero"],
            referencia_tipo="admision",
            referencia_id=nuevo["id_admision"],
        )
    except Exception:
        pass
    return {"mensaje": "Admisión registrada", "id_admision": nuevo["id_admision"]}


def actualizar(id_admision: str, cambios: dict) -> dict:
    df = _extraer()
    idx = df.index[df["id_admision"].astype(str) == str(id_admision)].tolist()
    if not idx:
        return {"error": "Admisión no encontrada"}
    cambios = _enriquecer_paciente(cambios) if cambios.get("id_paciente") else cambios
    if cambios.get("tipo") and str(cambios["tipo"]) not in TIPOS:
        return {"error": f"tipo inválido. Use: {', '.join(sorted(TIPOS))}"}
    if cambios.get("via_llegada") and str(cambios["via_llegada"]).lower() not in VIAS:
        return {"error": "Vía de llegada inválida. Use: propia, ambulancia o referido."}
    via_prev = ""
    if "via_llegada" in df.columns:
        via_prev = df.at[idx[0], "via_llegada"]
    via = str(cambios.get("via_llegada") or via_prev or "propia").lower()
    tipo = str(cambios.get("tipo") or df.at[idx[0], "tipo"] or "ambulatoria")
    if via == "ambulancia" and tipo == "ambulatoria":
        cambios["tipo"] = "urgencia"
    ingreso = str(cambios.get("fecha_ingreso") or df.at[idx[0], "fecha_ingreso"] or "")
    egreso = str(cambios.get("fecha_egreso") if "fecha_egreso" in cambios else df.at[idx[0], "fecha_egreso"] or "")
    err_f = rango_fechas_ok(ingreso, egreso)
    if err_f:
        return {"error": err_f}
    actual = df.fillna("").loc[idx[0]].to_dict()
    candidato = {**actual, **cambios}
    if str(candidato.get("estado")) in ("alta", "cancelada"):
        from paquetes.instrumental import InstrumentalServicio as instrumental
        equipos = instrumental.asignados_admision(id_admision).get("instrumentos", [])
        if equipos:
            return {"error": f"Devuelva el instrumental asignado antes de cerrar la hospitalización ({len(equipos)} pendiente(s))"}
    if str(candidato.get("estado")) in ("alta", "cancelada") or str(candidato.get("tipo")) != "hospitalizacion":
        cambios["habitacion"] = ""
        if str(candidato.get("estado")) == "alta" and not cambios.get("fecha_egreso"):
            cambios["fecha_egreso"] = datetime.utcnow().date().isoformat()
        candidato = {**candidato, **cambios}
    error_cama = _validar_cama(candidato, df, excluir_id=id_admision)
    if error_cama:
        return {"error": error_cama}
    for k, v in cambios.items():
        if k in COLUMNAS and k not in ("id_admision", "creado_en"):
            df.at[idx[0], k] = v
    df.at[idx[0], "actualizado_en"] = datetime.utcnow().isoformat()
    _cargar(df)
    habitacion_anterior = str(actual.get("habitacion") or "")
    habitacion_nueva = str(candidato.get("habitacion") or "")
    if habitacion_nueva and habitacion_nueva != habitacion_anterior:
        from paquetes.instrumental import InstrumentalServicio as instrumental
        instrumental.reubicar_por_admision(id_admision, habitacion_nueva)
    return {"mensaje": "Admisión actualizada", "id_admision": id_admision}
