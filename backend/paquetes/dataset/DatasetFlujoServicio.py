# -*- coding: utf-8 -*-
"""Expande generación sintética a un flujo operativo E2E (pacientes → clínica → negocio)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

NOMBRES_F = ["Ana", "María", "Elena", "Sofía", "Paula", "Lucía", "Valeria", "Camila", "Diana", "Rosa"]
NOMBRES_M = ["Luis", "Carlos", "José", "Diego", "Andrés", "Miguel", "Pedro", "Jorge", "Mateo", "Daniel"]
APELLIDOS = [
    "García", "Rodríguez", "Martínez", "López", "González", "Pérez", "Sánchez",
    "Ramírez", "Torres", "Flores", "Rivera", "Gómez", "Díaz", "Vargas", "Castro",
]
SEDES = [
    "Quito Centro", "Guayaquil Norte", "Cuenca", "Ambato", "Sede principal",
    "Machala", "Manta", "Loja", "Ibarra", "Riobamba", "Santo Domingo", "Santa Elena",
]
MOTIVOS = [
    "Control diabetes", "Ajuste de insulina", "Seguimiento HbA1c",
    "Pie diabético", "Hipoglucemia reciente", "Primera consulta endocrino",
]


def _now() -> str:
    return datetime.utcnow().isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


def _norm_genero(g: Any) -> str:
    s = str(g or "").strip().lower()
    if s in ("f", "female", "femenino", "mujer"):
        return "Femenino"
    if s in ("m", "male", "masculino", "hombre"):
        return "Masculino"
    return "Femenino" if "f" in s else ("Masculino" if "m" in s else "Otro")


def _personal() -> dict[str, list[dict]]:
    """Devuelve listas {id, nombre} por rol."""
    out: dict[str, list[dict]] = {"medico": [], "enfermero": [], "farmaceutico": [], "admin": []}
    try:
        from paquetes.usuarios.UsuariosServicio import listar_activos_por_rol, obtener_usuarios
        for rol, key in [
            ("medico", "medico"),
            ("enfermero", "enfermero"),
            ("farmaceutico", "farmaceutico"),
            ("administrador", "admin"),
        ]:
            for r in listar_activos_por_rol(rol) or []:
                out[key].append({"id": str(r["id"]), "nombre": str(r.get("nombre") or "Médico")})
        if not out["medico"]:
            for r in (obtener_usuarios() or [])[:5]:
                out["medico"].append({"id": str(r["id"]), "nombre": str(r.get("nombre") or "Médico")})
    except Exception:
        pass
    for k in out:
        if not out[k]:
            out[k] = [{"id": _uid(), "nombre": k.capitalize()}]
    return out


# Códigos de provincia en cédula ecuatoriana (2 primeros dígitos).
PROVINCIAS_CEDULA = {
    1: "Azuay", 2: "Bolívar", 3: "Cañar", 4: "Carchi", 5: "Cotopaxi",
    6: "Chimborazo", 7: "El Oro", 8: "Esmeraldas", 9: "Guayas", 10: "Imbabura",
    11: "Loja", 12: "Los Ríos", 13: "Manabí", 14: "Morona Santiago", 15: "Napo",
    16: "Pastaza", 17: "Pichincha", 18: "Tungurahua", 19: "Zamora Chinchipe",
    20: "Galápagos", 21: "Sucumbíos", 22: "Orellana",
    23: "Santo Domingo de los Tsáchilas", 24: "Santa Elena",
}
# Probabilidad aproximada por población (más 09 Guayas y 17 Pichincha, pero todas salen).
_PESO_PROV = np.array([
    4, 1, 2, 1, 2,  # 01-05
    2, 3, 2, 12, 2,  # 06-10 (09 Guayas alto)
    2, 3, 5, 1, 1,  # 11-15
    1, 11, 2, 1, 1,  # 16-20 (17 Pichincha alto)
    1, 1, 2, 2,      # 21-24
], dtype=float)
_PESO_PROV = _PESO_PROV / _PESO_PROV.sum()

# Sede operativa → código de provincia para la cédula
_SEDE_A_PROVINCIA = {
    "quito": 17, "quito centro": 17, "sede principal": 17,
    "guayaquil": 9, "guayaquil norte": 9,
    "cuenca": 1,
    "ambato": 18,
    "machala": 7,
    "manta": 13, "portoviejo": 13,
    "loja": 11,
    "esmeraldas": 8,
    "santo domingo": 23,
    "santa elena": 24,
    "ibarra": 10,
    "riobamba": 6,
}


def _provincia_desde_sede(sede: str | None) -> int | None:
    if not sede:
        return None
    key = str(sede).strip().lower()
    if key in _SEDE_A_PROVINCIA:
        return _SEDE_A_PROVINCIA[key]
    for fragmento, codigo in _SEDE_A_PROVINCIA.items():
        if fragmento in key:
            return codigo
    return None


def _cedula_ecuador(rng: np.random.Generator, provincia: int | None = None) -> str:
    """
    Cédula ecuatoriana de 10 dígitos.
    - Dígitos 1-2: provincia (01–24), p. ej. 09=Guayas, 17=Pichincha, 01=Azuay
    - Dígito 3: 0–5 persona natural
    - Dígito 10: verificador (módulo 10)
    """
    if provincia is None or provincia not in PROVINCIAS_CEDULA:
        provincia = int(rng.choice(np.arange(1, 25), p=_PESO_PROV))
    # Tercer dígito 0–5 = persona natural
    base9 = f"{provincia:02d}{int(rng.integers(0, 6))}{int(rng.integers(0, 1_000_000)):06d}"
    coef = (2, 1, 2, 1, 2, 1, 2, 1, 2)
    total = 0
    for i, c in enumerate(coef):
        v = int(base9[i]) * c
        total += v - 9 if v >= 10 else v
    digito = (10 - (total % 10)) % 10
    return base9 + str(digito)


def _historia_clinica(year: int, n: int) -> str:
    """Número de historia clínica hospitalaria (no es la cédula)."""
    return f"HC-{year}-{n:05d}"


def _perfil_a_paciente(row: dict, year: int, i: int, rng: np.random.Generator) -> dict:
    genero = _norm_genero(row.get("gender") or row.get("genero"))
    nombre = (NOMBRES_F if genero == "Femenino" else NOMBRES_M)[int(rng.integers(0, 10))]
    apellido = APELLIDOS[int(rng.integers(0, len(APELLIDOS)))]
    edad = int(float(row.get("age") or row.get("edad") or rng.integers(30, 75)))
    # Preferir sedes ecuatorianas para alinear cédula con provincia
    sede_raw = str(row.get("location") or row.get("ubicacion") or "")
    prov = _provincia_desde_sede(sede_raw)
    if prov is None:
        sede = SEDES[int(rng.integers(0, len(SEDES)))]
        prov = _provincia_desde_sede(sede)
    else:
        sede = sede_raw[:80] if sede_raw else SEDES[int(rng.integers(0, len(SEDES)))]
    cedula = _cedula_ecuador(rng, provincia=prov)
    return {
        "codigo": _historia_clinica(year, 1000 + i),
        "nombre": nombre,
        "apellido": apellido,
        "documento": cedula,
        "edad": edad,
        "genero": genero,
        # Celulares en Ecuador sí usan prefijo 09 (no confundir con cédula)
        "telefono": f"09{int(rng.integers(10_000_000, 99_999_999))}",
        "email": f"paciente.{cedula}@demo.diabcare.local",
        "sede": sede[:80],
        "notas": "",
        # clínica origen
        "_bmi": float(row.get("bmi") or 27),
        "_hba1c": float(row.get("hbA1c_level") or row.get("hba1c_level") or 6.5),
        "_glucosa": float(row.get("blood_glucose_level") or 120),
        "_diabetes": int(row.get("diabetes") or 0),
        "_htn": int(row.get("hypertension") or 0),
        "_heart": int(row.get("heart_disease") or 0),
        "_smoke": str(row.get("smoking_history") or "never"),
        "_year": int(row.get("year") or year),
        # Reutilizar encounter del stage (no crear filas extra)
        "_encounter_num": (
            int(float(row["encounter_id"]))
            if row.get("encounter_id") not in (None, "")
            else None
        ),
        "_encounter": (
            str(int(float(row["encounter_id"])))
            if row.get("encounter_id") not in (None, "")
            else None
        ),
    }


def _crear_pacientes(perfiles: list[dict], year: int, rng: np.random.Generator) -> list[dict]:
    """Alta masiva en operativo/pacientes.parquet (una sola escritura)."""
    from paquetes.clinico.pacientes import PacientesServicio as PS

    now = _now()
    existentes = PS._extraer()
    base = int(len(existentes))
    docs = set(existentes["documento"].astype(str)) if not existentes.empty and "documento" in existentes.columns else set()
    filas = []
    out = []
    for i, row in enumerate(perfiles):
        datos = _perfil_a_paciente(row, year, base + i, rng)
        clin = {k: datos.pop(k) for k in list(datos) if k.startswith("_")}
        doc = str(datos.get("documento") or "")
        if doc in docs:
            doc = _cedula_ecuador(rng)
            datos["documento"] = doc
        docs.add(doc)
        pid = _uid()
        fila = {
            "id_paciente": pid,
            "codigo": datos.get("codigo") or _historia_clinica(year, base + i + 1),
            "nombre": datos["nombre"],
            "apellido": datos["apellido"],
            "documento": doc,
            "edad": float(datos["edad"]),
            "genero": datos["genero"],
            "telefono": datos.get("telefono") or "",
            "email": datos.get("email") or "",
            "sede": datos.get("sede") or "Sede principal",
            "estado": "activo",
            "notas": datos.get("notas") or "",
            "creado_en": now,
            "actualizado_en": now,
        }
        filas.append(fila)
        out.append({
            "id_paciente": pid,
            "nombre": fila["nombre"],
            "apellido": fila["apellido"],
            "nombre_completo": f"{fila['nombre']} {fila['apellido']}",
            "documento": fila["documento"],
            "edad": datos["edad"],
            "genero": fila["genero"],
            "sede": fila["sede"],
            **clin,
        })
    if not filas:
        return []
    nuevo = pd.DataFrame(filas)
    if existentes.empty:
        PS._cargar(nuevo)
    else:
        for col in PS.COLUMNAS:
            if col not in existentes.columns:
                existentes[col] = ""
            if col not in nuevo.columns:
                nuevo[col] = ""
        PS._cargar(pd.concat([existentes[PS.COLUMNAS], nuevo[PS.COLUMNAS]], ignore_index=True))
    return out


def _batch_citas_admisiones(pacientes: list[dict], personal: dict, year: int, rng: np.random.Generator) -> dict:
    from paquetes.clinico.citas import CitasServicio as CS
    from paquetes.clinico.admisiones import AdmisionesServicio as AS

    now = _now()
    citas_rows = []
    adm_rows = []
    for i, p in enumerate(pacientes):
        med = personal["medico"][int(rng.integers(0, len(personal["medico"])))]
        day = int(rng.integers(1, 320))
        fecha = (datetime(year, 1, 1) + timedelta(days=day)).strftime("%Y-%m-%d")
        hora = f"{int(rng.integers(8, 17)):02d}:{int(rng.choice([0, 15, 30, 45])):02d}"
        motivo = MOTIVOS[int(rng.integers(0, len(MOTIVOS)))]
        estado_cita = str(rng.choice(["atendida", "atendida", "confirmada", "programada"]))
        citas_rows.append({
            "id_cita": _uid(),
            "id_paciente": p["id_paciente"],
            "paciente_nombre": p["nombre_completo"],
            "medico": med["nombre"],
            "fecha": fecha,
            "hora": hora,
            "estado": estado_cita,
            "motivo": motivo,
            "sede": p.get("sede") or "Sede principal",
            "notas": "",
            "proximo_control": (datetime(year, 1, 1) + timedelta(days=day + 90)).strftime("%Y-%m-%d")
            if estado_cita == "atendida" else "",
            "creado_en": now,
            "actualizado_en": now,
        })
        # ~40% también con admisión (urgencia o ambulatoria)
        if rng.random() < 0.45 or p.get("_diabetes"):
            tipo = "urgencia" if rng.random() < 0.25 else "ambulatoria"
            estado_adm = "alta" if estado_cita == "atendida" else "activa"
            adm_rows.append({
                "id_admision": _uid(),
                "id_paciente": p["id_paciente"],
                "paciente_nombre": p["nombre_completo"],
                "documento": p.get("documento") or "",
                "tipo": tipo,
                "servicio": "Endocrinología" if p.get("_diabetes") else "Medicina interna",
                "medico_id": med["id"],
                "medico_nombre": med["nombre"],
                "sede": p.get("sede") or "Sede principal",
                "habitacion": f"A-{int(rng.integers(101, 320))}" if tipo != "ambulatoria" else "",
                "estado": estado_adm,
                "motivo": motivo,
                "fecha_ingreso": fecha,
                "fecha_egreso": fecha if estado_adm == "alta" else "",
                "notas": "",
                "creado_en": now,
                "actualizado_en": now,
            })
        p["_medico_id"] = med["id"]
        p["_medico_nombre"] = med["nombre"]
        p["_fecha_visita"] = fecha
        p["_encounter"] = f"ENC-{year}-{i + 1:06d}"

    # una sola escritura por store
    if citas_rows:
        df = CS._extraer()
        CS._cargar(pd.concat([df, pd.DataFrame(citas_rows)], ignore_index=True))
    if adm_rows:
        df = AS._extraer()
        AS._cargar(pd.concat([df, pd.DataFrame(adm_rows)], ignore_index=True))
    return {"citas": len(citas_rows), "admisiones": len(adm_rows)}


def _batch_registros_clinicos(pacientes: list[dict], year: int) -> dict:
    """
    Enlaza pacientes con encuentros clínicos **sin añadir filas a stage/**.

    Si el perfil ya viene del dataset generado, reutiliza su `encounter_id`.
    Así pedís 100K y seguís con 100K (no 100K + 800).
    """
    linked = 0
    for i, p in enumerate(pacientes):
        if p.get("_encounter_num") is not None or p.get("_encounter"):
            if p.get("_encounter_num") is None and p.get("_encounter"):
                try:
                    p["_encounter_num"] = int(float(str(p["_encounter"]).split("-")[-1]))
                except Exception:
                    p["_encounter_num"] = i + 1
            linked += 1
            continue
        # Flujo suelto (sin stage previo): IDs solo en memoria para hospital/E2E
        eid = i + 1
        p["_encounter_num"] = eid
        p["_encounter"] = f"ENC-{year}-{eid:05d}"
        linked += 1
    return {"registros": linked, "escritos_stage": 0, "reutilizados": True}


def _vincular_id_paciente_en_stage(stage_path: str, pacientes: list[dict]) -> dict:
    """Anota id_paciente en las filas YA existentes del parquet generado (sin filas nuevas)."""
    if not stage_path or not pacientes:
        return {"vinculados": 0}
    import io
    from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente
    from paquetes.configuracion.ConfiguracionAjustes import MINIO_BUCKET

    c = get_cliente()
    try:
        obj = c.get_object(MINIO_BUCKET, stage_path)
        df = pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return {"vinculados": 0, "error": "No se pudo leer stage para vincular"}

    if df.empty or "encounter_id" not in df.columns:
        return {"vinculados": 0}

    if "id_paciente" not in df.columns:
        df["id_paciente"] = ""
    if "paciente_nombre" not in df.columns:
        df["paciente_nombre"] = ""

    enc_to_idx = {}
    for idx, eid in enumerate(df["encounter_id"].tolist()):
        try:
            enc_to_idx[int(eid)] = idx
        except Exception:
            enc_to_idx[str(eid)] = idx

    vinculados = 0
    for p in pacientes:
        eid = p.get("_encounter_num")
        if eid is None and p.get("_encounter") is not None:
            try:
                eid = int(float(str(p["_encounter"])))
            except Exception:
                eid = p.get("_encounter")
        if eid is None:
            continue
        pos = enc_to_idx.get(int(eid) if not isinstance(eid, str) else eid)
        if pos is None and isinstance(eid, (int, float)):
            pos = enc_to_idx.get(int(eid))
        if pos is None:
            continue
        df.at[pos, "id_paciente"] = str(p["id_paciente"])
        df.at[pos, "paciente_nombre"] = str(p.get("nombre_completo") or "")
        vinculados += 1

    if vinculados:
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        buf.seek(0)
        c.put_object(MINIO_BUCKET, stage_path, buf, buf.getbuffer().nbytes)
    return {"vinculados": vinculados}


def expandir_flujo_operativo(
    cantidad: int = 1000,
    year: int = 2025,
    opts: dict | None = None,
    perfiles_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """
    Crea pacientes + citas + admisiones + registros clínicos y luego el dataset hospitalario
    (negocio/) usando los mismos id_paciente, simulando un flujo ya ejecutado.
    """
    opts = dict(opts or {})
    semilla = opts.get("semilla")
    rng = np.random.default_rng(int(semilla) if semilla is not None else None)

    # Tope operativo: hasta 5K pacientes E2E por corrida (lotes semanales grandes en stage).
    TOPE_PACIENTES = 800 if opts.get("modo_rapido") else 5_000
    n = int(min(max(30, cantidad), TOPE_PACIENTES))
    perfiles: list[dict] = []
    if perfiles_df is not None and not perfiles_df.empty:
        sample = perfiles_df.head(n)
        perfiles = sample.fillna("").to_dict(orient="records")
        n = len(perfiles)
    else:
        # perfiles clínicos mínimos
        for i in range(n):
            diabetes = 1 if rng.random() < float(opts.get("prevalencia_diabetes") or 0.35) else 0
            perfiles.append({
                "year": year,
                "gender": "Female" if rng.random() < 0.55 else "Male",
                "age": int(rng.integers(28, 78)),
                "location": SEDES[int(rng.integers(0, len(SEDES)))],
                "hypertension": int(rng.random() < 0.4),
                "heart_disease": int(rng.random() < 0.2),
                "smoking_history": str(rng.choice(["never", "former", "current", "No Info"])),
                "bmi": float(round(rng.uniform(22, 38), 1)),
                "hbA1c_level": float(round(rng.uniform(5.2, 11.0 if diabetes else 6.2), 1)),
                "blood_glucose_level": float(int(rng.integers(90, 280 if diabetes else 140))),
                "diabetes": diabetes,
                "encounter_id": i + 1,
            })

    personal = _personal()
    pacientes = _crear_pacientes(perfiles, year, rng)
    if not pacientes:
        return {"ok": False, "error": "No se pudieron crear pacientes operativos"}

    clinico = _batch_citas_admisiones(pacientes, personal, year, rng)
    registros = _batch_registros_clinicos(pacientes, year)
    vinculo = {}
    stage_path = opts.get("stage_path")
    if stage_path:
        vinculo = _vincular_id_paciente_en_stage(str(stage_path), pacientes)

    from paquetes.dataset.DatasetHospitalServicio import generar_hospital
    hospital = generar_hospital(
        cantidad,
        year,
        {**opts, "reemplazar_hospital": opts.get("reemplazar_hospital", True)},
        pacientes=pacientes,
        personal=personal,
    )

    # Notificaciones de flujo (muestra)
    try:
        from paquetes.notificaciones.NotificacionesServicio import crear as notif_crear
        notif_crear({
            "titulo": "Flujo sintético generado",
            "mensaje": f"{len(pacientes)} pacientes con citas, registros y módulos hospitalarios.",
            "tipo": "info",
        })
    except Exception:
        pass

    return {
        "ok": True,
        "mensaje": "Flujo operativo expandido (pacientes → clínica → negocio)",
        "pacientes": len(pacientes),
        "citas": clinico.get("citas", 0),
        "admisiones": clinico.get("admisiones", 0),
        "registros_clinicos": registros.get("registros", 0),
        "stage_sin_filas_extra": True,
        "vinculo_stage": vinculo,
        "hospital": hospital,
    }
