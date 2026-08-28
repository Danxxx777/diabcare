# -*- coding: utf-8 -*-
"""Generación sintética de tablas hospitalarias (P16–P20 + comorbilidades) en negocio/."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from nucleo.utilidades.ParquetStore import ParquetStore


def _now() -> str:
    return datetime.utcnow().isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


def _escribir(store: ParquetStore, rows: list[dict]) -> int:
    if not rows:
        store.cargar(pd.DataFrame(columns=store.columnas))
        return 0
    df = pd.DataFrame(rows)
    for col in store.columnas:
        if col not in df.columns:
            df[col] = True if col == "activo" else ""
    store.cargar(df[store.columnas])
    return len(rows)


def _escribir_lote(tareas: list[tuple]) -> dict[str, int]:
    """Escribe varias tablas Parquet en paralelo (I/O MinIO)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    out: dict[str, int] = {}
    if not tareas:
        return out

    def _job(item):
        clave, store, rows = item
        return clave, _escribir(store, rows)

    workers = min(8, max(2, len(tareas)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_job, t) for t in tareas]
        for fut in as_completed(futures):
            clave, n = fut.result()
            out[clave] = n
    return out


def _fecha(rng: np.random.Generator, year: int, day_offset: int = 0) -> str:
    base = datetime(year, 1, 1) + timedelta(days=int(day_offset % 350))
    return base.strftime("%Y-%m-%d")


NOMBRES = [
    "Ana", "Luis", "María", "Carlos", "Elena", "José", "Sofía", "Diego",
    "Paula", "Andrés", "Lucía", "Miguel", "Valeria", "Pedro", "Camila", "Jorge",
]
APELLIDOS = [
    "García", "Rodríguez", "Martínez", "López", "González", "Pérez", "Sánchez",
    "Ramírez", "Torres", "Flores", "Rivera", "Gómez", "Díaz", "Vargas", "Castro",
]


def _asegurar_pacientes(n: int, year: int, rng: np.random.Generator) -> list[str]:
    from paquetes.clinico.pacientes import PacientesServicio as PS
    from paquetes.dataset.DatasetFlujoServicio import _cedula_ecuador, _historia_clinica

    existentes = PS.listar(offset=0, limit=max(n, 500), estado="activo").get("pacientes") or []
    ids = [str(p["id_paciente"]) for p in existentes]
    faltan = max(0, n - len(ids))
    for i in range(faltan):
        cedula = _cedula_ecuador(rng)
        res = PS.crear({
            "codigo": _historia_clinica(year, 1000 + len(ids) + i),
            "nombre": NOMBRES[int(rng.integers(0, len(NOMBRES)))],
            "apellido": APELLIDOS[int(rng.integers(0, len(APELLIDOS)))],
            "documento": cedula,
            "edad": int(rng.integers(25, 80)),
            "genero": "Femenino" if rng.random() < 0.55 else "Masculino",
            "telefono": f"09{int(rng.integers(10000000, 99999999))}",
            "email": f"paciente.{cedula}@demo.diabcare.local",
            "sede": "Quito Centro",
            "notas": "",
        })
        if res.get("id_paciente"):
            ids.append(str(res["id_paciente"]))
    return ids[:n] if ids else [_uid() for _ in range(n)]


def _ids_personal(rng: np.random.Generator) -> dict[str, list[str]]:
    """Personal por rol, desde las cuentas de usuario y la nómina de RRHH.

    Las cuentas suelen ser dos o tres; la nómina tiene decenas de empleados.
    Usar ambas evita que toda la actividad clínica quede firmada por el único
    usuario con rol Médico, y evita inventar identificadores que después no
    corresponden a nadie en el sistema.
    """
    out = {"medico": [], "enfermero": [], "farmaceutico": [], "admin": []}
    try:
        from paquetes.usuarios.UsuariosServicio import listar_activos_por_rol, obtener_usuarios
        for rol, key in [
            ("medico", "medico"),
            ("enfermero", "enfermero"),
            ("farmaceutico", "farmaceutico"),
            ("administrador", "admin"),
        ]:
            rows = listar_activos_por_rol(rol) or []
            out[key] = [str(r["id"]) for r in rows]
        if not out["medico"]:
            todos = obtener_usuarios() or []
            out["medico"] = [str(r["id"]) for r in todos][:5]
    except Exception:
        pass

    # Completar con la nómina de RRHH (empleados activos).
    try:
        from paquetes.rrhh import RrhhServicio as Rh
        nomina = Rh.empleados.extraer(copiar=False)
        if not nomina.empty:
            claves = {"medico": "medico", "enfermero": "enfermero",
                      "farmaceutico": "farmaceutico", "administrador": "admin"}
            for fila in nomina.fillna("").to_dict(orient="records"):
                if str(fila.get("estado_laboral") or "").lower() != "activo":
                    continue
                key = claves.get(str(fila.get("rol_sugerido") or "").lower())
                eid = str(fila.get("id_empleado") or "")
                if key and eid and eid not in out[key]:
                    out[key].append(eid)
    except Exception:
        pass

    for k in out:
        if not out[k]:
            out[k] = [_uid()]
    return out


def nombres_de_personal() -> dict:
    """id -> nombre, uniendo cuentas de usuario y nómina de RRHH."""
    nombres = {}
    try:
        from paquetes.usuarios import UsuariosServicio as U
        padron = U._extraer()
        if not padron.empty and "id" in padron.columns:
            for r in padron.fillna("").to_dict(orient="records"):
                nombre = str(r.get("nombre") or "").strip()
                if nombre:
                    nombres[str(r.get("id"))] = nombre
    except Exception:
        pass
    try:
        from paquetes.rrhh import RrhhServicio as Rh
        nomina = Rh.empleados.extraer(copiar=False)
        if not nomina.empty:
            for r in nomina.fillna("").to_dict(orient="records"):
                completo = (str(r.get("nombre") or "").strip() + " "
                            + str(r.get("apellido") or "").strip()).strip()
                if completo:
                    nombres[str(r.get("id_empleado"))] = completo
    except Exception:
        pass
    return nombres


# -- Fase clinica hospitalaria -------------------------------------------------
# Estas 13 tablas estaban declaradas en el catalogo del DWH pero nadie las
# escribia nunca: el resumen las mostraba en 0 y no habia forma de medir la app
# con el modelo completo. Se derivan de lo operativo cuando existe (admisiones,
# camas, instrumental) y se sintetizan cuando no.

_CIE10 = [
    ("E10.9", "Diabetes mellitus tipo 1 sin complicaciones", "IV Endocrinas"),
    ("E11.9", "Diabetes mellitus tipo 2 sin complicaciones", "IV Endocrinas"),
    ("E11.2", "Diabetes tipo 2 con complicacion renal", "IV Endocrinas"),
    ("E11.3", "Diabetes tipo 2 con complicacion oftalmica", "IV Endocrinas"),
    ("E11.4", "Diabetes tipo 2 con complicacion neurologica", "IV Endocrinas"),
    ("E11.5", "Diabetes tipo 2 con complicacion circulatoria", "IV Endocrinas"),
    ("E66.9", "Obesidad no especificada", "IV Endocrinas"),
    ("I10", "Hipertension esencial", "IX Circulatorio"),
    ("N18.3", "Enfermedad renal cronica estadio 3", "XIV Genitourinario"),
    ("H36.0", "Retinopatia diabetica", "VII Ojo y anexos"),
]

_ESPECIALIDADES = [
    ("Endocrinologia", "Endocrinologia"),
    ("Medicina interna", "Medicina interna"),
    ("Nutricion clinica", "Endocrinologia"),
    ("Nefrologia", "Medicina interna"),
    ("Oftalmologia", "Medicina interna"),
    ("Enfermeria", "Hospitalizacion"),
]

