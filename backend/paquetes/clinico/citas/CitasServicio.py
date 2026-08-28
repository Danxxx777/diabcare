import uuid
import pandas as pd
from datetime import date, datetime
from nucleo.utilidades.ParquetCache import leer, escribir
from nucleo.utilidades.Validaciones import horario_consulta_ok

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
        df = facturas.extraer()
        if df.empty or "encounter_id" not in df.columns:
            return set()
        mask = df["estado"].astype(str).str.lower().eq("pagada") if "estado" in df.columns else True
        enc = df.loc[mask, "encounter_id"].astype(str)
        return set(enc[enc.isin(ids)].tolist())
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


def _fecha_con_agenda(df: pd.DataFrame, fecha: str = "") -> str:
    """Hoy, o el último día con citas (datos sintéticos no caen siempre en la fecha del sistema)."""
    f = str(fecha or date.today().isoformat())[:10]
    if df.empty or "fecha" not in df.columns:
        return f
    col = df["fecha"].astype(str)
    if col.str.startswith(f).any():
        return f
    try:
        return str(col.max())[:10]
    except Exception:
        return f


def hoy() -> dict:
    df = _extraer(copiar=False)
    if df.empty:
        return {"total": 0, "citas": [], "fecha": date.today().isoformat()}
    h = _fecha_con_agenda(df)
    sub = df[df["fecha"].astype(str).str.startswith(h)]
    total = int(len(sub))
    if not sub.empty and "hora" in sub.columns:
        sub = sub.sort_values("hora")
    rows = enriquecer_citas(sub.head(80).fillna("").to_dict(orient="records"))
    return {"total": total, "citas": rows, "fecha": h}


def resumen_operativo(fecha: str = "") -> dict:
    """Informe simple: totales y desglose transaccional (equivalente SELECT/agregación ligera en origen)."""
    df = _extraer(copiar=False)
    if df.empty:
        return {
            "tipo": "informe_simple",
            "fecha": fecha or date.today().isoformat(),
            "total": 0,
            "por_estado": {},
            "cobro_pagado": 0,
            "cobro_pendiente": 0,
        }
    f = _fecha_con_agenda(df, fecha)
    sub = df[df["fecha"].astype(str).str.startswith(f)]
    total = int(len(sub))
    por_estado: dict[str, int] = {}
    if total and "estado" in sub.columns:
        por_estado = (
            sub["estado"].fillna("—").astype(str).str.lower().value_counts().to_dict()
        )
        por_estado = {str(k): int(v) for k, v in por_estado.items()}
    pagadas = 0
    if "consulta_pagada" in sub.columns:
        pagadas = int(sub["consulta_pagada"].fillna(False).astype(bool).sum())
    elif "estado" in sub.columns:
        est = sub["estado"].astype(str).str.lower()
        pagadas = int(est.isin(["confirmada", "atendida", "pagada"]).sum())
    return {
        "tipo": "informe_simple",
        "fecha": f,
        "total": total,
        "por_estado": por_estado,
        "cobro_pagado": pagadas,
        "cobro_pendiente": max(0, total - pagadas),
    }


def listar(offset: int = 0, limit: int = 50, fecha: str = "", estado: str = "", q: str = "") -> dict:
    from nucleo.utilidades.Busqueda import rankear_dataframe

    df = _extraer(copiar=False)
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
    df = _extraer(copiar=False)
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


def _recetas_de_cita(cita: dict) -> list[dict]:
    from paquetes.farmacia import FarmaciaServicio as Farm
    df = Farm.recetas.extraer(copiar=False)
    if df.empty:
        return []
    cid = str(cita.get("id_cita") or "")
    pid = str(cita.get("id_paciente") or "")
    fecha = str(cita.get("fecha") or "")[:10]
    estados = df["estado"].fillna("").astype(str).str.lower()
    activas = ~estados.isin(["dispensada", "dispensado", "anulada", "anulado"])
    por_cita = df["encounter_id"].fillna("").astype(str) == cid
    por_paciente_fecha = (df["id_paciente"].fillna("").astype(str) == pid) & (df["fecha"].fillna("").astype(str).str[:10] == fecha)
    filas = df[activas & (por_cita | por_paciente_fecha)].fillna("").to_dict(orient="records")
    return Farm.enriquecer_recetas(filas)


