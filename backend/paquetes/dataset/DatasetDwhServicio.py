"""
DatasetDwhServicio — materializa el modelo Hecho-Dimensión en MinIO (Principio III).

Lee todos los Parquet en stage/, construye 6 tablas y las persiste en diabcare-app.
"""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone

import pandas as pd

from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente
from paquetes.configuracion.ConfiguracionAjustes import MINIO_BUCKET, MINIO_STAGE_PATH
from paquetes.dataset.DatasetTraducciones import normalizar_genero, normalizar_tabaco

from nucleo.modelos.catalogo.EsquemaDwhHospital import TABLAS, TABLA_POR_ID, listar_por_grupo

BUCKET_APP = "diabcare-app"
PATH_HECHOS = "hechos/hechos_diabetes.parquet"
PATH_DIM_PACIENTE = "dimensiones/dim_paciente.parquet"
PATH_DIM_UBICACION = "dimensiones/dim_ubicacion.parquet"
PATH_DIM_RAZA = "dimensiones/dim_raza.parquet"
PATH_DIM_CONDICION = "dimensiones/dim_condicion.parquet"
PATH_DIM_TIEMPO = "dimensiones/dim_tiempo.parquet"
PATH_META = "dwh/materializacion.json"

RAZA_COLS = [
    "race_AfricanAmerican", "race_Asian", "race_Caucasian",
    "race_Hispanic", "race_Other",
]


def _asegurar_bucket(c):
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)


def _subir_df(c, path: str, df: pd.DataFrame) -> None:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(BUCKET_APP, path, buf, buf.getbuffer().nbytes)


def _leer_df(c, path: str) -> pd.DataFrame:
    try:
        obj = c.get_object(BUCKET_APP, path)
        return pd.read_parquet(io.BytesIO(obj.read()))
    except Exception:
        return pd.DataFrame()