_DEPARTAMENTOS = [
    ("Consulta externa", "asistencial"),
    ("Hospitalizacion", "asistencial"),
    ("Emergencia", "asistencial"),
    ("Laboratorio clinico", "apoyo diagnostico"),
    ("Farmacia", "apoyo terapeutico"),
    ("Admisiones", "administrativo"),
    ("Facturacion", "administrativo"),
    ("Talento humano", "administrativo"),
]

_DIETAS = [
    ("Diabetica 1800 kcal", "Sin azucares simples; 6 tomas"),
    ("Diabetica 1500 kcal", "Sin azucares simples; control de porciones"),
    ("Hiposodica", "Menos de 2 g de sodio al dia"),
    ("Hipoproteica", "Restriccion proteica por dano renal"),
    ("Blanda", "Textura modificada, sin irritantes"),
    ("Liquida amplia", "Solo liquidos claros y espesados"),
    ("Absoluta", "Nada por via oral"),
]

_PROCEDIMIENTOS = [
    ("Fondo de ojo", "H36.0"),
    ("Curacion de pie diabetico", "E11.5"),
    ("Colocacion de via periferica", "E11.9"),
    ("Monitoreo continuo de glucosa", "E11.9"),
    ("Tamizaje de nefropatia", "E11.2"),
    ("Educacion diabetologica", "E11.9"),
]

_INSULINAS = ["NPH", "Glargina", "Regular", "Lispro", "Detemir"]

# (nombre, tipo, area por defecto, unidades)
_EQUIPOS = [
    ("Glucómetro capilar", "dispositivo", "Consulta externa", 6),
    ("Bomba de infusión de insulina", "equipo", "Hospitalización", 4),
    ("Monitor de signos vitales", "equipo", "Hospitalización", 4),
    ("Tensiómetro digital", "dispositivo", "Consulta externa", 5),
    ("Oxímetro de pulso", "dispositivo", "Emergencia", 5),
    ("Balanza con tallímetro", "equipo", "Consulta externa", 2),
    ("Retinógrafo no midriático", "equipo", "Oftalmología", 1),
    ("Doppler vascular portátil", "equipo", "Consulta externa", 2),
    ("Monofilamento Semmes-Weinstein", "instrumental", "Consulta externa", 4),
    ("Diapasón 128 Hz", "instrumental", "Consulta externa", 3),
    ("Set de curación de pie diabético", "instrumental", "Hospitalización", 4),
    ("Electrocardiógrafo de 12 derivaciones", "equipo", "Emergencia", 2),
    ("Bomba de nutrición enteral", "equipo", "Hospitalización", 2),
    ("Carro de paro", "equipo", "Emergencia", 2),
    ("Analizador de HbA1c de mesa", "equipo", "Laboratorio clínico", 1),
    ("Centrífuga de laboratorio", "equipo", "Laboratorio clínico", 2),
    ("Refrigerador de insulinas", "equipo", "Farmacia", 2),
    ("Nevera de cadena de frío", "equipo", "Farmacia", 1),
]


def _store_dwh(archivo: str, columnas: list, id_campo: str, coleccion: str) -> ParquetStore:
    return ParquetStore(archivo, columnas, id_campo, coleccion, modo_borrado="activo")


def _sembrar_instrumental(rng: np.random.Generator, now: str) -> int:
    """Inventario de equipos, con parte asignado a las camas ocupadas.

    Reemplaza lo que haya: el catálogo es determinista y no tiene sentido
    acumular duplicados en cada generación.
    """
    from paquetes.clinico.admisiones import AdmisionesServicio as Adm
    from paquetes.instrumental import InstrumentalServicio as Ins

    # Camas ocupadas ahora mismo, para repartir equipo a pie de cama.
    internados = []
    try:
        df = Adm._extraer(copiar=False)
        if not df.empty:
            for fila in df.fillna("").to_dict(orient="records"):
                if (str(fila.get("tipo")) == "hospitalizacion"
                        and str(fila.get("estado")) == "activa"
                        and str(fila.get("habitacion") or "")):
                    internados.append(fila)
    except Exception:
        pass

    filas = []
    contadores = {"instrumental": 0, "equipo": 0, "dispositivo": 0}
    prefijos = {"instrumental": "INS", "equipo": "EQP", "dispositivo": "DIS"}
    idx_cama = 0
    for nombre, tipo, area, unidades in _EQUIPOS:
        for _ in range(unidades):
            contadores[tipo] += 1
            codigo = "%s-%04d" % (prefijos[tipo], contadores[tipo])
            estado, ubicacion = "disponible", area
            id_admision = id_paciente = paciente_nombre = habitacion = ""
            # A pie de cama: el equipo de hospitalización sigue al internado.
            if area == "Hospitalización" and idx_cama < len(internados):
                adm = internados[idx_cama]
                idx_cama += 1
                estado = "asignado"
                habitacion = str(adm.get("habitacion") or "")
                ubicacion = "Habitación %s" % habitacion
                id_admision = str(adm.get("id_admision") or "")
                id_paciente = str(adm.get("id_paciente") or "")
                paciente_nombre = str(adm.get("paciente_nombre") or "")
            elif rng.random() < 0.12:
                estado, ubicacion = "mantenimiento", "Taller biomédico"
            filas.append({
                "id_instrumental": _uid(), "codigo": codigo, "nombre": nombre,
                "tipo": tipo, "serie": "SN-%06d" % int(rng.integers(1, 999999)),
                "estado": estado, "ubicacion": ubicacion,
                "responsable": "Enfermería" if estado == "asignado" else "",
                "id_admision": id_admision, "id_paciente": id_paciente,
                "paciente_nombre": paciente_nombre, "habitacion": habitacion,
                "existencia": 1, "notas": "", "activo": True,
                "creado_en": now, "actualizado_en": now,
            })

    _escribir(Ins.instrumentos, filas)
    return len(filas)