def _lineas_consulta_y_receta(cita: dict, concepto: str, precio: float) -> tuple[list[dict], list[str]]:
    lineas = [{"concepto": concepto, "cantidad": 1, "precio_unitario": precio}]
    ids = []
    for receta in _recetas_de_cita(cita):
        ids.append(str(receta.get("id_receta") or ""))
        for med in receta.get("medicamentos") or []:
            lineas.append({
                "concepto": str(med.get("medicamento_nombre") or "Medicamento"),
                "cantidad": float(med.get("cantidad") or 1),
                "precio_unitario": float(med.get("precio_unitario") or 0),
            })
    return lineas, ids


def marcar_recetas_pagadas_cita(cita: dict) -> None:
    from paquetes.farmacia import FarmaciaServicio as Farm
    for receta in _recetas_de_cita(cita):
        Farm.recetas.actualizar(str(receta.get("id_receta") or ""), {"estado": "pagada"})


def cobrar_consulta(id_cita: str, metodo: str = "efectivo", referencia: str = "") -> dict:
    """
    Caja factura la atención y los medicamentos después de que el médico atiende.
    metodo=qr → emite factura y devuelve enlace/QR (el paciente paga; no se marca cobrada hasta el pago).
    efectivo | tarjeta | transferencia → registra el cobro ahora.
    """
    cita = obtener(id_cita)
    if cita.get("error"):
        return cita
    est = str(cita.get("estado") or "").lower()
    if est in ("cancelada", "anulada"):
        return {"error": "No se puede cobrar una cita cancelada"}
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
    pend = Fact.factura_abierta_por_cita(id_cita)
    if pend:
        fid = pend.get("id_factura")
        try:
            total = round(float(pend.get("total") or 0), 2)
        except (TypeError, ValueError):
            total = 0.0
        if total <= 0:
            return {"error": "La factura abierta no tiene total válido"}
        concepto = Fact.concepto_factura(str(fid))
    else:
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
        lineas_factura, recetas_asociadas = _lineas_consulta_y_receta(cita, concepto, precio)
        subtotal = round(sum(float(x.get("cantidad") or 1) * float(x.get("precio_unitario") or 0) for x in lineas_factura), 2)
        fac = Fact.crear_factura({
            "encounter_id": str(id_cita),
            "id_paciente": str(cita.get("id_paciente") or ""),
            "subtotal": subtotal,
            "descuento": 0,
            "iva": round(subtotal * 0.15, 2),
            "total": round(subtotal * 1.15, 2),
            "estado": "emitida",
            "fecha": str(cita.get("fecha") or date.today().isoformat())[:10],
            "lineas": lineas_factura,
        })
        if fac.get("error"):
            return fac
        fid = fac.get("id_factura")
        reg = fac.get("registro") if isinstance(fac.get("registro"), dict) else {}
        try:
            total = round(float(reg.get("total") or fac.get("total") or (subtotal * 1.15)), 2)
        except (TypeError, ValueError):
            total = round(subtotal * 1.15, 2)

    metodo_n = str(metodo or "efectivo").strip().lower()
    if metodo_n in ("qr", "enlace", "digital"):
        pac = str(cita.get("paciente_nombre") or cita.get("id_paciente") or "Paciente")
        enlace = Fact.crear_enlace_pago(str(fid), id_cita=str(id_cita), concepto=concepto, paciente=pac)
        if enlace.get("error"):
            return enlace
        return {
            "mensaje": "Enlace de pago listo. El cobro se registra cuando el paciente pague o caja confirme otro método.",
            "id_cita": id_cita,
            "id_factura": fid,
            "total": total,
            "metodo": "qr",
            "consulta_pagada": False,
            "estado": est,
            "concepto": concepto,
            **enlace,
        }

    pago = Fact.crear_pago(str(fid), {
        "monto": total,
        "metodo": metodo_n if metodo_n in ("efectivo", "tarjeta", "transferencia") else "efectivo",
        "referencia": str(referencia or ""),
        "fecha": date.today().isoformat(),
    })
    if pago.get("error"):
        return pago

    if est != "atendida":
        actualizar(id_cita, {"estado": "confirmada"})
    marcar_recetas_pagadas_cita(cita)
    try:
        from paquetes.notificaciones.NotificacionesServicio import emitir_a_roles
        pac = str(cita.get("paciente_nombre") or cita.get("id_paciente") or "Paciente")
        hora = str(cita.get("hora") or "")
        fecha = str(cita.get("fecha") or "")
        emitir_a_roles(
            "Consulta lista para atender",
            f"{pac}: cita cobrada ({fecha} {hora}). El paciente ya puede pasar a consulta.",
            "info",
            roles=["medico"],
            referencia_tipo="cita",
            referencia_id=str(id_cita),
        )
    except Exception:
        pass
    return {
        "mensaje": "Consulta cobrada — paciente listo para el médico",
        "id_cita": id_cita,
        "id_factura": fid,
        "total": total,
        "metodo": metodo_n,
        "consulta_pagada": True,
        "estado": "confirmada",
        "concepto": concepto,
    }


