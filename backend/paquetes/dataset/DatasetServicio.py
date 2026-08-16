import io
import os
import tempfile
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente
from paquetes.configuracion.ConfiguracionAjustes import MINIO_BUCKET, MINIO_STAGE_PATH

UBICACIONES = [
    "Alabama", "California", "Texas", "Florida", "Nueva York",
    "Georgia", "Ohio", "Michigan", "Arizona", "Nevada",
    "Colorado", "Washington", "Oregón", "Illinois", "Pensilvania",
]

RAZAS = {
    "race_AfricanAmerican": 0,
    "race_Asian": 0,
    "race_Caucasian": 0,
    "race_Hispanic": 0,
    "race_Other": 0,
}

HISTORIAL_TABAQUISMO = ["nunca", "actual", "no actual", "anterior", "Sin información"]

GENEROS = ["Masculino", "Femenino", "Otro"]

MAX_REGISTROS_GENERACION = 10_000_000
CHUNK_GENERACION = 1_000_000
RAZA_KEYS = list(RAZAS.keys())


def _invalidar_cache_registros():
    try:
        from paquetes.registros_clinicos import RegistrosClinicosServicio
        RegistrosClinicosServicio.invalidar_cache()
    except Exception:
        pass


def fusionar_stage_dataframes(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """Une Parquets de stage/ remapeando encounter_id si colisionan entre archivos.

    Cada lote del generador suele reiniciar IDs en 1…N; un drop_duplicates
    dejaba solo ~N filas aunque hubiera 1.1M en disco.
    """
    partes: list[pd.DataFrame] = []
    max_id = 0
    for df in dfs:
        if df is None or df.empty:
            continue
        d = df.copy()
        if "encounter_id" not in d.columns:
            d.insert(0, "encounter_id", range(max_id + 1, max_id + 1 + len(d)))
        else:
            ids = pd.to_numeric(d["encounter_id"], errors="coerce")
            d = d.loc[ids.notna()].copy()
            if d.empty:
                continue
            d["encounter_id"] = ids.loc[ids.notna()].astype("int64")
            mn = int(d["encounter_id"].min())
            if max_id > 0 and mn <= max_id:
                d["encounter_id"] = d["encounter_id"] + (max_id + 1 - mn)
        d = d.drop_duplicates(subset=["encounter_id"], keep="last")
        if d.empty:
            continue
        max_id = int(d["encounter_id"].max())
        partes.append(d)
    if not partes:
        return pd.DataFrame()
    out = pd.concat(partes, ignore_index=True)
    return out.drop_duplicates(subset=["encounter_id"], keep="last").reset_index(drop=True)


def max_encounter_id_en_stage() -> int:
    """Máximo encounter_id efectivo (con el mismo remapeo que la fusión)."""
    import pyarrow.parquet as pq

    c = get_cliente()
    objetos = [
        o for o in c.list_objects(MINIO_BUCKET, prefix=MINIO_STAGE_PATH, recursive=True)
        if o.object_name.endswith(".parquet")
    ]
    objetos = sorted(objetos, key=lambda o: o.object_name)
    max_id = 0
    for o in objetos:
        try:
            data = c.get_object(MINIO_BUCKET, o.object_name).read()
            pf = pq.ParquetFile(io.BytesIO(data))
            names = set(pf.schema_arrow.names)
            if "encounter_id" not in names:
                max_id += pf.metadata.num_rows
                continue
            mn = mx = None
            for batch in pf.iter_batches(columns=["encounter_id"], batch_size=500_000):
                s = batch.column(0).to_pandas()
                s = pd.to_numeric(s, errors="coerce").dropna().astype("int64")
                if s.empty:
                    continue
                bmin, bmax = int(s.min()), int(s.max())
                mn = bmin if mn is None else min(mn, bmin)
                mx = bmax if mx is None else max(mx, bmax)
            if mn is None or mx is None:
                continue
            if max_id > 0 and mn <= max_id:
                max_id = max_id + (mx - mn + 1)
            else:
                max_id = max(max_id, mx)
        except Exception:
            continue
    return int(max_id)


def _rng(opts: dict):
    semilla = opts.get("semilla")
    if semilla is not None:
        return np.random.default_rng(int(semilla))
    return np.random.default_rng()


def _sigmoide(x):
    return 1.0 / (1.0 + np.exp(-x))


def _sesgo_perfil(perfil: str) -> tuple[float, float, float]:
    """
    (BMI base, prevalencia objetivo, desplazamiento de HbA1c) por perfil.

    La prevalencia se fija como objetivo y se alcanza calibrando el intercepto,
    no ajustandolo a ojo: asi el numero es exacto y sigue dependiendo de los
    factores de riesgo. El 11 % del perfil clinico es el orden de magnitud real
    de diabetes en poblacion adulta; el 74 % anterior era imposible.
    """
    if perfil == "alto_riesgo":
        return 31.0, 0.42, 0.3
    if perfil == "bajo_riesgo":
        return 23.5, 0.03, -0.2
    if perfil == "balanceado":
        return 27.5, 0.40, 0.0
    return 27.0, 0.11, 0.0


def _desplazar_a_prevalencia(logit: np.ndarray, objetivo: float) -> float:
    """
    Constante que lleva la prevalencia media del lote al objetivo pedido.

    Permite fijar la prevalencia sin perder la estructura: los factores de
    riesgo siguen ordenando quién tiene más probabilidad, solo se mueve el
    nivel general. Sortear la etiqueta al azar con p=objetivo, como se hacia
    antes, borraba toda relacion con edad, BMI y comorbilidades.
    """
    muestra = logit if logit.size <= 20000 else logit[:20000]
    bajo, alto = -12.0, 12.0
    for _ in range(40):
        medio = (bajo + alto) / 2
        if _sigmoide(muestra + medio).mean() < objetivo:
            bajo = medio
        else:
            alto = medio
    return (bajo + alto) / 2


def _generar_chunk_table(n: int, year: int, opts: dict, rng: np.random.Generator, offset: int = 0):
    """Generación vectorizada — órdenes de magnitud más rápida que fila a fila."""
    import pyarrow as pa

    edad_min = float(opts.get("edad_min") or 1)
    edad_max = float(opts.get("edad_max") or 80)
    genero = opts.get("genero")
    ubicacion = opts.get("ubicacion")
    prevalencia = opts.get("prevalencia_diabetes")
    perfil = opts.get("perfil") or "aleatorio"

    age = np.round(rng.uniform(edad_min, edad_max, n), 1)
    smoking = rng.choice(HISTORIAL_TABAQUISMO, n)

    # ── Antropometría y comorbilidades, dependientes de la edad ──
    # El BMI sube con la edad y la hipertensión sube con el BMI: si se sortean
    # sueltos, ningún corte demográfico muestra diferencia y todas las gráficas
    # salen planas.
    bmi_base, prev_perfil, glc_off = _sesgo_perfil(perfil)
    bmi = np.clip(rng.normal(bmi_base + 0.045 * (age - 40), 4.2, n), 15.0, 50.0)
    p_hiper = _sigmoide(-3.4 + 0.045 * (age - 45) + 0.085 * (bmi - 27))
    hiper = (rng.random(n) < p_hiper).astype(np.int8)
    p_cardio = _sigmoide(-4.6 + 0.055 * (age - 45) + 0.05 * (bmi - 27) + 0.7 * hiper)
    cardio = (rng.random(n) < p_cardio).astype(np.int8)
    fuma = np.isin(smoking, ("actual", "current")).astype(np.int8)

    # ── Diabetes a partir del riesgo, NO de los análisis ──
    # Antes la etiqueta era `hba1c > 6.5 or glucosa > 200` sobre valores
    # uniformes: el 70 % daba positivo por construcción, ningún factor
    # discriminaba y el modelo ML "acertaba" repitiendo el umbral.
    logit = (
        -5.9
        + 0.052 * (age - 45)
        + 0.115 * (bmi - 27)
        + 0.80 * hiper
        + 0.55 * cardio
        + 0.35 * fuma
    )
    objetivo = float(prevalencia) if prevalencia is not None else prev_perfil
    logit = logit + _desplazar_a_prevalencia(logit, max(0.001, min(0.999, objetivo)))
    diabetes = (rng.random(n) < _sigmoide(logit)).astype(np.int8)

    # ── Análisis condicionados al diagnóstico ──
    # Se solapan a propósito: sin solape el modelo separa perfecto y la métrica
    # deja de significar nada.
    # El solape es clinico, no ruido: una parte de los diabeticos esta bien
    # controlada (HbA1c < 7) y una parte de los no diabeticos es prediabetica
    # (5,7-6,4). Sin ese cruce el modelo solo reaprende el umbral diagnostico y
    # la metrica no dice nada del modelo.
    hba1c = np.where(
        diabetes == 1,
        rng.normal(7.35, 1.55, n),
        rng.normal(5.50, 0.62, n),
    )
    glucosa = np.where(
        diabetes == 1,
        rng.normal(168, 52, n),
        rng.normal(112, 26, n),
    )
    bmi = np.round(np.where(diabetes == 1, bmi + rng.normal(2.6, 1.0, n), bmi), 2)
    bmi = np.clip(bmi, 15.0, 50.0)
    hba1c = np.round(np.clip(hba1c + glc_off, 3.5, 15.0), 1)
    glucosa = np.clip(glucosa, 70, 400).astype(np.int16)

    if genero in GENEROS:
        gender = np.full(n, genero, dtype=object)
    else:
        gender = rng.choice(GENEROS, n)

    if ubicacion:
        location = np.full(n, ubicacion, dtype=object)
    else:
        location = rng.choice(UBICACIONES, n)

    race_idx = rng.integers(0, len(RAZA_KEYS), n)

    columns = {
        "encounter_id": pa.array(np.arange(offset + 1, offset + n + 1, dtype=np.int64)),
        "year": pa.array(np.full(n, year, dtype=np.int16)),
        "gender": pa.array(gender),
        "age": pa.array(age, type=pa.float32()),
        "location": pa.array(location),
        "hypertension": pa.array(hiper),
        "heart_disease": pa.array(cardio),
        "smoking_history": pa.array(smoking),
        "bmi": pa.array(bmi, type=pa.float32()),
        "hbA1c_level": pa.array(hba1c, type=pa.float32()),
        "blood_glucose_level": pa.array(glucosa, type=pa.int16()),
        "diabetes": pa.array(diabetes),
    }
    for i, key in enumerate(RAZA_KEYS):
        columns[key] = pa.array((race_idx == i).astype(np.int8))

    return pa.table(columns)


def generar_registro(year: int, opts: dict | None = None) -> dict:
    opts = dict(opts or {})
    rng = _rng(opts)
    df = _generar_chunk_table(1, year, opts, rng).to_pandas()
    return df.iloc[0].to_dict()


def generar_y_subir(cantidad: int = 100000, year: int = 2025, opts: dict | None = None) -> dict:
    opts = dict(opts or {})
    if cantidad < 1:
        return {"error": "La cantidad debe ser al menos 1"}
    if cantidad > MAX_REGISTROS_GENERACION:
        return {
            "error": f"Máximo {MAX_REGISTROS_GENERACION:,} registros por lote".replace(",", "."),
        }

    tmp_path = None
    try:
        import pyarrow.parquet as pq

        rng = _rng(opts)
        fd, tmp_path = tempfile.mkstemp(suffix=".parquet")
        os.close(fd)

        # Continuar IDs tras lo ya presente en stage/ (evita colisiones 1…N por lote)
        try:
            id_base = max_encounter_id_en_stage()
        except Exception:
            id_base = 0

        writer = None
        generados = 0
        while generados < cantidad:
            n = min(CHUNK_GENERACION, cantidad - generados)
            table = _generar_chunk_table(n, year, opts, rng, offset=id_base + generados)
            if writer is None:
                writer = pq.ParquetWriter(
                    tmp_path,
                    table.schema,
                    compression="snappy",
                    use_dictionary=True,
                )
            writer.write_table(table)
            generados += n

        if writer is not None:
            writer.close()

        perfil = opts.get("perfil") or "aleatorio"
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archivo = f"{MINIO_STAGE_PATH}sinteticos_{perfil}_{year}_{timestamp}.parquet"
        c = get_cliente()
        tamano = os.path.getsize(tmp_path)
        with open(tmp_path, "rb") as f:
            c.put_object(MINIO_BUCKET, archivo, f, tamano)

        _invalidar_cache_registros()
        dwh = {}
        try:
            from paquetes.dataset.DatasetDwhServicio import materializar_dwh
            import pyarrow.parquet as pq
            # Evita re-descargar de MinIO el archivo que acabamos de subir si es el único en stage
            otros = [
                o for o in _listar_parquets_ordenados()
                if o.object_name != archivo
            ]
            if not otros and tmp_path and os.path.exists(tmp_path):
                plano = pq.read_table(tmp_path).to_pandas()
                dwh = materializar_dwh(plano=plano)
            else:
                dwh = materializar_dwh()
        except Exception as e:
            dwh = {"ok": False, "error": str(e)}
        hospital = {}
        if opts.get("incluir_hospital", True):
            try:
                from paquetes.dataset.DatasetFlujoServicio import expandir_flujo_operativo
                import pyarrow as pa
                import pyarrow.parquet as pq
                sample_df = None
                if tmp_path and os.path.exists(tmp_path):
                    # Hasta 5K pacientes E2E; leer solo lo necesario (no el Parquet completo)
                    n_sample = int(min(max(30, cantidad), 5_000))
                    if opts.get("modo_rapido"):
                        n_sample = min(n_sample, 800)
                    pf = pq.ParquetFile(tmp_path)
                    batches = []
                    rows = 0
                    for batch in pf.iter_batches(batch_size=min(50_000, n_sample)):
                        batches.append(batch)
                        rows += batch.num_rows
                        if rows >= n_sample:
                            break
                    if batches:
                        sample_df = pa.Table.from_batches(batches).slice(0, n_sample).to_pandas()
                hospital = expandir_flujo_operativo(
                    cantidad,
                    year,
                    {**opts, "stage_path": archivo},
                    perfiles_df=sample_df,
                )
            except Exception as e:
                hospital = {"ok": False, "error": str(e)}
        # Alertas clínicas: costosas en lotes grandes; se omiten en modo rápido
        if not opts.get("modo_rapido") and cantidad <= 50_000:
            try:
                from paquetes.notificaciones.NotificacionesServicio import evaluar_alertas_clinicas
                evaluar_alertas_clinicas()
            except Exception:
                pass
        return {
            "mensaje": f"{cantidad:,} registros generados y subidos".replace(",", "."),
            "archivo": archivo,
            "total": cantidad,
            "perfil": perfil,
            "modo_rapido": bool(opts.get("modo_rapido")),
            "dwh": dwh,
            "hospital": hospital,
            "flujo": {
                "pacientes": (hospital or {}).get("pacientes"),
                "citas": (hospital or {}).get("citas"),
                "admisiones": (hospital or {}).get("admisiones"),
                "registros_clinicos": (hospital or {}).get("registros_clinicos"),
            } if isinstance(hospital, dict) and hospital.get("ok") else {},
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _listar_parquets_ordenados():
    c = get_cliente()
    objetos = list(c.list_objects(MINIO_BUCKET, prefix=MINIO_STAGE_PATH, recursive=True))
    return sorted(
        [o for o in objetos if o.object_name.endswith(".parquet")],
        key=lambda o: o.last_modified or datetime.min.replace(tzinfo=timezone.utc),
    )


def _filas_parquet(c, ruta: str) -> int:
    import pyarrow.parquet as pq
    obj = c.get_object(MINIO_BUCKET, ruta)
    return pq.ParquetFile(io.BytesIO(obj.read())).metadata.num_rows


def _leer_parquet(c, ruta: str) -> pd.DataFrame:
    obj = c.get_object(MINIO_BUCKET, ruta)
    return pd.read_parquet(io.BytesIO(obj.read()))


def _subir_parquet(c, ruta: str, df: pd.DataFrame) -> None:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    c.put_object(MINIO_BUCKET, ruta, buf, buf.getbuffer().nbytes)


def contar_registros() -> dict:
    try:
        c = get_cliente()
        parquets = _listar_parquets_ordenados()
        total = 0
        for o in parquets:
            total += _filas_parquet(c, o.object_name)
        return {"total_registros": total, "total_archivos": len(parquets)}
    except Exception as e:
        return {"total_registros": 0, "total_archivos": 0, "error": str(e)}


def listar_archivos() -> dict:
    try:
        c = get_cliente()
        parquets = _listar_parquets_ordenados()
        archivos = []
        total_registros = 0
        for o in parquets:
            filas = _filas_parquet(c, o.object_name)
            total_registros += filas
            archivos.append({
                "nombre": o.object_name,
                "tamano_mb": round((o.size or 0) / 1024 / 1024, 2),
                "fecha": o.last_modified.isoformat() if o.last_modified else "",
                "registros": filas,
            })
        archivos.sort(key=lambda x: x["fecha"], reverse=True)
        return {"archivos": archivos, "total": len(archivos), "total_registros": total_registros}
    except Exception as e:
        return {"archivos": [], "total": 0, "total_registros": 0, "error": str(e)}


def eliminar_archivo(ruta: str) -> dict:
    try:
        if not ruta.startswith(MINIO_STAGE_PATH) or not ruta.endswith(".parquet"):
            return {"error": "Ruta de archivo no válida"}
        c = get_cliente()
        c.remove_object(MINIO_BUCKET, ruta)
        _invalidar_cache_registros()
        return {"mensaje": "Archivo eliminado", "archivo": ruta}
    except Exception as e:
        return {"error": str(e)}


def eliminar_todos() -> dict:
    """Borra stage + DWH + hospital generado (recetas, facturas, pacientes E2E, etc.)."""
    try:
        c = get_cliente()
        parquets = _listar_parquets_ordenados()
        eliminados = 0
        for o in parquets:
            c.remove_object(MINIO_BUCKET, o.object_name)
            eliminados += 1
        # Snapshot de stats en stage
        try:
            c.remove_object(MINIO_BUCKET, f"{MINIO_STAGE_PATH}.diabcare_estadisticas_v2.json")
        except Exception:
            pass
        _invalidar_cache_registros()
        from paquetes.dataset.DatasetDwhServicio import vaciar_dwh
        dwh = vaciar_dwh()
        if not dwh.get("ok"):
            return {
                "error": dwh.get("error") or "No se pudo vaciar DWH/operativo",
                "eliminados_stage": eliminados,
                "dwh": dwh,
            }
        return {
            "ok": True,
            "mensaje": (
                f"Limpieza completa: {eliminados} archivo(s) de stage + "
                f"{dwh.get('eliminados', 0)} objeto(s) DWH/hospital"
            ),
            "eliminados": eliminados,
            "dwh": dwh,
        }
    except Exception as e:
        return {"error": str(e)}


def _recortar_parquet(c, path: str, quitar: int, desde: str) -> str:
    """Recorta filas sin cargar pandas. Devuelve 'delete', 'updated' o 'unchanged'."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    if quitar <= 0:
        return "unchanged"

    obj = c.get_object(MINIO_BUCKET, path)
    pf = pq.ParquetFile(io.BytesIO(obj.read()))
    total = pf.metadata.num_rows
    keep = total - quitar
    if keep <= 0:
        return "delete"

    parts = []
    if desde == "recientes":
        rows = 0
        for i in range(pf.num_row_groups):
            if rows >= keep:
                break
            chunk = pf.read_row_group(i)
            if rows + chunk.num_rows <= keep:
                parts.append(chunk)
                rows += chunk.num_rows
            else:
                parts.append(chunk.slice(0, keep - rows))
                rows = keep
    else:
        skip = quitar
        rows = 0
        for i in range(pf.num_row_groups):
            if rows >= keep:
                break
            chunk = pf.read_row_group(i)
            n = chunk.num_rows
            if skip >= n:
                skip -= n
                continue
            if skip > 0:
                chunk = chunk.slice(skip)
                skip = 0
            need = keep - rows
            if chunk.num_rows <= need:
                parts.append(chunk)
                rows += chunk.num_rows
            else:
                parts.append(chunk.slice(0, need))
                rows = keep

    out_table = pa.concat_tables(parts) if len(parts) > 1 else parts[0]
    out = io.BytesIO()
    pq.write_table(out_table, out, compression="snappy")
    out.seek(0)
    c.put_object(MINIO_BUCKET, path, out, out.getbuffer().nbytes)
    return "updated"


def eliminar_registros(cantidad: int, desde: str = "recientes") -> dict:
    """Elimina exactamente `cantidad` filas de los parquets en stage/."""
    if cantidad < 1:
        return {"error": "La cantidad debe ser al menos 1"}
    if desde not in ("recientes", "antiguos"):
        return {"error": "Parámetro 'desde' debe ser 'recientes' o 'antiguos'"}

    try:
        c = get_cliente()
        parquets = _listar_parquets_ordenados()
        if not parquets:
            return {"error": "No hay registros para eliminar"}

        meta = [{"path": o.object_name, "rows": _filas_parquet(c, o.object_name)} for o in parquets]
        total = sum(m["rows"] for m in meta)
        if cantidad > total:
            return {"error": f"Solo hay {total:,} registros disponibles".replace(",", ".")}

        if cantidad == total:
            res = eliminar_todos()
            if "error" in res:
                return res
            return {
                "mensaje": f"{cantidad:,} registro(s) eliminado(s)".replace(",", "."),
                "eliminados": cantidad,
                "restantes": 0,
                "desde": desde,
                "archivos_eliminados": res.get("eliminados", 0),
                "archivos_actualizados": 0,
            }

        indices = list(reversed(range(len(meta)))) if desde == "recientes" else list(range(len(meta)))
        restante = cantidad
        paths_to_delete: set[str] = set()
        archivos_actualizados = 0

        for idx in indices:
            if restante <= 0:
                break
            path = meta[idx]["path"]
            n = meta[idx]["rows"]
            if restante >= n:
                paths_to_delete.add(path)
                restante -= n
            else:
                accion = _recortar_parquet(c, path, restante, desde)
                if accion == "delete":
                    paths_to_delete.add(path)
                elif accion == "updated":
                    archivos_actualizados += 1
                restante = 0

        for path in paths_to_delete:
            c.remove_object(MINIO_BUCKET, path)

        _invalidar_cache_registros()
        restantes = total - cantidad
        dwh = {}
        if restantes <= 0:
            try:
                from paquetes.dataset.DatasetDwhServicio import vaciar_dwh
                dwh = vaciar_dwh()
            except Exception as e:
                dwh = {"ok": False, "error": str(e)}
        return {
            "mensaje": f"{cantidad:,} registro(s) eliminado(s)".replace(",", "."),
            "eliminados": cantidad,
            "restantes": restantes,
            "desde": desde,
            "archivos_eliminados": len(paths_to_delete),
            "archivos_actualizados": archivos_actualizados,
            "dwh": dwh,
        }
    except Exception as e:
        return {"error": str(e)}