def generar_fase_clinica(
    rng: np.random.Generator,
    pacientes: list,
    medicos: list,
    year: int,
    now: str,
    fecha_de,
    n_ops: int,
) -> dict:
    """Puebla las tablas clinicas del catalogo DWH que quedaban vacias."""
    from paquetes.clinico.admisiones import AdmisionesServicio as Adm

    medicos = list(medicos) or ["medico-demo"]
    pacientes = list(pacientes)

    # -- Dimensiones de catalogo ---------------------------------------------
    dim_cie10 = [
        {"codigo_cie10": cod, "descripcion": desc, "capitulo": cap,
         "activo": True, "creado_en": now, "actualizado_en": now}
        for cod, desc, cap in _CIE10
    ]
    dim_especialidad = [
        {"id_especialidad": "ESP-%02d" % i, "nombre": nombre, "servicio": serv,
         "activo": True, "creado_en": now, "actualizado_en": now}
        for i, (nombre, serv) in enumerate(_ESPECIALIDADES, start=1)
    ]
    dim_departamento = [
        {"id_departamento": "DEP-%02d" % i, "nombre": nombre, "tipo": tipo,
         "activo": True, "creado_en": now, "actualizado_en": now}
        for i, (nombre, tipo) in enumerate(_DEPARTAMENTOS, start=1)
    ]
    dim_dieta = [
        {"id_dieta": "DIE-%02d" % i, "nombre": nombre, "restricciones": restr,
         "activo": True, "creado_en": now, "actualizado_en": now}
        for i, (nombre, restr) in enumerate(_DIETAS, start=1)
    ]

    # -- Habitaciones: el catalogo real de camas, no uno inventado ------------
    estados_cama = {}
    try:
        for fila in (Adm.listar_camas().get("camas") or []):
            estados_cama[str(fila.get("codigo") or "")] = str(fila.get("estado") or "disponible")
    except Exception:
        pass
    dim_habitacion = []
    for codigo in Adm.CAMAS:
        sufijo = codigo.split("-")[1] if "-" in codigo else codigo
        piso = sufijo[0]
        numero = sufijo[1:] or "1"
        try:
            individual = int(numero) <= 3
        except ValueError:
            individual = True
        dim_habitacion.append({
            "id_habitacion": codigo, "piso": piso, "numero": numero,
            "tipo": "individual" if individual else "compartida",
            "estado": estados_cama.get(codigo, "disponible"),
            "activo": True, "creado_en": now, "actualizado_en": now,
        })

    # Cobertura de seguro para todo el padron, no solo para el lote nuevo.
    try:
        from paquetes.clinico.pacientes import PacientesServicio as Pac
        from paquetes.facturacion import FacturacionServicio as Fact
        todos = [p.get("id_paciente") for p in
                 (Pac.listar(limit=100000).get("pacientes") or [])]
        Fact.asegurar_polizas(todos)
    except Exception:
        pass

    # -- Equipos: sembrar el inventario y luego espejarlo en la dimensión -----
    _sembrar_instrumental(rng, now)
    dim_equipo = []
    try:
        from paquetes.instrumental import InstrumentalServicio as Ins
        for item in (Ins.listar(limit=500).get("instrumentos") or []):
            dim_equipo.append({
                "id_equipo": str(item.get("id_instrumental") or _uid()),
                "nombre": str(item.get("nombre") or "Equipo"),
                "ubicacion": str(item.get("habitacion") or item.get("ubicacion") or "Almacen clinico"),
                "estado_mantenimiento": str(item.get("estado") or "disponible"),
                "activo": True, "creado_en": now, "actualizado_en": now,
            })
    except Exception:
        pass

    # -- Admisiones: hechos derivados de lo operativo -------------------------
    hechos_admision, hechos_hosp = [], []
    try:
        df_adm = Adm._extraer(copiar=False)
    except Exception:
        df_adm = pd.DataFrame()
    if not df_adm.empty:
        for fila in df_adm.fillna("").to_dict(orient="records"):
            ingreso = str(fila.get("fecha_ingreso") or "")[:10]
            egreso = str(fila.get("fecha_egreso") or "")[:10]
            tipo = str(fila.get("tipo") or "ambulatoria")
            hechos_admision.append({
                "id_admision": str(fila.get("id_admision") or _uid()),
                "id_paciente": str(fila.get("id_paciente") or ""),
                "id_servicio": str(fila.get("servicio") or "Medicina interna"),
                "id_hospital": str(fila.get("sede") or "HOSP-001"),
                "tipo": tipo, "fecha_ingreso": ingreso,
                "activo": True, "creado_en": now, "actualizado_en": now,
            })
            if tipo != "hospitalizacion":
                continue
            dias = 0
            if ingreso and egreso:
                try:
                    dias = max(0, (datetime.fromisoformat(egreso) - datetime.fromisoformat(ingreso)).days)
                except ValueError:
                    dias = 0
            hechos_hosp.append({
                "id_estadia": _uid(),
                "id_paciente": str(fila.get("id_paciente") or ""),
                "id_habitacion": str(fila.get("habitacion") or ""),
                "fecha_ingreso": ingreso, "fecha_egreso": egreso,
                "dias_estadia": int(dias),
                "activo": True, "creado_en": now, "actualizado_en": now,
            })

    # -- Ocupacion de camas por dia, a partir de las estadias -----------------
    camas_totales = max(1, len(Adm.CAMAS))
    ocupadas_por_dia = {}
    for est in hechos_hosp:
        f = str(est.get("fecha_ingreso") or "")[:10]
        if f:
            ocupadas_por_dia[f] = ocupadas_por_dia.get(f, 0) + 1
    agg_ocupacion = [
        {
            "fecha": f, "id_hospital": "HOSP-001",
            "camas_totales": camas_totales,
            "camas_ocupadas": min(int(n), camas_totales),
            "pct_ocupacion": round(min(int(n), camas_totales) * 100.0 / camas_totales, 2),
            "activo": True, "creado_en": now, "actualizado_en": now,
        }
        for f, n in sorted(ocupadas_por_dia.items())
    ]

    # -- Medico <-> servicio --------------------------------------------------
    servicios = ["Endocrinologia", "Medicina interna", "Emergencia"]
    bridge_med_serv = [
        {
            "id_medico": mid, "id_servicio": servicios[i % len(servicios)],
            "fecha_desde": "%d-01-01" % year, "fecha_hasta": "",
            "activo": True, "creado_en": now, "actualizado_en": now,
        }
        for i, mid in enumerate(medicos)
    ]

    # -- Hechos sinteticos por paciente ---------------------------------------
    signos, procedimientos, insulina = [], [], []
    muestra = pacientes[: max(30, min(len(pacientes), n_ops))]
    for i, pac in enumerate(muestra):
        fecha = fecha_de(pac, i)
        signos.append({
            "id_registro": _uid(), "id_paciente": pac, "fecha": fecha,
            "presion_sistolica": int(rng.integers(100, 165)),
            "presion_diastolica": int(rng.integers(60, 100)),
            "frecuencia_cardiaca": int(rng.integers(58, 105)),
            "frecuencia_respiratoria": int(rng.integers(12, 22)),
            "temperatura": round(float(rng.uniform(36.0, 38.2)), 1),
            "saturacion": int(rng.integers(92, 100)),
            "activo": True, "creado_en": now, "actualizado_en": now,
        })
        if i % 3 == 0:
            nombre, cod = _PROCEDIMIENTOS[i % len(_PROCEDIMIENTOS)]
            procedimientos.append({
                "id_procedimiento": _uid(), "id_paciente": pac,
                "codigo_cie10": cod, "descripcion": nombre, "fecha": fecha,
                "id_medico": medicos[i % len(medicos)],
                "activo": True, "creado_en": now, "actualizado_en": now,
            })
        if i % 2 == 0:
            insulina.append({
                "id_tratamiento": _uid(), "id_paciente": pac,
                "tipo_insulina": _INSULINAS[i % len(_INSULINAS)],
                "dosis": "%d UI" % int(rng.integers(6, 34)),
                "frecuencia": str(rng.choice(["1/dia", "2/dia", "3/dia"])),
                "fecha_inicio": fecha,
                "activo": True, "creado_en": now, "actualizado_en": now,
            })

    tareas = [
        ("dim_cie10", _store_dwh("dimensiones/dim_cie10.parquet",
            ["codigo_cie10", "descripcion", "capitulo", "activo", "creado_en", "actualizado_en"],
            "codigo_cie10", "cie10"), dim_cie10),
        ("dim_especialidad", _store_dwh("dimensiones/dim_especialidad.parquet",
            ["id_especialidad", "nombre", "servicio", "activo", "creado_en", "actualizado_en"],
            "id_especialidad", "especialidades"), dim_especialidad),
        ("dim_departamento_hospital", _store_dwh("dimensiones/dim_departamento_hospital.parquet",
            ["id_departamento", "nombre", "tipo", "activo", "creado_en", "actualizado_en"],
            "id_departamento", "departamentos"), dim_departamento),
        ("dim_dieta", _store_dwh("dimensiones/dim_dieta.parquet",
            ["id_dieta", "nombre", "restricciones", "activo", "creado_en", "actualizado_en"],
            "id_dieta", "dietas"), dim_dieta),
        ("dim_habitacion", _store_dwh("dimensiones/dim_habitacion.parquet",
            ["id_habitacion", "piso", "numero", "tipo", "estado", "activo", "creado_en", "actualizado_en"],
            "id_habitacion", "habitaciones"), dim_habitacion),
        ("dim_equipo_medico", _store_dwh("dimensiones/dim_equipo_medico.parquet",
            ["id_equipo", "nombre", "ubicacion", "estado_mantenimiento", "activo", "creado_en", "actualizado_en"],
            "id_equipo", "equipos"), dim_equipo),
        ("hechos_admision", _store_dwh("hechos/hechos_admision.parquet",
            ["id_admision", "id_paciente", "id_servicio", "id_hospital", "tipo", "fecha_ingreso",
             "activo", "creado_en", "actualizado_en"],
            "id_admision", "admisiones"), hechos_admision),
        ("hechos_hospitalizacion", _store_dwh("hechos/hechos_hospitalizacion.parquet",
            ["id_estadia", "id_paciente", "id_habitacion", "fecha_ingreso", "fecha_egreso",
             "dias_estadia", "activo", "creado_en", "actualizado_en"],
            "id_estadia", "estadias"), hechos_hosp),
        ("hechos_signos_vitales", _store_dwh("hechos/hechos_signos_vitales.parquet",
            ["id_registro", "id_paciente", "fecha", "presion_sistolica", "presion_diastolica",
             "frecuencia_cardiaca", "frecuencia_respiratoria", "temperatura", "saturacion",
             "activo", "creado_en", "actualizado_en"],
            "id_registro", "signos"), signos),
        ("hechos_procedimiento", _store_dwh("hechos/hechos_procedimiento.parquet",
            ["id_procedimiento", "id_paciente", "codigo_cie10", "descripcion", "fecha", "id_medico",
             "activo", "creado_en", "actualizado_en"],
            "id_procedimiento", "procedimientos"), procedimientos),
        ("hechos_tratamiento_insulina", _store_dwh("hechos/hechos_tratamiento_insulina.parquet",
            ["id_tratamiento", "id_paciente", "tipo_insulina", "dosis", "frecuencia", "fecha_inicio",
             "activo", "creado_en", "actualizado_en"],
            "id_tratamiento", "tratamientos"), insulina),
        ("agg_ocupacion_camas", _store_dwh("agregados/agg_ocupacion_camas.parquet",
            ["fecha", "id_hospital", "camas_totales", "camas_ocupadas", "pct_ocupacion",
             "activo", "creado_en", "actualizado_en"],
            "fecha", "ocupacion"), agg_ocupacion),
        ("bridge_medico_servicio", _store_dwh("puentes/bridge_medico_servicio.parquet",
            ["id_medico", "id_servicio", "fecha_desde", "fecha_hasta",
             "activo", "creado_en", "actualizado_en"],
            "id_medico", "medico_servicio"), bridge_med_serv),
    ]
    return _escribir_lote(tareas)


