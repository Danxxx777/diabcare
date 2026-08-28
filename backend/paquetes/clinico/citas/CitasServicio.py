import uuid
import pandas as pd
from datetime import date, datetime
from nucleo.utilidades.ParquetCache import leer, escribir
from nucleo.utilidades.Validaciones import horario_consulta_ok
from paquetes.configuracion.ConfiguracionServicio import iva_pct, iva_factor

BUCKET_APP = "diabcare-app"
ARCHIVO = "operativo/citas.parquet"
COLUMNAS = [
    "id_cita", "id_paciente", "paciente_nombre", "id_medico", "medico", "fecha", "hora",
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


def resolver_medico(datos: dict) -> tuple[str, str]:
    """(id_medico, nombre) a partir de lo que mande el formulario.

    Acepta id o nombre: la agenda vieja solo enviaba el nombre.
    """
    id_medico = str(datos.get("id_medico") or "").strip()
    nombre = str(datos.get("medico") or "").strip()
    try:
        from paquetes.usuarios.UsuariosServicio import listar_activos_por_rol
        medicos = listar_activos_por_rol("medico") or []
    except Exception:
        medicos = []
    if id_medico:
        for u in medicos:
            if str(u.get("id")) == id_medico:
                return id_medico, str(u.get("nombre") or nombre)
        return id_medico, nombre
    if nombre:
        objetivo = nombre.lower()
        for u in medicos:
            if str(u.get("nombre") or "").strip().lower() == objetivo:
                return str(u.get("id") or ""), str(u.get("nombre") or nombre)
    return "", nombre


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
    if not nombre and not id_usuario:
        return {"total": 0, "medico": "", "citas": []}
    df = _extraer(copiar=False)
    if df.empty:
        return {"total": 0, "medico": nombre, "citas": []}
    # Por id cuando la cita lo tiene; por nombre solo para las citas viejas,
    # que se agendaron cuando la agenda no guardaba el id del médico.
    uid = str(id_usuario or "").strip()
    ids = (df["id_medico"].astype(str).str.strip()
           if "id_medico" in df.columns else pd.Series("", index=df.index))
    nombres = df["medico"].astype(str).str.strip().str.lower()
    coincide = (ids == uid) if uid else pd.Series(False, index=df.index)
    if nombre:
        coincide = coincide | (ids.eq("") & nombres.eq(nombre.lower()))
    df = df[coincide]
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


def _tarifa_consulta(cita: dict) -> dict:
    """Tarifa de la consulta segun el servicio que atendio.

    Endocrinologia y medicina interna no cuestan lo mismo; antes todo se cobraba
    a un unico codigo generico que ni figuraba en el tarifario.
    """
    from paquetes.facturacion import FacturacionServicio as Fact

    texto = " ".join([
        str(cita.get("servicio") or ""),
        str(cita.get("motivo") or ""),
    ]).lower()
    codigo = "CONS-ENDO" if ("endocrino" in texto or "diabet" in texto) else "CONS-GEN"
    tarifa = Fact.tarifa_por_codigo(codigo)
    if not tarifa:
        tarifa = Fact.tarifa_por_codigo("CONS-GEN") or Fact.tarifa_por_codigo("CONS-ENDO")
    return tarifa or {}


def _ordenes_lab_de_cita(cita: dict) -> list[dict]:
    """Ordenes de laboratorio del paciente ese dia, aun sin facturar."""
    from paquetes.laboratorio import LaboratorioServicio as Lab

    pid = str(cita.get("id_paciente") or "")
    fecha = str(cita.get("fecha") or "")[:10]
    if not pid or not fecha:
        return []
    try:
        df = Lab.ordenes.extraer(copiar=False)
    except Exception:
        return []
    if df.empty:
        return []
    estados = df["estado"].fillna("").astype(str).str.lower()
    vivas = ~estados.isin(["anulada", "anulado", "facturada"])
    mismas = (df["id_paciente"].fillna("").astype(str) == pid) & (
        df["fecha"].fillna("").astype(str).str[:10] == fecha)
    return df[vivas & mismas].fillna("").to_dict(orient="records")


def _lineas_laboratorio(cita: dict) -> tuple[list[dict], list[str]]:
    """Una linea por orden de laboratorio, con la tarifa de su prueba."""
    from paquetes.facturacion import FacturacionServicio as Fact
    from paquetes.laboratorio import LaboratorioServicio as Lab

    ordenes = _ordenes_lab_de_cita(cita)
    if not ordenes:
        return [], []
    try:
        pruebas = {
            str(p.get("id_prueba")): p
            for p in (Lab.pruebas.listar(limit=500, incluir_inactivos=True).get("pruebas") or [])
        }
    except Exception:
        pruebas = {}

    lineas, ids = [], []
    for orden in ordenes:
        prueba = pruebas.get(str(orden.get("id_prueba") or "")) or {}
        codigo_prueba = str(prueba.get("codigo") or "").strip().upper()
        # LAB-HBA1C para HbA1c; si esa prueba no tiene tarifa propia, la generica.
        tarifa = Fact.tarifa_por_codigo("LAB-" + codigo_prueba) if codigo_prueba else {}
        if not tarifa:
            tarifa = Fact.tarifa_por_codigo("LAB-HBA1C")
        try:
            precio = round(float(tarifa.get("precio") or 0), 2)
        except (TypeError, ValueError):
            precio = 0.0
        if precio <= 0:
            continue
        lineas.append({
            "concepto": "Laboratorio: " + str(prueba.get("nombre") or codigo_prueba or "prueba"),
            "cantidad": 1,
            "precio_unitario": precio,
        })
        ids.append(str(orden.get("id_orden") or ""))
    return lineas, ids


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
        tarifa = _tarifa_consulta(cita)
        try:
            precio = round(float(tarifa.get("precio") or 0), 2)
        except (TypeError, ValueError):
            precio = 0.0
        if precio <= 0:
            return {"error": "No hay tarifa de consulta cargada. Revise el Tarifario en Facturación."}

        concepto = str(tarifa.get("descripcion") or "Consulta médica")
        lineas_factura, recetas_asociadas = _lineas_consulta_y_receta(cita, concepto, precio)
        # Lo que se le hizo al paciente ese dia tambien se cobra: hasta ahora las
        # ordenes de laboratorio quedaban fuera de la factura.
        lineas_lab, ordenes_lab = _lineas_laboratorio(cita)
        lineas_factura.extend(lineas_lab)

        subtotal = round(sum(float(x.get("cantidad") or 1) * float(x.get("precio_unitario") or 0) for x in lineas_factura), 2)
        # Cobertura de la poliza del paciente: antes todos pagaban el 100%.
        cobertura = Fact.cobertura_paciente(str(cita.get("id_paciente") or ""))
        pct = float(cobertura.get("cobertura_pct") or 0)
        descuento = round(subtotal * pct / 100.0, 2)
        base = round(subtotal - descuento, 2)
        fac = Fact.crear_factura({
            "encounter_id": str(id_cita),
            "id_paciente": str(cita.get("id_paciente") or ""),
            "id_seguro": cobertura.get("id_seguro") or "",
            "subtotal": subtotal,
            "descuento": descuento,
            "iva": round(base * iva_pct() / 100.0, 2),
            "total": round(base * iva_factor(), 2),
            "estado": "emitida",
            "fecha": str(cita.get("fecha") or date.today().isoformat())[:10],
            "lineas": lineas_factura,
        })
        if fac.get("error"):
            return fac
        fid = fac.get("id_factura")
        reg = fac.get("registro") if isinstance(fac.get("registro"), dict) else {}
        try:
            total = round(float(reg.get("total") or fac.get("total") or (base * iva_factor())), 2)
        except (TypeError, ValueError):
            total = round(base * iva_factor(), 2)

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
    tarifa = _tarifa_consulta(cita)
    precio = round(float(tarifa.get("precio") or 0), 2)
    concepto = str(tarifa.get("descripcion") or "Consulta médica")
    lineas, _ = _lineas_consulta_y_receta(cita, concepto, precio)
    lineas_lab, _ordenes = _lineas_laboratorio(cita)
    lineas.extend(lineas_lab)
    subtotal = round(sum(float(x.get("cantidad") or 1) * float(x.get("precio_unitario") or 0) for x in lineas), 2)
    cobertura = Fact.cobertura_paciente(str(cita.get("id_paciente") or ""))
    pct = float(cobertura.get("cobertura_pct") or 0)
    descuento = round(subtotal * pct / 100.0, 2)
    base = round(subtotal - descuento, 2)
    iva = round(base * iva_pct() / 100.0, 2)
    alcance = alcance_url()
    return {
        "id_cita": id_cita,
        "consulta_pagada": False,
        "concepto": concepto,
        "precio": subtotal,
        "lineas": lineas,
        "seguro": cobertura.get("nombre"),
        "cobertura_pct": pct,
        "descuento": descuento,
        "iva": iva,
        "total": round(base + iva, 2),
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
    id_medico, nombre_medico = resolver_medico(datos)
    # Recepción solo agenda: el estado lo cambia el médico (o Cancelar).
    estado = "programada"
    now = datetime.utcnow().isoformat()
    nuevo = {
        "id_cita": str(uuid.uuid4()),
        "id_paciente": str(datos["id_paciente"]),
        "paciente_nombre": str(datos.get("paciente_nombre") or ""),
        "id_medico": id_medico,
        "medico": nombre_medico,
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
    if cambios.get("medico") or cambios.get("id_medico"):
        # Reasignar médico: id y nombre viajan siempre juntos.
        cambios = dict(cambios)
        cambios["id_medico"], cambios["medico"] = resolver_medico(cambios)
    for k, v in cambios.items():
        if k in COLUMNAS and k not in ("id_cita", "creado_en"):
            df.at[idx[0], k] = v
    df.at[idx[0], "actualizado_en"] = datetime.utcnow().isoformat()
    _cargar(df)
    return {"mensaje": "Cita actualizada", "id_cita": id_cita}


def cancelar(id_cita: str) -> dict:
    return actualizar(id_cita, {"estado": "cancelada"})
