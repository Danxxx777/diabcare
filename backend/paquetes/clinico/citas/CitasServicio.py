import io
import uuid
import pandas as pd
from datetime import date, datetime
from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente

BUCKET_APP = "diabcare-app"
ARCHIVO = "operativo/citas.parquet"
COLUMNAS = [
    "id_cita", "id_paciente", "paciente_nombre", "medico", "fecha", "hora",
    "estado", "motivo", "sede", "notas", "proximo_control", "creado_en", "actualizado_en",
]
ESTADOS = {"programada", "confirmada", "atendida", "cancelada", "no_asistio"}
ESTADO_LABEL = {
    "programada": "Programada",
    "confirmada": "Lista (cobrada)",
    "atendida": "Atendida",
    "cancelada": "Cancelada",
    "no_asistio": "No asistió",
}


def _extraer() -> pd.DataFrame:
    try:
        c = get_cliente()
        if not c.bucket_exists(BUCKET_APP):
            c.make_bucket(BUCKET_APP)
        obj = c.get_object(BUCKET_APP, ARCHIVO)
        return pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame(columns=COLUMNAS)


def _cargar(df: pd.DataFrame):
    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(BUCKET_APP, ARCHIVO, buf, buf.getbuffer().nbytes)


def _enriquecer_paciente(datos: dict) -> dict:
    pid = datos.get("id_paciente")
    if not pid:
        return datos
    try:
        from paquetes.clinico.pacientes.PacientesServicio import obtener
        p = obtener(str(pid))
        if "error" not in p:
            datos.setdefault("paciente_nombre", p.get("nombre_completo", ""))
    except Exception:
        pass
    return datos


def _ids_consulta_pagada(ids: set[str]) -> set[str]:
    """Citas con factura de consulta pagada (encounter_id = id_cita)."""
    ids = {str(i) for i in ids if i}
    if not ids:
        return set()
    try:
        from paquetes.facturacion.FacturacionServicio import facturas
        data = facturas.listar(offset=0, limit=10**9, incluir_inactivos=True)
        out = set()
        for f in data.get("facturas") or []:
            if str(f.get("estado") or "").lower() != "pagada":
                continue
            enc = str(f.get("encounter_id") or "").strip()
            if enc in ids:
                out.add(enc)
        return out
    except Exception:
        return set()


def consulta_pagada(id_cita: str) -> bool:
    return str(id_cita) in _ids_consulta_pagada({str(id_cita)})


def enriquecer_citas(filas: list) -> list:
    if not filas:
        return []
    pagadas = _ids_consulta_pagada({str(r.get("id_cita") or "") for r in filas})
    ids = {str(r.get("id_paciente") or "") for r in filas if r.get("id_paciente")}
    mapa = {}
    if ids:
        try:
            from nucleo.utilidades.PacientesLookup import mapa_pacientes
            mapa = mapa_pacientes(ids)
        except Exception:
            mapa = {}
    out = []
    for r in filas:
        x = dict(r)
        cid = str(x.get("id_cita") or "")
        paid = cid in pagadas
        est = str(x.get("estado") or "").lower()
        x["consulta_pagada"] = paid
        x["pago_label"] = "Cobrada" if paid else "Pendiente cobro"
        x["estado_label"] = ESTADO_LABEL.get(est, est[:1].upper() + est[1:] if est else "—")
        pid = str(x.get("id_paciente") or "").strip()
        p = mapa.get(pid) or {}
        if p.get("nombre_completo") and not (x.get("paciente_nombre") or "").strip():
            x["paciente_nombre"] = p["nombre_completo"]
        x["tiene_foto"] = bool(p.get("tiene_foto"))
        out.append(x)
    return out


def hoy() -> dict:
    df = _extraer()
    if df.empty:
        return {"total": 0, "citas": []}
    h = date.today().isoformat()
    sub = df[df["fecha"].astype(str).str.startswith(h)]
    sub = sub.sort_values("hora")
    rows = enriquecer_citas(sub.fillna("").to_dict(orient="records"))
    return {"total": len(rows), "citas": rows}