def preview_cobro(id_cita: str) -> dict:
    """Datos para el modal de caja (sin registrar pago)."""
    cita = obtener(id_cita)
    if cita.get("error"):
        return cita
    if consulta_pagada(id_cita):
        return {
            "id_cita": id_cita,
            "consulta_pagada": True,
            "mensaje": "Consulta ya cobrada",
        }
    from paquetes.facturacion import FacturacionServicio as Fact
    from nucleo.utilidades.UrlPublica import alcance_url
    Fact.seed_basico()
    tarifas = Fact.tarifario.listar(offset=0, limit=200, incluir_inactivos=True).get("tarifas") or []
    tarifa = next((t for t in tarifas if str(t.get("codigo") or "").upper() == "CONS-DM"), None)
    precio = round(float((tarifa or {}).get("precio") or 35), 2)
    concepto = str((tarifa or {}).get("descripcion") or "Consulta endocrinología diabetes")
    lineas, _ = _lineas_consulta_y_receta(cita, concepto, precio)
    subtotal = round(sum(float(x.get("cantidad") or 1) * float(x.get("precio_unitario") or 0) for x in lineas), 2)
    iva = round(subtotal * 0.15, 2)
    alcance = alcance_url()
    return {
        "id_cita": id_cita,
        "consulta_pagada": False,
        "concepto": concepto,
        "precio": subtotal,
        "lineas": lineas,
        "iva": iva,
        "total": round(subtotal + iva, 2),
        "paciente": cita.get("paciente_nombre") or cita.get("id_paciente") or "Paciente",
        "fecha": cita.get("fecha"),
        "hora": cita.get("hora"),
        "alcance": alcance["alcance"],
        "internet": alcance["internet"],
        "url_base": alcance["url"],
        "stripe": Fact.stripe_disponible(),
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
    fecha = str(datos.get("fecha") or date.today().isoformat())
    hora = str(datos.get("hora") or "09:00")
    err = horario_consulta_ok(fecha, hora)
    if err:
        return {"error": err}
    # Recepción solo agenda: el estado lo cambia el médico (o Cancelar).
    estado = "programada"
    now = datetime.utcnow().isoformat()
    nuevo = {
        "id_cita": str(uuid.uuid4()),
        "id_paciente": str(datos["id_paciente"]),
        "paciente_nombre": str(datos.get("paciente_nombre") or ""),
        "medico": str(datos.get("medico") or ""),
        "fecha": fecha,
        "hora": hora,
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
    fecha = str(cambios.get("fecha") or df.at[idx[0], "fecha"] or "")
    hora = str(cambios.get("hora") or df.at[idx[0], "hora"] or "")
    if "fecha" in cambios or "hora" in cambios:
        err = horario_consulta_ok(fecha, hora)
        if err:
            return {"error": err}
    for k, v in cambios.items():
        if k in COLUMNAS and k not in ("id_cita", "creado_en"):
            df.at[idx[0], k] = v
    df.at[idx[0], "actualizado_en"] = datetime.utcnow().isoformat()
    _cargar(df)
    return {"mensaje": "Cita actualizada", "id_cita": id_cita}


def cancelar(id_cita: str) -> dict:
    return actualizar(id_cita, {"estado": "cancelada"})