def generar_hospital(
    cantidad: int = 1000,
    year: int = 2025,
    opts: dict | None = None,
    pacientes: list | None = None,
    personal: dict | None = None,
) -> dict[str, Any]:
    """
    Puebla negocio/ con datos coherentes P16–P20 + comorbilidades.
    Si `pacientes` viene del flujo E2E (lista de dicts con id_paciente), reutiliza esos IDs
    y encounter para simular el mismo recorrido clínico-administrativo.
    """
    opts = dict(opts or {})
    reemplazar = bool(opts.get("reemplazar_hospital", True))
    semilla = opts.get("semilla")
    rng = np.random.default_rng(int(semilla) if semilla is not None else None)

    n_pac = int(min(max(40, cantidad // 8), 5_000))
    # Operaciones negocio: modo rápido reduce densidad (menos filas y menos puts MinIO)
    modo_rapido = bool(opts.get("modo_rapido"))
    tope_ops = 400 if modo_rapido else 2_000
    n_ops = int(min(max(30, cantidad // (20 if modo_rapido else 10)), tope_ops))

    from paquetes.facturacion import FacturacionServicio as F
    from paquetes.farmacia import FarmaciaServicio as Farm
    from paquetes.laboratorio import LaboratorioServicio as Lab
    from paquetes.urgencias import UrgenciasServicio as Urg
    from paquetes.rrhh import RrhhServicio as Rh
    from paquetes.comorbilidades import ComorbilidadesServicio as Com

    # Si no se reemplaza y ya hay medicamentos, salir temprano con conteos actuales
    if not reemplazar and (Farm.medicamentos.listar(limit=1).get("medicamentos") or []):
        return {
            "ok": True,
            "omitido": True,
            "mensaje": "Datos hospitalarios ya existen (reemplazar_hospital=false)",
            "conteos": {},
        }

    # Pacientes: lista de IDs o metadatos del flujo
    pacientes_meta: list[dict] = []
    if pacientes:
        for p in pacientes:
            if isinstance(p, dict):
                pacientes_meta.append(p)
            else:
                pacientes_meta.append({"id_paciente": str(p)})
        paciente_ids = [str(p["id_paciente"]) for p in pacientes_meta]
    else:
        paciente_ids = _asegurar_pacientes(n_pac, year, rng)
        pacientes_meta = [{"id_paciente": pid} for pid in paciente_ids]

    n_ops = min(n_ops, max(len(paciente_ids), 30))

    # Personal: aceptar {rol: [id]} o {rol: [{id,nombre}]}
    if personal and personal.get("medico") and isinstance(personal["medico"][0], dict):
        personal_ids = {
            k: [str(x["id"]) for x in (personal.get(k) or [])] or [_uid()]
            for k in ("medico", "enfermero", "farmaceutico", "admin")
        }
    elif personal:
        personal_ids = {k: list(v) if v else [_uid()] for k, v in personal.items()}
        for k in ("medico", "enfermero", "farmaceutico", "admin"):
            personal_ids.setdefault(k, [_uid()])
    else:
        personal_ids = _ids_personal(rng)

    now = _now()
    conteos: dict[str, int] = {}
    pacientes = paciente_ids  # resto del archivo usa lista de IDs
    personal = personal_ids
    meta_idx = {
        str(m.get("id_paciente")): m
        for m in pacientes_meta
        if isinstance(m, dict) and m.get("id_paciente") is not None
    }

    def _meta(pac_id: str) -> dict:
        return meta_idx.get(str(pac_id), {})

    def _enc(pac_id: str, i: int, suf: str = "") -> str:
        m = _meta(pac_id)
        if m.get("_encounter"):
            return str(m["_encounter"]) + (f"-{suf}" if suf else "")
        if m.get("_encounter_num") is not None:
            return str(m["_encounter_num"])
        return f"ENC-{year}-{i+1:05d}" + (f"-{suf}" if suf else "")

    def _fecha_pac(pac_id: str, i: int) -> str:
        m = _meta(pac_id)
        if m.get("_fecha_visita"):
            return str(m["_fecha_visita"])
        return _fecha(rng, year, i * 3)

    def _medico_pac(pac_id: str) -> str:
        m = _meta(pac_id)
        if m.get("_medico_id"):
            return str(m["_medico_id"])
        return personal["medico"][int(rng.integers(0, len(personal["medico"])))]

    # ── Catálogos base / seeds ──────────────────────────────────────────────
    seguros_rows = [
        {"id_seguro": _uid(), "nombre": "IESS", "cobertura_pct": 80, "activo": True, "creado_en": now, "actualizado_en": now},
        {"id_seguro": _uid(), "nombre": "Particular", "cobertura_pct": 0, "activo": True, "creado_en": now, "actualizado_en": now},
        {"id_seguro": _uid(), "nombre": "Seguros Equinoccial", "cobertura_pct": 60, "activo": True, "creado_en": now, "actualizado_en": now},
    ]
    tarifas = [
        ("CONS-GEN", "Consulta general", 25.0),
        ("CONS-ENDO", "Consulta endocrinología", 45.0),
        ("LAB-HBA1C", "HbA1c laboratorio", 18.0),
        ("URG-TRIAGE", "Triage urgencias", 15.0),
        ("FARM-DISP", "Dispensación farmacia", 5.0),
    ]
    tarifario_rows = [
        {
            "id_tarifa": _uid(), "codigo": c, "descripcion": d, "precio": p,
            "activo": True, "creado_en": now, "actualizado_en": now,
        }
        for c, d, p in tarifas
    ]
    meds_def = [
        ("Insulina NPH", "insulina", "inyectable", 25.0, 12.0, False),
        ("Insulina glargina", "insulina", "inyectable", 38.0, 18.0, False),
        ("Metformina 850mg", "metformina", "tableta", 4.0, 1.2, False),
        ("Glibenclamida 5mg", "glibenclamida", "tableta", 3.5, 1.0, False),
        ("Tiras reactivas", "glucosa", "unidad", 8.5, 3.0, True),
        ("Agujas insulinoterapia", "insumo", "unidad", 2.0, 0.6, True),
        ("Losartán 50mg", "losartan", "tableta", 5.0, 1.5, False),
        ("Atorvastatina 20mg", "atorvastatina", "tableta", 6.5, 2.0, False),
    ]
    med_rows = [
        {
            "id_medicamento": _uid(), "nombre": n, "principio_activo": pa, "forma": forma,
            "precio_venta": pv, "precio_costo": pc, "stock_minimo": 15,
            "venta_libre": libre, "activo": True, "creado_en": now, "actualizado_en": now,
        }
        for n, pa, forma, pv, pc, libre in meds_def
    ]
    prov_rows = [
        {"id_proveedor": _uid(), "nombre": "FarmaAndina S.A.", "ruc": "1790012345001",
         "contacto": "compras@farmaandina.ec", "condiciones_pago": "30 días",
         "activo": True, "creado_en": now, "actualizado_en": now},
        {"id_proveedor": _uid(), "nombre": "MedSupply Ecuador", "ruc": "1790098765001",
         "contacto": "ventas@medsupply.ec", "condiciones_pago": "contado",
         "activo": True, "creado_en": now, "actualizado_en": now},
    ]
    lab_def = [
        ("HBA1C", "HbA1c", "%"),
        ("GLU", "Glucosa en ayunas", "mg/dL"),
        ("CREA", "Creatinina", "mg/dL"),
        ("LIP", "Perfil lipídico", "mg/dL"),
        ("MICRO", "Microalbuminuria", "mg/g"),
    ]
    lab_rows = [
        {
            "id_prueba": _uid(), "codigo": c, "nombre": n, "unidad": u,
            "activo": True, "creado_en": now, "actualizado_en": now,
        }
        for c, n, u in lab_def
    ]
    cargo_names = ["medico_general", "endocrinologo", "enfermero", "farmaceutico", "administrativo"]
    cargo_rows = [
        {"id_cargo": _uid(), "nombre": n, "activo": True, "creado_en": now, "actualizado_en": now}
        for n in cargo_names
    ]
    turno_def = [("mañana", "07:00", "15:00"), ("tarde", "15:00", "23:00"), ("noche", "23:00", "07:00")]
    turno_rows = [
        {
            "id_turno": _uid(), "nombre": n, "hora_inicio": hi, "hora_fin": hf,
            "activo": True, "creado_en": now, "actualizado_en": now,
        }
        for n, hi, hf in turno_def
    ]
    conteos.update(_escribir_lote([
        ("dim_seguro", F.seguros, seguros_rows),
        ("dim_tarifa", F.tarifario, tarifario_rows),
        ("dim_medicamento", Farm.medicamentos, med_rows),
        ("dim_impuesto", Farm.impuestos, [{
            "id_impuesto": _uid(), "nombre": "IVA", "porcentaje": 15,
            "vigente_desde": f"{year}-01-01", "activo": True, "creado_en": now, "actualizado_en": now,
        }]),
        ("dim_proveedor", Farm.proveedores, prov_rows),
        ("dim_laboratorio_prueba", Lab.pruebas, lab_rows),
        ("dim_cargo", Rh.cargos, cargo_rows),
        ("dim_turno", Rh.turnos, turno_rows),
    ]))
    med_ids = [m["id_medicamento"] for m in med_rows]

    # ── Inventario + compras ────────────────────────────────────────────────
    inv_rows, mov_rows, kardex_rows = [], [], []
    for mid in med_ids:
        for lote_i in range(2):
            cant = float(int(rng.integers(40, 200)))
            costo = float(rng.uniform(1.0, 18.0))
            iid = _uid()
            fv = _fecha(rng, year + 1, int(rng.integers(30, 300)))
            inv_rows.append({
                "id_inventario": iid, "id_medicamento": mid, "lote": f"L{year}{lote_i+1}",
                "fecha_vencimiento": fv, "cantidad": cant, "costo_unitario": round(costo, 2),
                "activo": True, "creado_en": now, "actualizado_en": now,
            })
            mov_rows.append({
                "id_movimiento": _uid(), "id_medicamento": mid, "tipo": "entrada",
                "cantidad": cant, "fecha": _fecha(rng, year, int(rng.integers(0, 60))),
                "referencia": "seed", "estado": "registrado", "creado_en": now, "actualizado_en": now,
            })
            kardex_rows.append({
                "id_movimiento_kardex": _uid(), "id_medicamento": mid,
                "fecha": _fecha(rng, year, int(rng.integers(0, 60))),
                "tipo_movimiento": "entrada", "cantidad": cant, "costo_unitario": round(costo, 2),
                "costo_total": round(cant * costo, 2), "saldo_cantidad": cant,
                "saldo_valorizado": round(cant * costo, 2), "referencia": "seed",
                "estado": "registrado", "creado_en": now, "actualizado_en": now,
            })
    conteos.update(_escribir_lote([
        ("oper_inventario", Farm.inventario, inv_rows),
        ("oper_movimientos_inventario", Farm.movimientos, mov_rows),
        ("oper_kardex", Farm.kardex, kardex_rows),
    ]))

    compras_rows, compras_det, cxp_rows = [], [], []
    for i in range(max(5, n_ops // 20)):
        cid = _uid()
        pid = prov_rows[int(rng.integers(0, len(prov_rows)))]["id_proveedor"]
        total = 0.0
        lineas_tmp = []
        for _ in range(int(rng.integers(1, 4))):
            mid = med_ids[int(rng.integers(0, len(med_ids)))]
            cant = float(int(rng.integers(20, 80)))
            pu = float(round(rng.uniform(1.0, 15.0), 2))
            total += cant * pu
            lineas_tmp.append((mid, cant, pu))
        compras_rows.append({
            "id_compra": cid, "id_proveedor": pid,
            "fecha_compra": _fecha(rng, year, int(rng.integers(0, 200))),
            "total": round(total, 2), "estado": "recibida",
            "creado_en": now, "actualizado_en": now,
        })
        for mid, cant, pu in lineas_tmp:
            compras_det.append({
                "id_detalle": _uid(), "id_compra": cid, "id_medicamento": mid,
                "cantidad": cant, "precio_unitario": pu, "lote": f"C{i}",
                "fecha_vencimiento": _fecha(rng, year + 1, 100),
                "estado": "registrado", "creado_en": now, "actualizado_en": now,
            })
        cxp_rows.append({
            "id_cxp": _uid(), "id_compra": cid, "monto_pendiente": round(total * 0.4, 2),
            "fecha_vencimiento": _fecha(rng, year, int(rng.integers(200, 340))),
            "estado": "vigente", "creado_en": now, "actualizado_en": now,
        })
    conteos.update(_escribir_lote([
        ("oper_compras", Farm.compras, compras_rows),
        ("oper_compras_detalle", Farm.compras_detalle, compras_det),
        ("oper_cuentas_por_pagar", Farm.cxp, cxp_rows),
    ]))

    # ── Recetas / dispensaciones / ventas ───────────────────────────────────
    recetas_rows, recetas_det_rows, disp_rows = [], [], []
    for i in range(n_ops):
        rid = _uid()
        pac = pacientes[i % len(pacientes)]
        med = _medico_pac(pac)
        mid = med_ids[int(rng.integers(0, len(med_ids)))]
        fecha = _fecha_pac(pac, i)
        # El estado sigue el ciclo real (emitida -> pagada -> dispensada), no el
        # viejo "pendiente": la bandeja de farmacia filtra por este vocabulario.
        entregada = rng.random() < 0.7
        if entregada:
            estado_receta = "dispensada"
        else:
            sorteo = rng.random()
            estado_receta = "pagada" if sorteo < 0.6 else ("emitida" if sorteo < 0.95 else "anulada")
        recetas_rows.append({
            "id_receta": rid, "id_paciente": pac, "id_medico": med,
            "encounter_id": _enc(pac, i),
            "indicaciones": "Según protocolo diabetes",
            "estado": estado_receta,
            "fecha": fecha, "creado_en": now, "actualizado_en": now,
        })
        recetas_det_rows.append({
            "id_detalle": _uid(), "id_receta": rid, "id_medicamento": mid,
            "dosis": "1 unidad", "frecuencia": "Cada 12 horas", "duracion": "30 días",
            "cantidad": 2.0, "indicaciones": "Administrar según indicación médica",
            "estado": "emitida", "creado_en": now, "actualizado_en": now,
        })
        if entregada and inv_rows:
            lot = inv_rows[int(rng.integers(0, len(inv_rows)))]
            cant = float(int(rng.integers(1, 5)))
            disp_rows.append({
                "id_dispensacion": _uid(), "id_receta": rid, "id_medicamento": mid,
                "id_inventario": lot["id_inventario"], "cantidad": cant,
                "lote": lot["lote"], "fecha": fecha, "estado": "dispensada",
                "creado_en": now, "actualizado_en": now,
            })
    if not disp_rows and recetas_rows and inv_rows:
        receta = recetas_rows[0]
        detalle = recetas_det_rows[0]
        lote = inv_rows[0]
        receta["estado"] = "dispensada"
        disp_rows.append({
            "id_dispensacion": _uid(), "id_receta": receta["id_receta"],
            "id_medicamento": detalle["id_medicamento"],
            "id_inventario": lote["id_inventario"], "cantidad": 1.0,
            "lote": lote["lote"], "fecha": receta["fecha"], "estado": "dispensada",
            "creado_en": now, "actualizado_en": now,
        })
    conteos.update(_escribir_lote([
        ("oper_recetas", Farm.recetas, recetas_rows),
        ("oper_recetas_detalle", Farm.recetas_detalle, recetas_det_rows),
        ("hechos_farmacia_dispensacion", Farm.dispensaciones, disp_rows),
    ]))

    ov_rows, ov_det, ventas_rows, notas_rows = [], [], [], []
    for i in range(max(10, n_ops // 3)):
        oid = _uid()
        pac = pacientes[int(rng.integers(0, len(pacientes)))]
        mid = med_ids[int(rng.integers(0, len(med_ids)))]
        med_row = next(m for m in med_rows if m["id_medicamento"] == mid)
        cant = float(int(rng.integers(1, 4)))
        pu = float(med_row["precio_venta"])
        sub = cant * pu
        fecha = _fecha(rng, year, int(rng.integers(0, 300)))
        ov_rows.append({
            "id_orden_venta": oid, "id_paciente": pac, "tipo": "venta_libre",
            "id_receta": "", "fecha": fecha, "estado": "registrada",
            "creado_en": now, "actualizado_en": now,
        })
        ov_det.append({
            "id_detalle": _uid(), "id_orden_venta": oid, "id_medicamento": mid,
            "cantidad": cant, "precio_unitario": pu, "subtotal": sub,
            "estado": "registrado", "creado_en": now, "actualizado_en": now,
        })
        iva = round(sub * 0.15, 2)
        vid = _uid()
        ventas_rows.append({
            "id_venta": vid, "id_orden_venta": oid, "id_factura": "",
            "total_bruto": sub, "descuento": 0, "iva": iva, "total_neto": round(sub + iva, 2),
            "fecha": fecha, "estado": "registrada", "creado_en": now, "actualizado_en": now,
        })
        if rng.random() < 0.08:
            notas_rows.append({
                "id_nota": _uid(), "tipo": "credito", "id_venta": vid, "id_compra": "",
                "motivo": "Devolución parcial", "monto": round(pu, 2), "fecha": fecha,
                "estado": "emitida", "creado_en": now, "actualizado_en": now,
            })
    if not notas_rows and ventas_rows:
        venta = ventas_rows[0]
        notas_rows.append({
            "id_nota": _uid(), "tipo": "credito", "id_venta": venta["id_venta"],
            "id_compra": "", "motivo": "Ajuste sintético de prueba",
            "monto": 1.0, "fecha": venta["fecha"], "estado": "emitida",
            "creado_en": now, "actualizado_en": now,
        })
    conteos.update(_escribir_lote([
        ("oper_ordenes_venta", Farm.ordenes_venta, ov_rows),
        ("oper_ordenes_venta_detalle", Farm.ordenes_venta_det, ov_det),
        ("hechos_venta_farmacia", Farm.ventas, ventas_rows),
        ("oper_notas_credito_debito", Farm.notas, notas_rows),
    ]))

    cierres_rows = []
    for i in range(max(5, n_ops // 40)):
        ef = float(round(rng.uniform(80, 400), 2))
        tj = float(round(rng.uniform(50, 300), 2))
        sg = float(round(rng.uniform(20, 150), 2))
        esp = ef + tj + sg
        cont = esp + float(round(rng.uniform(-5, 5), 2))
        cierres_rows.append({
            "id_cierre": _uid(), "fecha": _fecha(rng, year, 20 + i * 7),
            "id_personal": personal["farmaceutico"][0],
            "total_ventas_efectivo": ef, "total_ventas_tarjeta": tj,
            "total_ventas_seguro": sg, "monto_esperado": esp, "monto_contado": cont,
            "diferencia": round(cont - esp, 2), "estado": "cerrado",
            "creado_en": now, "actualizado_en": now,
        })
    margen_rows = []
    periodo = f"{year}-Q{(datetime.utcnow().month - 1) // 3 + 1}"
    for m in med_rows:
        ing = float(round(rng.uniform(100, 2000), 2))
        cos = float(round(ing * rng.uniform(0.35, 0.7), 2))
        margen_rows.append({
            "id_agg": _uid(), "id_medicamento": m["id_medicamento"], "periodo": periodo,
            "ingreso_total": ing, "costo_total": cos, "margen": round(ing - cos, 2),
            "creado_en": now, "actualizado_en": now,
        })
    conteos.update(_escribir_lote([
        ("oper_cierre_caja", Farm.cierres, cierres_rows),
        ("agg_margen_farmacia", Farm.margen_agg, margen_rows),
    ]))

    # ── Facturación ─────────────────────────────────────────────────────────
    bridge_rows, fact_rows, det_fact, pagos_rows, comp_rows = [], [], [], [], []
    for i, pac in enumerate(pacientes[:n_ops]):
        seg = seguros_rows[int(rng.integers(0, len(seguros_rows)))]
        if rng.random() < 0.6:
            bridge_rows.append({
                "id_bridge": _uid(), "id_paciente": pac, "id_seguro": seg["id_seguro"],
                "poliza": f"POL-{year}-{i+1:04d}", "activo": True,
                "creado_en": now, "actualizado_en": now,
            })
        fid = _uid()
        tar = tarifario_rows[int(rng.integers(0, len(tarifario_rows)))]
        subtotal = float(tar["precio"]) * float(int(rng.integers(1, 3)))
        descuento = round(subtotal * float(seg["cobertura_pct"]) / 100.0 * 0.5, 2)
        iva = round(max(subtotal - descuento, 0) * 0.15, 2)
        total = round(subtotal - descuento + iva, 2)
        fecha = _fecha_pac(pac, i)
        estado = "pagada" if rng.random() < 0.65 else "emitida"
        fact_rows.append({
            "id_factura": fid, "encounter_id": _enc(pac, i),
            "id_orden_venta": "", "id_paciente": pac, "id_seguro": seg["id_seguro"],
            "subtotal": subtotal, "descuento": descuento, "iva": iva, "total": total,
            "estado": estado, "fecha": fecha, "creado_en": now, "actualizado_en": now,
        })
        det_fact.append({
            "id_detalle": _uid(), "id_factura": fid, "concepto": tar["descripcion"],
            "cantidad": 1, "precio_unitario": float(tar["precio"]), "subtotal": float(tar["precio"]),
            "creado_en": now, "actualizado_en": now,
        })
        if estado == "pagada":
            pagos_rows.append({
                "id_pago": _uid(), "id_factura": fid, "monto": total,
                "metodo": rng.choice(["efectivo", "tarjeta", "transferencia"]),
                "fecha": fecha, "estado": "registrado",
                "creado_en": now, "actualizado_en": now,
            })
            comp_rows.append({
                "id_comprobante": _uid(), "id_factura": fid, "tipo": "factura",
                "autorizacion_sri": f"SIM-{fid[:8]}", "clave_acceso": f"DEMO{fid[:20]}",
                "fecha_autorizacion": fecha, "estado": "autorizado",
                "creado_en": now, "actualizado_en": now,
            })
    if not bridge_rows and pacientes and seguros_rows:
        bridge_rows.append({
            "id_bridge": _uid(), "id_paciente": pacientes[0],
            "id_seguro": seguros_rows[0]["id_seguro"],
            "poliza": f"POL-{year}-0001", "activo": True,
            "creado_en": now, "actualizado_en": now,
        })
    if not pagos_rows and fact_rows:
        factura = fact_rows[0]
        factura["estado"] = "pagada"
        pagos_rows.append({
            "id_pago": _uid(), "id_factura": factura["id_factura"],
            "monto": factura["total"], "metodo": "efectivo",
            "fecha": factura["fecha"], "estado": "registrado",
            "creado_en": now, "actualizado_en": now,
        })
        comp_rows.append({
            "id_comprobante": _uid(), "id_factura": factura["id_factura"],
            "tipo": "factura", "autorizacion_sri": f"SIM-{factura['id_factura'][:8]}",
            "clave_acceso": f"DEMO{factura['id_factura'][:20]}",
            "fecha_autorizacion": factura["fecha"], "estado": "autorizado",
            "creado_en": now, "actualizado_en": now,
        })
    conteos.update(_escribir_lote([
        ("bridge_paciente_seguro", F.bridge_seguro, bridge_rows),
        ("hechos_facturacion", F.facturas, fact_rows),
        ("oper_facturas_detalle", F.detalle, det_fact),
        ("oper_pagos", F.pagos, pagos_rows),
        ("oper_comprobantes_electronicos", Farm.comprobantes, comp_rows),
    ]))

    # Retenciones (tabla auxiliar negocio, sin CRUD dedicado)
    ret_store = ParquetStore(
        "negocio/oper_retenciones.parquet",
        ["id_retencion", "id_factura", "tipo", "base", "porcentaje", "monto",
         "fecha", "estado", "creado_en", "actualizado_en"],
        "id_retencion", "retenciones", modo_borrado="estado",
    )
    ret_rows = []
    for f in fact_rows[: max(3, len(fact_rows) // 8)]:
        base = float(f["subtotal"])
        pct = 1.75
        ret_rows.append({
            "id_retencion": _uid(), "id_factura": f["id_factura"], "tipo": "renta",
            "base": base, "porcentaje": pct, "monto": round(base * pct / 100, 2),
            "fecha": f["fecha"], "estado": "registrada",
            "creado_en": now, "actualizado_en": now,
        })
    costo_rows = [
        {
            "id_agg": _uid(), "periodo": periodo, "servicio": s,
            "costo_total": float(round(rng.uniform(500, 5000), 2)),
            "facturado_total": float(round(rng.uniform(800, 8000), 2)),
            "margen": 0, "creado_en": now, "actualizado_en": now,
        }
        for s in ["consulta", "laboratorio", "farmacia", "urgencias"]
    ]
    for r in costo_rows:
        r["margen"] = round(float(r["facturado_total"]) - float(r["costo_total"]), 2)
    conteos.update(_escribir_lote([
        ("oper_retenciones", ret_store, ret_rows),
        ("agg_costo_servicio", F.agg_costo, costo_rows),
    ]))

    # ── Laboratorio ─────────────────────────────────────────────────────────
    orden_rows, res_rows = [], []
    for i in range(n_ops):
        oid = _uid()
        pac = pacientes[i % len(pacientes)]
        pr = lab_rows[int(rng.integers(0, len(lab_rows)))]
        med = _medico_pac(pac)
        fecha = _fecha_pac(pac, i)
        done = rng.random() < 0.75
        orden_rows.append({
            "id_orden": oid, "id_paciente": pac, "id_prueba": pr["id_prueba"],
            "id_medico": med, "encounter_id": _enc(pac, i, "LAB"),
            "estado": "completada" if done else "pendiente",
            "fecha": fecha, "creado_en": now, "actualizado_en": now,
        })
        if done:
            if pr["codigo"] == "HBA1C":
                valor = f"{rng.uniform(5.2, 11.5):.1f}"
            elif pr["codigo"] == "GLU":
                valor = str(int(rng.integers(70, 280)))
            else:
                valor = f"{rng.uniform(0.5, 2.5):.2f}"
            # Preferir métricas del perfil clínico si existen
            m = _meta(pac)
            if pr["codigo"] == "HBA1C" and m.get("_hba1c") is not None:
                valor = f"{float(m['_hba1c']):.1f}"
            if pr["codigo"] == "GLU" and m.get("_glucosa") is not None:
                valor = str(int(float(m["_glucosa"])))
            res_rows.append({
                "id_resultado": _uid(), "id_orden": oid, "id_paciente": pac,
                "id_prueba": pr["id_prueba"], "valor": valor, "unidad": pr["unidad"],
                "fecha": fecha, "estado": "registrado",
                "creado_en": now, "actualizado_en": now,
            })
    conteos.update(_escribir_lote([
        ("oper_ordenes_lab", Lab.ordenes, orden_rows),
        ("hechos_laboratorio", Lab.resultados, res_rows),
    ]))

    # ── Urgencias ───────────────────────────────────────────────────────────
    urg_rows = []
    esperas = []
    for i in range(max(15, n_ops // 2)):
        uid = _uid()
        pac = pacientes[int(rng.integers(0, len(pacientes)))]
        triage = rng.choice(["I", "II", "III", "IV", "V"], p=[0.05, 0.15, 0.4, 0.25, 0.15])
        llegada = datetime(year, 1, 1) + timedelta(days=int(rng.integers(0, 300)), hours=int(rng.integers(0, 23)))
        atendida = rng.random() < 0.8
        espera_min = int(rng.integers(5, 120))
        hora_at = (llegada + timedelta(minutes=espera_min)).isoformat() if atendida else ""
        urg_rows.append({
            "id_urgencia": uid, "id_paciente": pac, "triage": triage,
            "motivo": rng.choice(["Hipoglucemia", "Cetoacidosis", "Herida pie diabético", "Dolor torácico", "Malestar general"]),
            "id_enfermero": personal["enfermero"][0],
            "id_medico": personal["medico"][0] if atendida else "",
            "hora_llegada": llegada.isoformat(), "hora_atencion": hora_at,
            "desenlace": "alta" if atendida else "en_espera",
            "estado": "atendida" if atendida else "triage",
            "creado_en": now, "actualizado_en": now,
        })
        if atendida:
            esperas.append(espera_min)
    agg_esp = [{
        "id_agg": _uid(), "periodo": periodo,
        "espera_promedio_min": round(float(np.mean(esperas)) if esperas else 0, 1),
        "total_urgencias": len(urg_rows),
        "creado_en": now, "actualizado_en": now,
    }]
    conteos.update(_escribir_lote([
        ("hechos_emergencia", Urg.urgencias, urg_rows),
        ("agg_tiempos_espera", Urg.agg_espera, agg_esp),
    ]))

    # ── Comorbilidades ──────────────────────────────────────────────────────
    tipos = ["retinopatia", "nefropatia", "neuropatia", "cardiovascular", "pie_diabetico"]
    severidades = ["leve", "moderada", "severa"]
    # La severa se controla y se cita antes; la leve puede quedar resuelta.
    notas_por_tipo = {
        "retinopatia": "Control oftalmológico anual; fondo de ojo en la última visita.",
        "nefropatia": "Microalbuminuria en seguimiento; ajustar IECA.",
        "neuropatia": "Exploración con monofilamento; educación en cuidado de pies.",
        "cardiovascular": "Riesgo cardiovascular alto; control de perfil lipídico.",
        "pie_diabetico": "Curaciones programadas; vigilar signos de infección.",
    }
    com_rows = []
    for idx, pac in enumerate(pacientes[: max(20, n_pac // 2)]):
        if rng.random() >= 0.55:
            continue
        tipo = tipos[int(rng.integers(0, len(tipos)))]
        severidad = severidades[int(rng.integers(0, len(severidades)))]
        sorteo = rng.random()
        if severidad == "severa":
            estado = "activa" if sorteo < 0.8 else "controlada"
            dias_control = 30
        elif severidad == "moderada":
            estado = "activa" if sorteo < 0.5 else ("controlada" if sorteo < 0.9 else "resuelta")
            dias_control = 90
        else:
            estado = "controlada" if sorteo < 0.5 else ("resuelta" if sorteo < 0.85 else "activa")
            dias_control = 180
        dia = int(rng.integers(0, 280))
        deteccion = _fecha(rng, year, dia)
        com_rows.append({
            "id_comorbilidad": _uid(), "id_paciente": pac,
            "tipo": tipo,
            "severidad": severidad,
            "fecha_deteccion": deteccion,
            # Una complicación resuelta ya no necesita control programado.
            "proximo_control": "" if estado == "resuelta" else _fecha(rng, year, dia + dias_control),
            "id_medico": personal["medico"][idx % len(personal["medico"])],
            "notas": notas_por_tipo.get(tipo, ""), "estado": estado,
            "creado_en": now, "actualizado_en": now,
        })
    if not com_rows and pacientes:
        com_rows.append({
            "id_comorbilidad": _uid(), "id_paciente": pacientes[0],
            "tipo": "neuropatia", "fecha_deteccion": f"{year}-01-15",
            "id_medico": personal["medico"][0], "notas": "Registro sintético",
            "estado": "activa", "creado_en": now, "actualizado_en": now,
        })

    # ── RRHH ────────────────────────────────────────────────────────────────
    pers_rows, asg_rows, prod_rows = [], [], []
    staff_ids = list({*personal["medico"], *personal["enfermero"], *personal["farmaceutico"]})
    for sid in staff_ids:
        cargo = cargo_rows[int(rng.integers(0, len(cargo_rows)))]["id_cargo"]
        pers_rows.append({
            "id_personal_costo": _uid(), "id_personal": sid, "id_cargo": cargo,
            "costo_hora": float(round(rng.uniform(8, 35), 2)),
            "fecha_vigencia": f"{year}-01-01", "activo": True,
            "creado_en": now, "actualizado_en": now,
        })
        asg_rows.append({
            "id_bridge": _uid(), "id_personal": sid,
            "id_turno": turno_rows[int(rng.integers(0, len(turno_rows)))]["id_turno"],
            "fecha": _fecha(rng, year, int(rng.integers(0, 30))),
            "activo": True, "creado_en": now, "actualizado_en": now,
        })
        prod_rows.append({
            "id_agg": _uid(), "id_personal": sid, "periodo": periodo,
            "num_consultas": int(rng.integers(20, 180)),
            "num_procedimientos": int(rng.integers(0, 40)),
            "ingreso_generado": float(round(rng.uniform(500, 8000), 2)),
            "creado_en": now, "actualizado_en": now,
        })
    conteos.update(_escribir_lote([
        ("oper_comorbilidades_paciente", Com.comorbilidades, com_rows),
        ("oper_personal_costo", Rh.personal, pers_rows),
        ("bridge_personal_turno", Rh.bridge_turno, asg_rows),
        ("agg_productividad_medica", Rh.productividad, prod_rows),
    ]))

    # Bridge tratamiento-medicamento (catálogo DWH)
    bridge_tx = ParquetStore(
        "negocio/bridge_tratamiento_medicamento.parquet",
        ["id_bridge", "id_tratamiento", "id_medicamento", "dosis", "frecuencia",
         "activo", "creado_en", "actualizado_en"],
        "id_bridge", "bridges_tx", modo_borrado="activo",
    )
    tx_rows = []
    for i in range(max(10, n_ops // 10)):
        tx_rows.append({
            "id_bridge": _uid(), "id_tratamiento": f"TX-{year}-{i+1}",
            "id_medicamento": med_ids[int(rng.integers(0, len(med_ids)))],
            "dosis": rng.choice(["1 tab", "10 UI", "850 mg"]),
            "frecuencia": rng.choice(["1/día", "2/día", "con comidas"]),
            "activo": True, "creado_en": now, "actualizado_en": now,
        })

    # Ranking top medicamentos
    top_store = ParquetStore(
        "negocio/agg_medicamentos_top.parquet",
        ["id_agg", "id_medicamento", "nombre", "total_dispensaciones", "periodo",
         "creado_en", "actualizado_en"],
        "id_agg", "tops", modo_borrado="activo",
    )
    from collections import Counter
    cnt = Counter(d["id_medicamento"] for d in disp_rows)
    top_rows = []
    for mid, total in cnt.most_common(8):
        nombre = next((m["nombre"] for m in med_rows if m["id_medicamento"] == mid), mid)
        top_rows.append({
            "id_agg": _uid(), "id_medicamento": mid, "nombre": nombre,
            "total_dispensaciones": int(total), "periodo": periodo,
            "creado_en": now, "actualizado_en": now,
        })
    conteos.update(_escribir_lote([
        ("bridge_tratamiento_medicamento", bridge_tx, tx_rows),
        ("agg_medicamentos_top", top_store, top_rows),
    ]))

    # Tablas clinicas del catalogo DWH (camas, equipos, estadias, signos, CIE-10).
    # Sin esto quedaban declaradas en el esquema y siempre en cero.
    conteos.update(generar_fase_clinica(
        rng=rng,
        pacientes=pacientes,
        medicos=personal["medico"],
        year=year,
        now=now,
        fecha_de=_fecha_pac,
        n_ops=n_ops,
    ))

    tablas_vacias = sorted(k for k, v in conteos.items() if int(v or 0) <= 0)
    return {
        "ok": True,
        "mensaje": "Datos hospitalarios generados en negocio/",
        "pacientes": len(pacientes),
        "tablas": len(conteos),
        "filas_total": int(sum(conteos.values())),
        "conteos": conteos,
        "cobertura": {
            "pobladas": len(conteos) - len(tablas_vacias),
            "total": len(conteos),
            "vacias": tablas_vacias,
            "completa": not tablas_vacias,
        },
        "modo_rapido": modo_rapido,
        "year": year,
        "periodo": periodo,
    }