def listar(offset: int = 0, limit: int = 50, fecha: str = "", estado: str = "", q: str = "") -> dict:
    from nucleo.utilidades.Busqueda import rankear_dataframe

    df = _extraer()
    if df.empty:
        return {"total": 0, "citas": []}
    if fecha:
        df = df[df["fecha"].astype(str).str.startswith(str(fecha))]
    if estado:
        df = df[df["estado"].astype(str) == str(estado)]
    if q:
        df = rankear_dataframe(df, q, ["paciente_nombre", "medico", "motivo", "sede", "estado", "notas"])
    elif "fecha" in df.columns and "hora" in df.columns:
        df = df.sort_values(["fecha", "hora"], ascending=[False, True])
    total = len(df)
    chunk = df.iloc[offset:offset + limit]
    return {"total": int(total), "citas": enriquecer_citas(chunk.fillna("").to_dict(orient="records"))}


def _nombre_medico(id_usuario: str) -> str:
    try:
        from paquetes.usuarios.UsuariosServicio import obtener_usuario
        u = obtener_usuario(str(id_usuario))
        if "error" not in u:
            return str(u.get("nombre") or "").strip()
    except Exception:
        pass
    return ""


def listar_por_medico(
    id_usuario: str,
    offset: int = 0,
    limit: int = 50,
    fecha: str = "",
    estado: str = "",
    nombre_jwt: str = "",
    q: str = "",
) -> dict:
    nombre = _nombre_medico(id_usuario) or str(nombre_jwt or "").strip()
    if not nombre:
        return {"total": 0, "medico": "", "citas": []}
    df = _extraer()
    if df.empty:
        return {"total": 0, "medico": nombre, "citas": []}
    nl = nombre.lower()
    df = df[df["medico"].astype(str).str.strip().str.lower() == nl]
    if fecha:
        df = df[df["fecha"].astype(str).str.startswith(fecha)]
    if estado:
        df = df[df["estado"] == estado]
    if q:
        from nucleo.utilidades.Busqueda import rankear_dataframe
        df = rankear_dataframe(df, q, ["paciente_nombre", "motivo", "estado", "fecha", "hora", "notas"])
    total = len(df)
    if not q:
        df = df.sort_values(["fecha", "hora"], ascending=[False, True])
    chunk = df.iloc[offset:offset + limit]
    return {
        "total": total,
        "medico": nombre,
        "citas": enriquecer_citas(chunk.fillna("").to_dict(orient="records")),
    }


def cobrar_consulta(id_cita: str, metodo: str = "efectivo") -> dict:
    """
    RN-CIT-010: caja cobra la consulta (tarifa CONS-DM) antes de que el médico atienda.
    Emite factura + pago completo y deja la cita en confirmada (lista para consulta).
    """
    cita = obtener(id_cita)
    if cita.get("error"):
        return cita
    est = str(cita.get("estado") or "").lower()
    if est in ("cancelada", "anulada"):
        return {"error": "No se puede cobrar una cita cancelada"}
    if est == "atendida":
        return {"error": "La cita ya fue atendida"}
    if consulta_pagada(id_cita):
        if est == "programada":
            actualizar(id_cita, {"estado": "confirmada"})
        return {
            "mensaje": "Consulta ya cobrada",
            "id_cita": id_cita,
            "consulta_pagada": True,
            "estado": "confirmada",
        }

    from paquetes.facturacion import FacturacionServicio as Fact

    Fact.seed_basico()
    tarifas = Fact.tarifario.listar(offset=0, limit=200, incluir_inactivos=True).get("tarifas") or []
    tarifa = next(
        (t for t in tarifas if str(t.get("codigo") or "").upper() == "CONS-DM"),
        None,
    )
    if not tarifa:
        creada = Fact.tarifario.crear({
            "codigo": "CONS-DM",
            "descripcion": "Consulta endocrinología diabetes",
            "precio": 35.0,
            "activo": True,
        })
        if creada.get("error"):
            return {"error": "No hay tarifa CONS-DM. Cargue el catálogo en Facturación."}
        tarifa = creada.get("registro") or {
            "codigo": "CONS-DM",
            "descripcion": "Consulta endocrinología diabetes",
            "precio": 35.0,
        }
    try:
        precio = round(float(tarifa.get("precio") or 0), 2)
    except (TypeError, ValueError):
        precio = 0.0
    if precio <= 0:
        return {"error": "La tarifa CONS-DM no tiene precio válido"}

    concepto = str(tarifa.get("descripcion") or "Consulta médica")
    fac = Fact.crear_factura({
        "encounter_id": str(id_cita),
        "id_paciente": str(cita.get("id_paciente") or ""),
        "subtotal": precio,
        "descuento": 0,
        "iva": round(precio * 0.15, 2),
        "total": round(precio * 1.15, 2),
        "estado": "emitida",
        "fecha": str(cita.get("fecha") or date.today().isoformat())[:10],
        "lineas": [{
            "concepto": concepto,
            "cantidad": 1,
            "precio_unitario": precio,
        }],
    })
    if fac.get("error"):
        return fac
    fid = fac.get("id_factura")
    reg = fac.get("registro") if isinstance(fac.get("registro"), dict) else {}
    try:
        total = round(float(reg.get("total") or fac.get("total") or (precio * 1.15)), 2)
    except (TypeError, ValueError):
        total = round(precio * 1.15, 2)

    pago = Fact.crear_pago(str(fid), {
        "monto": total,
        "metodo": str(metodo or "efectivo"),
        "fecha": date.today().isoformat(),
    })
    if pago.get("error"):
        return pago

    actualizar(id_cita, {"estado": "confirmada"})
    return {
        "mensaje": "Consulta cobrada — paciente listo para el médico",
        "id_cita": id_cita,
        "id_factura": fid,
        "total": total,
        "metodo": metodo,
        "consulta_pagada": True,
        "estado": "confirmada",
        "concepto": concepto,
    }


