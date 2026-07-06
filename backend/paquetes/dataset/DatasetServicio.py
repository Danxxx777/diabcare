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


def _rng(opts: dict):
    semilla = opts.get("semilla")
    if semilla is not None:
        return np.random.default_rng(int(semilla))
    return np.random.default_rng()


def _generar_chunk_table(n: int, year: int, opts: dict, rng: np.random.Generator):
    """Generación vectorizada — órdenes de magnitud más rápida que fila a fila."""
    import pyarrow as pa

    edad_min = float(opts.get("edad_min") or 1)
    edad_max = float(opts.get("edad_max") or 80)
    genero = opts.get("genero")
    ubicacion = opts.get("ubicacion")
    prevalencia = opts.get("prevalencia_diabetes")
    perfil = opts.get("perfil") or "aleatorio"

    age = np.round(rng.uniform(edad_min, edad_max, n), 1)

    if perfil == "alto_riesgo":
        bmi = np.round(rng.uniform(28, 45, n), 2)
        hba1c = np.round(rng.uniform(6.8, 9.5, n), 1)
        glucosa = rng.integers(160, 301, n)
        hiper = (rng.random(n) < 0.55).astype(np.int8)
        cardio = (rng.random(n) < 0.35).astype(np.int8)
    elif perfil == "bajo_riesgo":
        bmi = np.round(rng.uniform(18, 26, n), 2)
        hba1c = np.round(rng.uniform(4.0, 5.8, n), 1)
        glucosa = rng.integers(80, 141, n)
        hiper = (rng.random(n) < 0.05).astype(np.int8)
        cardio = (rng.random(n) < 0.02).astype(np.int8)
    elif perfil == "balanceado":
        bmi = np.round(rng.uniform(20, 35, n), 2)
        hba1c = np.round(rng.uniform(4.5, 8.0, n), 1)
        glucosa = rng.integers(90, 221, n)
        hiper = (rng.random(n) < 0.2).astype(np.int8)
        cardio = (rng.random(n) < 0.1).astype(np.int8)
    else:
        bmi = np.round(rng.uniform(15, 45, n), 2)
        hba1c = np.round(rng.uniform(3.5, 9.0, n), 1)
        glucosa = rng.integers(80, 301, n)
        hiper = (rng.random(n) < np.where(bmi > 30, 0.4, 0.1)).astype(np.int8)
        cardio = (rng.random(n) < 0.08).astype(np.int8)

    if prevalencia is not None:
        p = max(0.0, min(1.0, float(prevalencia)))
        diabetes = (rng.random(n) < p).astype(np.int8)
    elif perfil == "alto_riesgo":
        diabetes = (rng.random(n) < 0.72).astype(np.int8)
    elif perfil == "bajo_riesgo":
        diabetes = (rng.random(n) < 0.08).astype(np.int8)
    else:
        clinico = (hba1c > 6.5) | (glucosa > 200)
        diabetes = np.where(clinico, 1, (rng.random(n) < 0.15).astype(np.int8))

    if genero in GENEROS:
        gender = np.full(n, genero, dtype=object)
    else:
        gender = rng.choice(GENEROS, n)

    if ubicacion:
        location = np.full(n, ubicacion, dtype=object)
    else:
        location = rng.choice(UBICACIONES, n)

    race_idx = rng.integers(0, len(RAZA_KEYS), n)
    smoking = rng.choice(HISTORIAL_TABAQUISMO, n)

    columns = {
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

        writer = None
        generados = 0
        while generados < cantidad:
            n = min(CHUNK_GENERACION, cantidad - generados)
            table = _generar_chunk_table(n, year, opts, rng)
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
            dwh = materializar_dwh()
        except Exception as e:
            dwh = {"ok": False, "error": str(e)}
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
            "dwh": dwh,
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
    try:
        c = get_cliente()
        parquets = _listar_parquets_ordenados()
        eliminados = 0
        for o in parquets:
            c.remove_object(MINIO_BUCKET, o.object_name)
            eliminados += 1
        _invalidar_cache_registros()
        return {"mensaje": f"{eliminados} archivo(s) eliminado(s)", "eliminados": eliminados}
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
        return {
            "mensaje": f"{cantidad:,} registro(s) eliminado(s)".replace(",", "."),
            "eliminados": cantidad,
            "restantes": total - cantidad,
            "desde": desde,
            "archivos_eliminados": len(paths_to_delete),
            "archivos_actualizados": archivos_actualizados,
        }
    except Exception as e:
        return {"error": str(e)}