def _leer_stage_plano() -> pd.DataFrame:
    c = get_cliente()
    objetos = list(c.list_objects(MINIO_BUCKET, prefix=MINIO_STAGE_PATH, recursive=True))
    parquets = [o for o in objetos if o.object_name.endswith(".parquet")]
    if not parquets:
        return pd.DataFrame()
    dfs = []
    for o in parquets:
        obj = c.get_object(MINIO_BUCKET, o.object_name)
        dfs.append(pd.read_parquet(io.BytesIO(obj.read())))
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def _normalizar_plano(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    rename = {
        "Gender": "gender", "Age": "age", "BMI": "bmi",
        "HbA1c_level": "hbA1c_level", "HbA1c": "hbA1c_level",
        "Blood_glucose_level": "blood_glucose_level",
        "Diabetes": "diabetes", "Location": "location", "Year": "year",
        "Hypertension": "hypertension", "Heart_disease": "heart_disease",
        "Smoking_history": "smoking_history",
    }
    out = out.rename(columns={k: v for k, v in rename.items() if k in out.columns})
    if "gender" in out.columns:
        out["gender"] = out["gender"].apply(normalizar_genero)
    if "smoking_history" in out.columns:
        out["smoking_history"] = out["smoking_history"].apply(normalizar_tabaco)
    for col in RAZA_COLS:
        if col not in out.columns:
            out[col] = 0
    if "year" not in out.columns:
        out["year"] = 2025
    if "encounter_id" not in out.columns:
        out.insert(0, "encounter_id", range(1, len(out) + 1))
    out = out.dropna(subset=["encounter_id"])
    out["encounter_id"] = out["encounter_id"].astype(int)
    out = out.drop_duplicates(subset=["encounter_id"], keep="last").reset_index(drop=True)
    return out


def _construir_dimensiones(df: pd.DataFrame) -> tuple[pd.DataFrame, ...]:
    """Devuelve (dim_paciente, dim_ubicacion, dim_raza, dim_condicion, dim_tiempo)."""
    pac = df[["gender", "age"]].drop_duplicates().reset_index(drop=True)
    pac.insert(0, "id_paciente", range(1, len(pac) + 1))

    locs = df[["location"]].dropna().drop_duplicates().reset_index(drop=True)
    locs.insert(0, "id_ubicacion", range(1, len(locs) + 1))

    raz = df[RAZA_COLS].drop_duplicates().reset_index(drop=True)
    raz.insert(0, "id_raza", range(1, len(raz) + 1))

    cond_cols = [c for c in ["hypertension", "heart_disease", "smoking_history"] if c in df.columns]
    if not cond_cols:
        cond_cols = ["hypertension", "heart_disease", "smoking_history"]
        for c in cond_cols:
            if c not in df.columns:
                df[c] = 0
    cond = df[cond_cols].drop_duplicates().reset_index(drop=True)
    cond.insert(0, "id_condicion", range(1, len(cond) + 1))

    tiempos = df[["year"]].drop_duplicates().sort_values("year").reset_index(drop=True)
    tiempos.insert(0, "id_tiempo", range(1, len(tiempos) + 1))

    return pac, locs, raz, cond, tiempos


def _construir_hechos(
    df: pd.DataFrame,
    pac: pd.DataFrame,
    locs: pd.DataFrame,
    raz: pd.DataFrame,
    cond: pd.DataFrame,
    tiempos: pd.DataFrame,
) -> pd.DataFrame:
    merged = df.copy()
    merged = merged.merge(pac, on=["gender", "age"], how="left")
    merged = merged.merge(locs, on="location", how="left")
    merged = merged.merge(raz, on=RAZA_COLS, how="left")
    cond_cols = ["hypertension", "heart_disease", "smoking_history"]
    merged = merged.merge(cond, on=cond_cols, how="left")
    merged = merged.merge(tiempos, on="year", how="left")

    cols_hecho = [
        "encounter_id", "year", "age", "bmi", "hbA1c_level", "blood_glucose_level",
        "diabetes", "hypertension", "heart_disease",
        "id_paciente", "id_ubicacion", "id_raza", "id_condicion", "id_tiempo",
    ]
    for c in cols_hecho:
        if c not in merged.columns:
            merged[c] = None
    return merged[cols_hecho].reset_index(drop=True)


def _clasificar_hba1c(v: float) -> str:
    if v < 5.7:
        return "normal"
    if v < 6.5:
        return "prediabetes"
    return "diabetes"


def _clasificar_glucosa(v: float) -> str:
    if v < 100:
        return "normal"
    if v < 126:
        return "prediabetes"
    return "diabetes"


def _nivel_riesgo(row) -> str:
    score = 0
    if float(row.get("bmi") or 0) >= 30:
        score += 1
    if float(row.get("hbA1c_level") or 0) >= 6.5:
        score += 1
    if float(row.get("blood_glucose_level") or 0) >= 126:
        score += 1
    if int(row.get("hypertension") or 0):
        score += 1
    if int(row.get("heart_disease") or 0):
        score += 1
    if score >= 4:
        return "muy_alto"
    if score >= 2:
        return "alto"
    if score >= 1:
        return "moderado"
    return "bajo"


def _materializar_extendido(c, hechos: pd.DataFrame, plano: pd.DataFrame) -> dict[str, int]:
    """Tablas derivadas / esquema hospitalario completo."""
    conteos: dict[str, int] = {}

    # Dim hospital
    hosp = plano[["location"]].drop_duplicates().reset_index(drop=True)
    hosp.insert(0, "id_hospital", range(1, len(hosp) + 1))
    hosp = hosp.rename(columns={"location": "ubicacion"})
    hosp["nombre"] = "Hospital " + hosp["ubicacion"].astype(str)
    hosp["region"] = hosp["ubicacion"]
    _subir_df(c, "dimensiones/dim_hospital.parquet", hosp)
    conteos["dim_hospital"] = len(hosp)

    # Dim edad grupo
    bins = [0, 20, 30, 40, 50, 60, 70, 200]
    labels = ["<20", "20-29", "30-39", "40-49", "50-59", "60-69", "70+"]
    dim_edad = pd.DataFrame({
        "id_edad_grupo": range(1, len(labels) + 1),
        "rango": labels,
        "edad_min": [0, 20, 30, 40, 50, 60, 70],
        "edad_max": [19, 29, 39, 49, 59, 69, 200],
    })
    _subir_df(c, "dimensiones/dim_edad_grupo.parquet", dim_edad)
    conteos["dim_edad_grupo"] = len(dim_edad)

    # Dim genero / tabaco
    gen = plano[["gender"]].drop_duplicates().reset_index(drop=True)
    gen.insert(0, "id_genero", range(1, len(gen) + 1))
    gen = gen.rename(columns={"gender": "genero"})
    _subir_df(c, "dimensiones/dim_genero.parquet", gen)
    conteos["dim_genero"] = len(gen)

    tab = plano[["smoking_history"]].drop_duplicates().reset_index(drop=True)
    tab.insert(0, "id_tabaco", range(1, len(tab) + 1))
    _subir_df(c, "dimensiones/dim_tabaquismo.parquet", tab)
    conteos["dim_tabaquismo"] = len(tab)

    # Dim diagnostico
    dim_diag = pd.DataFrame([
        {"id_diagnostico": 1, "codigo": "E10-E14", "descripcion": "Diabetes mellitus"},
        {"id_diagnostico": 2, "codigo": "R73", "descripcion": "Prediabetes"},
        {"id_diagnostico": 3, "codigo": "Z00", "descripcion": "Sin diabetes"},
    ])
    _subir_df(c, "dimensiones/dim_diagnostico.parquet", dim_diag)
    conteos["dim_diagnostico"] = len(dim_diag)

    # Dim comorbilidad
    com = plano[["hypertension", "heart_disease"]].drop_duplicates().reset_index(drop=True)
    com.insert(0, "id_comorbilidad", range(1, len(com) + 1))
    com["etiqueta"] = com.apply(
        lambda r: f"HT{'+' if r['hypertension'] else '-'} CARD{'+' if r['heart_disease'] else '-'}", axis=1
    )
    _subir_df(c, "dimensiones/dim_comorbilidad.parquet", com)
    conteos["dim_comorbilidad"] = len(com)

    # Dim riesgo metabolico (catalogo fijo)
    dim_riesgo = pd.DataFrame([
        {"id_riesgo": 1, "nivel": "bajo", "bmi_rango": "<25", "hba1c_rango": "<5.7", "glucosa_rango": "<100"},
        {"id_riesgo": 2, "nivel": "moderado", "bmi_rango": "25-29.9", "hba1c_rango": "5.7-6.4", "glucosa_rango": "100-125"},
        {"id_riesgo": 3, "nivel": "alto", "bmi_rango": "≥30", "hba1c_rango": "6.5-7.9", "glucosa_rango": "126-199"},
        {"id_riesgo": 4, "nivel": "muy_alto", "bmi_rango": "≥35", "hba1c_rango": "≥8", "glucosa_rango": "≥200"},
    ])
    _subir_df(c, "dimensiones/dim_riesgo_metabolico.parquet", dim_riesgo)
    conteos["dim_riesgo_metabolico"] = len(dim_riesgo)

    # Esquema: medico y servicio — sincronizar médicos desde P2
    try:
        from paquetes.usuarios.UsuariosServicio import _extraer as extraer_usuarios
        users = extraer_usuarios()
        medicos = users[users["rol"] == "medico"] if not users.empty else pd.DataFrame()
        if not medicos.empty:
            dim_med = pd.DataFrame({
                "id_medico": range(1, len(medicos) + 1),
                "nombre": medicos["nombre"].values,
                "especialidad": "Medicina interna",
                "correo": medicos["email"].values,
            })
            _subir_df(c, "dimensiones/dim_medico.parquet", dim_med)
            conteos["dim_medico"] = len(dim_med)
        else:
            _subir_df(c, "dimensiones/dim_medico.parquet", pd.DataFrame(
                columns=["id_medico", "nombre", "especialidad", "correo"]
            ))
            conteos["dim_medico"] = 0
    except Exception:
        _subir_df(c, "dimensiones/dim_medico.parquet", pd.DataFrame(
            columns=["id_medico", "nombre", "especialidad", "correo"]
        ))
        conteos["dim_medico"] = 0

    _subir_df(c, "dimensiones/dim_servicio.parquet", pd.DataFrame([
        {"id_servicio": 1, "nombre": "Endocrinología", "tipo": "consulta_externa"},
        {"id_servicio": 2, "nombre": "Medicina interna", "tipo": "hospitalizacion"},
        {"id_servicio": 3, "nombre": "Laboratorio clínico", "tipo": "apoyo_diagnostico"},
    ]))
    conteos["dim_servicio"] = 3

    # Hechos prediccion — conservar existentes o vacío
    hp = _leer_df(c, "hechos/hechos_prediccion.parquet")
    conteos["hechos_prediccion"] = len(hp) if not hp.empty else 0

    # Hechos consulta
    locs_df = _leer_df(c, PATH_DIM_UBICACION)
    merged = hechos.merge(locs_df, on="id_ubicacion", how="left").merge(
        hosp, left_on="location", right_on="ubicacion", how="left"
    )
    plano_edad = pd.cut(hechos["age"], bins=bins, labels=labels, right=False)
    edad_map = {labels[i]: i + 1 for i in range(len(labels))}
    hc = pd.DataFrame({
        "encounter_id": hechos["encounter_id"],
        "id_paciente": hechos["id_paciente"],
        "id_hospital": merged["id_hospital"],
        "id_edad_grupo": plano_edad.map(edad_map),
        "clasificacion_hba1c": hechos["hbA1c_level"].apply(_clasificar_hba1c),
        "clasificacion_glucosa": hechos["blood_glucose_level"].apply(_clasificar_glucosa),
        "nivel_riesgo": hechos.apply(_nivel_riesgo, axis=1),
        "diabetes": hechos["diabetes"],
    })
    _subir_df(c, "hechos/hechos_consulta.parquet", hc)
    conteos["hechos_consulta"] = len(hc)

    # Agg prevalencia ubicacion
    if "id_ubicacion" in hechos.columns:
        loc_m = hechos.groupby("id_ubicacion").agg(
            total=("encounter_id", "count"),
            con_diabetes=("diabetes", "sum"),
        ).reset_index()
        loc_m = loc_m.merge(
            _leer_df(c, PATH_DIM_UBICACION)[["id_ubicacion", "location"]], on="id_ubicacion", how="left"
        )
        loc_m["prevalencia_pct"] = (loc_m["con_diabetes"] / loc_m["total"] * 100).round(2)
        _subir_df(c, "agregados/agg_prevalencia_ubicacion.parquet", loc_m)
        conteos["agg_prevalencia_ubicacion"] = len(loc_m)

    # Agg prevalencia edad
    he_edad = hechos.copy()
    he_edad["rango"] = pd.cut(he_edad["age"], bins=bins, labels=labels, right=False)
    edad_m = he_edad.groupby("rango", observed=True).agg(
        total=("encounter_id", "count"),
        con_diabetes=("diabetes", "sum"),
    ).reset_index()
    edad_m["id_edad_grupo"] = edad_m["rango"].map(edad_map)
    edad_m["prevalencia_pct"] = (edad_m["con_diabetes"] / edad_m["total"] * 100).round(2)
    _subir_df(c, "agregados/agg_prevalencia_edad.parquet", edad_m)
    conteos["agg_prevalencia_edad"] = len(edad_m)

    # Agg promedios
    agg_prom = pd.DataFrame([
        {
            "cohorte": "con_diabetes",
            "total": int((hechos["diabetes"] == 1).sum()),
            "bmi_prom": round(hechos.loc[hechos["diabetes"] == 1, "bmi"].mean(), 2),
            "hba1c_prom": round(hechos.loc[hechos["diabetes"] == 1, "hbA1c_level"].mean(), 2),
            "glucosa_prom": round(hechos.loc[hechos["diabetes"] == 1, "blood_glucose_level"].mean(), 1),
        },
        {
            "cohorte": "sin_diabetes",
            "total": int((hechos["diabetes"] == 0).sum()),
            "bmi_prom": round(hechos.loc[hechos["diabetes"] == 0, "bmi"].mean(), 2),
            "hba1c_prom": round(hechos.loc[hechos["diabetes"] == 0, "hbA1c_level"].mean(), 2),
            "glucosa_prom": round(hechos.loc[hechos["diabetes"] == 0, "blood_glucose_level"].mean(), 1),
        },
    ])
    _subir_df(c, "agregados/agg_promedios_clinicos.parquet", agg_prom)
    conteos["agg_promedios_clinicos"] = len(agg_prom)

    # Agg cohorte riesgo
    riesgo_m = hc.groupby("nivel_riesgo").agg(
        total=("encounter_id", "count"),
        pct_diabetes=("diabetes", "mean"),
    ).reset_index()
    riesgo_m["pct_diabetes"] = (riesgo_m["pct_diabetes"] * 100).round(2)
    _subir_df(c, "agregados/agg_cohorte_riesgo.parquet", riesgo_m)
    conteos["agg_cohorte_riesgo"] = len(riesgo_m)

    # Bridge paciente-comorbilidad
    bridge = hechos.merge(com, on=["hypertension", "heart_disease"], how="left")
    br = bridge.groupby(["id_paciente", "id_comorbilidad"]).size().reset_index(name="frecuencia")
    _subir_df(c, "puentes/bridge_paciente_comorbilidad.parquet", br)
    conteos["bridge_paciente_comorbilidad"] = len(br)

    # Alertas desde notificaciones
    try:
        from paquetes.notificaciones import NotificacionesServicio
        notifs = NotificacionesServicio.listar(limit=500).get("notificaciones", [])
        if notifs:
            alertas = pd.DataFrame([
                {
                    "id_alerta": n.get("id", ""),
                    "tipo": n.get("tipo", "info"),
                    "titulo": n.get("titulo", ""),
                    "severidad": n.get("tipo", "info"),
                    "valor_medido": "",
                    "umbral": "7.5",
                    "fecha": n.get("creado_en", ""),
                }
                for n in notifs
            ])
            _subir_df(c, "hechos/hechos_alertas.parquet", alertas)
            conteos["hechos_alertas"] = len(alertas)
        else:
            _subir_df(c, "hechos/hechos_alertas.parquet", pd.DataFrame(
                columns=["id_alerta", "tipo", "titulo", "severidad", "valor_medido", "umbral", "fecha"]
            ))
            conteos["hechos_alertas"] = 0
    except Exception:
        conteos["hechos_alertas"] = 0

    # Catalogos operativos
    _subir_df(c, "catalogo/cat_fuentes.parquet", pd.DataFrame([
        {"id_fuente": 1, "nombre": "generador", "descripcion": "Datos sintéticos P4"},
        {"id_fuente": 2, "nombre": "pocketbase", "descripcion": "Fuente clínica real P8"},
        {"id_fuente": 3, "nombre": "manual", "descripcion": "CRUD registros P3"},
    ]))
    cu_rows = []
    for t in TABLAS:
        for cu in t.cu_o:
            cu_rows.append({
                "cu_o": cu, "oo": t.oo[0] if t.oo else "",
                "paquete": t.paquete, "modulo_ui": t.grupo,
                "estado": t.estado,
            })
    _subir_df(c, "catalogo/cat_casos_uso.parquet", pd.DataFrame(cu_rows).drop_duplicates())
    conteos["cat_fuentes"] = 3
    conteos["cat_casos_uso"] = len(cu_rows)

    return conteos


def materializar_dwh() -> dict:
    """Reconstruye el star schema desde stage/ y lo persiste en diabcare-app."""
    plano = _normalizar_plano(_leer_stage_plano())
    if plano.empty:
        return {"ok": False, "error": "No hay datos en stage/ para materializar"}

    pac, locs, raz, cond, tiempos = _construir_dimensiones(plano)
    hechos = _construir_hechos(plano, pac, locs, raz, cond, tiempos)

    c = get_cliente()
    _asegurar_bucket(c)
    _subir_df(c, PATH_HECHOS, hechos)
    _subir_df(c, PATH_DIM_PACIENTE, pac)
    _subir_df(c, PATH_DIM_UBICACION, locs)
    _subir_df(c, PATH_DIM_RAZA, raz)
    _subir_df(c, PATH_DIM_CONDICION, cond)
    _subir_df(c, PATH_DIM_TIEMPO, tiempos)

    extendido = _materializar_extendido(c, hechos, plano)

    ahora = datetime.now(timezone.utc).isoformat()
    meta = {
        "ultima_materializacion": ahora,
        "filas_stage": len(plano),
        "hechos": len(hechos),
        "dim_paciente": len(pac),
        "dim_ubicacion": len(locs),
        "dim_raza": len(raz),
        "dim_condicion": len(cond),
        "dim_tiempo": len(tiempos),
        "tablas_total": len(TABLAS),
        "tablas_materializadas": extendido,
    }
    body = json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8")
    c.put_object(BUCKET_APP, PATH_META, io.BytesIO(body), len(body), content_type="application/json")

    return {"ok": True, **meta, "extendido": extendido}


def esquema_dwh() -> dict:
    """Catálogo completo del DWH hospitalario + conteos actuales."""
    c = get_cliente()
    tablas = []
    for t in TABLAS:
        filas = len(_leer_df(c, t.path))
        tablas.append({
            "id": t.id,
            "nombre": t.nombre,
            "grupo": t.grupo,
            "path": t.path,
            "descripcion": t.descripcion,
            "cu_o": list(t.cu_o),
            "oo": list(t.oo),
            "paquete": t.paquete,
            "estado_esquema": t.estado,
            "columnas": list(t.columnas),
            "filas": filas,
        })
    por_grupo: dict[str, list] = {}
    for row in tablas:
        por_grupo.setdefault(row["grupo"], []).append(row)
    return {
        "total_tablas": len(tablas),
        "grupos": por_grupo,
        "resumen": resumen_dwh(),
    }


def leer_tabla(tabla_id: str, skip: int = 0, limit: int = 50) -> dict:
    t = TABLA_POR_ID.get(tabla_id)
    if not t:
        return {"datos": [], "total": 0, "error": f"Tabla desconocida: {tabla_id}"}
    c = get_cliente()
    df = _leer_df(c, t.path)
    if df.empty:
        return {"datos": [], "total": 0, "skip": skip, "limit": limit, "tabla": tabla_id, "meta": t.nombre}
    chunk = df.iloc[skip: skip + limit]
    return {
        "datos": chunk.fillna("").to_dict(orient="records"),
        "total": len(df),
        "skip": skip,
        "limit": limit,
        "tabla": tabla_id,
        "meta": t.nombre,
        "columnas": list(t.columnas),
        "cu_o": list(t.cu_o),
    }


def resumen_dwh() -> dict:
    """Conteos de todas las tablas del catálogo + metadata."""
    c = get_cliente()
    conteos = {}
    total_filas = 0
    for t in TABLAS:
        n = len(_leer_df(c, t.path))
        conteos[t.id] = n
        total_filas += n

    meta = {}
    try:
        obj = c.get_object(BUCKET_APP, PATH_META)
        meta = json.loads(obj.read().decode("utf-8"))
    except Exception:
        pass

    stage_total = len(_normalizar_plano(_leer_stage_plano()))
    return {
        "conteos": conteos,
        "total_hechos": conteos.get("hechos_diabetes", 0),
        "total_tablas": len(TABLAS),
        "total_filas_dwh": total_filas,
        "total_stage": stage_total,
        "materializado": conteos.get("hechos_diabetes", 0) > 0,
        "ultima_materializacion": meta.get("ultima_materializacion"),
        "meta": meta,
    }


def leer_hechos(skip: int = 0, limit: int = 50) -> dict:
    c = get_cliente()
    df = _leer_df(c, PATH_HECHOS)
    if df.empty:
        return {"datos": [], "total": 0, "skip": skip, "limit": limit, "fuente": "dwh"}
    total = len(df)
    chunk = df.iloc[skip: skip + limit]
    return {
        "datos": chunk.fillna("").to_dict(orient="records"),
        "total": total,
        "skip": skip,
        "limit": limit,
        "fuente": "dwh",
    }


def leer_dimension(tipo: str, skip: int = 0, limit: int = 50) -> dict:
    paths = {
        "paciente": PATH_DIM_PACIENTE,
        "ubicacion": PATH_DIM_UBICACION,
        "raza": PATH_DIM_RAZA,
        "condicion": PATH_DIM_CONDICION,
        "tiempo": PATH_DIM_TIEMPO,
    }
    path = paths.get(tipo)
    if not path:
        return {"datos": [], "total": 0, "error": f"Dimensión desconocida: {tipo}"}
    c = get_cliente()
    df = _leer_df(c, path)
    if df.empty:
        return {"datos": [], "total": 0, "skip": skip, "limit": limit}
    total = len(df)
    chunk = df.iloc[skip: skip + limit]
    return {"datos": chunk.fillna("").to_dict(orient="records"), "total": total, "skip": skip, "limit": limit}


def compactar_stage() -> dict:
    """Fusiona parquets duplicados en stage/ en un solo archivo sin repetir encounter_id."""
    from paquetes.configuracion.ConfiguracionAjustes import MINIO_BUCKET, MINIO_STAGE_PATH

    c = get_cliente()
    objetos = list(c.list_objects(MINIO_BUCKET, prefix=MINIO_STAGE_PATH, recursive=True))
    parquets = [o for o in objetos if o.object_name.endswith(".parquet")]
    if not parquets:
        return {"error": "No hay archivos en stage/"}

    crudo = _leer_stage_plano()
    filas_crudas = len(crudo)
    df = _normalizar_plano(crudo)
    if df.empty:
        return {"error": "No se pudieron leer registros válidos"}

    destino = f"{MINIO_STAGE_PATH}diabcare_registros.parquet"
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(MINIO_BUCKET, destino, buf, buf.getbuffer().nbytes)

    eliminados = 0
    for o in parquets:
        if o.object_name != destino:
            try:
                c.remove_object(MINIO_BUCKET, o.object_name)
                eliminados += 1
            except Exception:
                pass

    try:
        from paquetes.registros_clinicos.RegistrosClinicosServicio import invalidar_cache
        invalidar_cache()
    except Exception:
        pass

    return {
        "mensaje": "Stage compactado",
        "filas_antes": filas_crudas,
        "filas_unicas": len(df),
        "duplicados_eliminados": max(0, filas_crudas - len(df)),
        "archivos_eliminados": eliminados,
        "archivo": destino,
    }