def actualizar_estado_medico(
    id_cita: str, id_usuario: str, estado: str, nombre_jwt: str = "",
) -> dict:
    nombre = _nombre_medico(id_usuario) or str(nombre_jwt or "").strip()
    if not nombre:
        return {"error": "Médico no encontrado"}
    permitidos = {"atendida", "no_asistio"}
    estado = str(estado or "").strip()
    if estado not in permitidos:
        return {"error": f"Estado no permitido. Use: {', '.join(sorted(permitidos))}"}
    df = _extraer()
    idx = df.index[df["id_cita"].astype(str) == str(id_cita)].tolist()
    if not idx:
        return {"error": "Cita no encontrada"}
    asignado = str(df.at[idx[0], "medico"]).strip().lower()
    if asignado != nombre.lower():
        return {"error": "La cita no está asignada a este médico"}
    if df.at[idx[0], "estado"] == "cancelada":
        return {"error": "La cita está cancelada"}
    if estado == "atendida" and not consulta_pagada(id_cita):
        return {
            "error": "RN-CIT-010: debe cobrarse la consulta en caja antes de atender al paciente",
        }
    return actualizar(id_cita, {"estado": estado})


def obtener(id_cita: str) -> dict:
    df = _extraer()
    fila = df[df["id_cita"].astype(str) == str(id_cita)]
    if fila.empty:
        return {"error": "Cita no encontrada"}
    return fila.fillna("").iloc[0].to_dict()


def crear(datos: dict) -> dict:
    datos = _enriquecer_paciente(dict(datos))
    if not datos.get("id_paciente"):
        return {"error": "id_paciente es obligatorio"}
    # Recepción solo agenda: el estado lo cambia el médico (o Cancelar).
    estado = "programada"
    now = datetime.utcnow().isoformat()
    nuevo = {
        "id_cita": str(uuid.uuid4()),
        "id_paciente": str(datos["id_paciente"]),
        "paciente_nombre": str(datos.get("paciente_nombre") or ""),
        "medico": str(datos.get("medico") or ""),
        "fecha": str(datos.get("fecha") or date.today().isoformat()),
        "hora": str(datos.get("hora") or "09:00"),
        "estado": estado,
        "motivo": str(datos.get("motivo") or "Control clínico"),
        "sede": str(datos.get("sede") or "Sede principal"),
        "notas": str(datos.get("notas") or ""),
        "proximo_control": str(datos.get("proximo_control") or ""),
        "creado_en": now,
        "actualizado_en": now,
    }
    df = _extraer()
    _cargar(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True))
    return {"mensaje": "Cita agendada", "id_cita": nuevo["id_cita"]}


def actualizar(id_cita: str, cambios: dict) -> dict:
    df = _extraer()
    idx = df.index[df["id_cita"].astype(str) == str(id_cita)].tolist()
    if not idx:
        return {"error": "Cita no encontrada"}
    cambios = _enriquecer_paciente(cambios) if cambios.get("id_paciente") else cambios
    for k, v in cambios.items():
        if k in COLUMNAS and k not in ("id_cita", "creado_en"):
            df.at[idx[0], k] = v
    df.at[idx[0], "actualizado_en"] = datetime.utcnow().isoformat()
    _cargar(df)
    return {"mensaje": "Cita actualizada", "id_cita": id_cita}


def cancelar(id_cita: str) -> dict:
    return actualizar(id_cita, {"estado": "cancelada"})
