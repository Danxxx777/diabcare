"""
Metadatos en Parquet (oper_fotos_entidad) + binarios en MinIO (diabcare-app).
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime

import pandas as pd

from paquetes.configuracion.ConfiguracionClienteMinio import get_cliente
from nucleo.utilidades.ParquetCache import leer, escribir

BUCKET_APP = "diabcare-app"
ARCHIVO_META = "operativo/fotos_entidad.parquet"
PREFIX_BIN = "operativo/fotos/binario/"
COLUMNAS = [
    "id_foto", "tipo_entidad", "id_entidad", "nombre_archivo", "mime_type",
    "ruta_minio", "es_principal", "subido_en", "subido_por",
]
MAX_BYTES = 5 * 1024 * 1024
MIME_OK = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}


def _es_true(val) -> bool:
    if val is True:
        return True
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "si", "sí")
    try:
        return bool(val) and str(val).lower() not in ("false", "0", "no", "none", "nan")
    except Exception:
        return False


def _extraer() -> pd.DataFrame:
    return leer(BUCKET_APP, ARCHIVO_META, COLUMNAS)


def _cargar(df: pd.DataFrame) -> None:
    escribir(BUCKET_APP, ARCHIVO_META, df)


def _ext(mime: str) -> str:
    m = (mime or "").lower()
    if "png" in m:
        return ".png"
    if "webp" in m:
        return ".webp"
    if "gif" in m:
        return ".gif"
    return ".jpg"


def guardar_foto(
    tipo_entidad: str,
    id_entidad: str,
    contenido: bytes,
    mime_type: str,
    usuario: str = "sistema",
    es_principal: bool = True,
) -> dict:
    if not contenido:
        return {"error": "Archivo vacío"}
    if len(contenido) > MAX_BYTES:
        return {"error": "La imagen no puede superar 5 MB"}
    mime = (mime_type or "image/jpeg").split(";")[0].strip().lower()
    if mime not in MIME_OK:
        return {"error": "Formato no permitido (use JPEG, PNG o WebP)"}

    id_foto = str(uuid.uuid4())
    ext = _ext(mime)
    nombre = f"foto{ext}"
    ruta = f"{PREFIX_BIN}{tipo_entidad}/{id_entidad}/{id_foto}{ext}"

    c = get_cliente()
    if not c.bucket_exists(BUCKET_APP):
        c.make_bucket(BUCKET_APP)
    c.put_object(
        BUCKET_APP, ruta, io.BytesIO(contenido), len(contenido), content_type=mime,
    )

    df = _extraer()
    if es_principal and not df.empty:
        mask = (
            (df["tipo_entidad"] == tipo_entidad)
            & (df["id_entidad"].astype(str) == str(id_entidad))
            & (df["es_principal"].map(_es_true))
        )
        df.loc[mask, "es_principal"] = False

    fila = {
        "id_foto": id_foto,
        "tipo_entidad": tipo_entidad,
        "id_entidad": str(id_entidad),
        "nombre_archivo": nombre,
        "mime_type": mime,
        "ruta_minio": ruta,
        "es_principal": es_principal,
        "subido_en": datetime.utcnow().isoformat(),
        "subido_por": str(usuario or "sistema"),
    }
    _cargar(pd.concat([df, pd.DataFrame([fila])], ignore_index=True))
    return {"mensaje": "Foto guardada", "id_foto": id_foto, "ruta_minio": ruta}


def obtener_principal(tipo_entidad: str, id_entidad: str) -> dict | None:
    df = _extraer()
    if df.empty:
        return None
    sub = df[
        (df["tipo_entidad"] == tipo_entidad)
        & (df["id_entidad"].astype(str) == str(id_entidad))
    ]
    if sub.empty:
        return None
    prin = sub[sub["es_principal"].map(_es_true)]
    row = prin.iloc[0] if not prin.empty else sub.sort_values("subido_en", ascending=False).iloc[0]
    return row.fillna("").to_dict()


def leer_bytes_foto(tipo_entidad: str, id_entidad: str) -> dict:
    meta = obtener_principal(tipo_entidad, id_entidad)
    if not meta:
        return {"error": "Sin foto"}
    try:
        c = get_cliente()
        obj = c.get_object(BUCKET_APP, meta["ruta_minio"])
        data = obj.read()
        return {
            "contenido": data,
            "mime_type": meta.get("mime_type") or "image/jpeg",
            "id_foto": meta.get("id_foto"),
        }
    except Exception as e:
        return {"error": f"No se pudo leer la foto: {e}"}


def _seed_int(valor: str) -> int:
    h = 0
    for ch in str(valor):
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return int(h)


_NOMBRES_F = {
    "ana", "maría", "maria", "elena", "sofía", "sofia", "paula", "lucía", "lucia",
    "valeria", "camila", "diana", "rosa", "carmen", "laura", "andrea", "isabel",
    "patricia", "gabriela", "alejandra", "daniela", "fernanda", "carolina", "mónica",
    "monica", "adriana", "claudia", "verónica", "veronica", "julia", "natalia",
}
_NOMBRES_M = {
    "luis", "carlos", "josé", "jose", "diego", "andrés", "andres", "miguel", "pedro",
    "jorge", "mateo", "daniel", "juan", "antonio", "francisco", "manuel", "álex",
    "alex", "david", "pablo", "rafael", "sergio", "javier", "ricardo", "eduardo",
}


def _inferir_carpeta_genero(genero: str, nombre: str = "", apellido: str = "") -> str:
    """women | men según género del expediente (y nombre si es Otro/desconocido)."""
    try:
        from paquetes.dataset.DatasetTraducciones import normalizar_genero
        canon = normalizar_genero(genero)
    except Exception:
        canon = str(genero or "").strip()

    c = (canon or "").strip().lower()
    if c in ("femenino", "female", "f", "mujer", "woman"):
        return "women"
    if c in ("masculino", "male", "m", "hombre", "man"):
        return "men"

    # Fallback: primer nombre del paciente
    prim = str(nombre or "").strip().split(" ")[0].lower()
    if prim in _NOMBRES_F:
        return "women"
    if prim in _NOMBRES_M:
        return "men"
    # sin señal clara: no mezclar al azar por id (evita “hombre con cara de mujer”)
    # usar lego solo si no hay género; preferimos men/women por apellido seed estable
    return "women" if (_seed_int(f"{nombre}|{apellido}|{genero}") % 2 == 0) else "men"


def _url_retrato_demo(genero: str, id_entidad: str, nombre: str = "", apellido: str = "") -> str:
    """Retratos demo de randomuser.me acorde al género del paciente."""
    carpeta = _inferir_carpeta_genero(genero, nombre, apellido)
    idx = _seed_int(f"{id_entidad}|{carpeta}") % 100
    return f"https://randomuser.me/api/portraits/{carpeta}/{idx}.jpg"


def _descargar_imagen(url: str) -> tuple[bytes, str]:
    import urllib.request

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DiabCare/1.0 (demo patient portraits)"},
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = resp.read()
        mime = (resp.headers.get_content_type() or "image/jpeg").split(";")[0].strip().lower()
    if not data:
        raise RuntimeError("Respuesta vacía")
    if len(data) > MAX_BYTES:
        raise RuntimeError("Imagen demasiado grande")
    if mime not in MIME_OK:
        mime = "image/jpeg"
    return data, mime


def asignar_fotos_automaticas(
    limite: int = 200,
    solo_sin_foto: bool = True,
    usuario: str = "sistema",
) -> dict:
    """Asigna fotos demo a pacientes (randomuser.me). Limite 1–2000 por llamada."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from paquetes.clinico.pacientes.PacientesServicio import _extraer as pacientes_df

    limite = max(1, min(int(limite or 200), 2000))
    pdf = pacientes_df()
    if pdf.empty:
        return {"mensaje": "No hay pacientes", "asignadas": 0, "omitidas": 0, "errores": 0}

    con_foto = set()
    try:
        fdf = _extraer()
        if not fdf.empty:
            con_foto = set(
                fdf[
                    (fdf["tipo_entidad"].astype(str) == "paciente")
                    & fdf["es_principal"].map(_es_true)
                ]["id_entidad"].astype(str).tolist()
            )
    except Exception:
        pass

    candidatos = []
    por_genero = {"women": 0, "men": 0}
    for _, row in pdf.iterrows():
        pid = str(row.get("id_paciente") or "")
        if not pid:
            continue
        if solo_sin_foto and pid in con_foto:
            continue
        genero = str(row.get("genero") or "")
        nombre = str(row.get("nombre") or "")
        apellido = str(row.get("apellido") or "")
        carpeta = _inferir_carpeta_genero(genero, nombre, apellido)
        por_genero[carpeta] = por_genero.get(carpeta, 0) + 1
        candidatos.append({
            "id_paciente": pid,
            "genero": genero,
            "nombre": nombre,
            "apellido": apellido,
            "carpeta": carpeta,
        })
        if len(candidatos) >= limite:
            break

    if not candidatos:
        return {
            "mensaje": "Todos los pacientes del lote ya tienen foto" if solo_sin_foto else "Sin candidatos",
            "asignadas": 0,
            "omitidas": 0,
            "errores": 0,
            "candidatos": 0,
            "por_genero": por_genero,
            "fuente": "randomuser.me",
        }

    asignadas = 0
    errores = 0
    detalle_err: list[str] = []

    def _uno(item: dict) -> tuple[bool, str]:
        try:
            url = _url_retrato_demo(
                item["genero"],
                item["id_paciente"],
                item.get("nombre") or "",
                item.get("apellido") or "",
            )
            data, mime = _descargar_imagen(url)
            res = guardar_foto(
                "paciente",
                item["id_paciente"],
                data,
                mime,
                usuario=usuario or "sistema",
                es_principal=True,
            )
            if res.get("error"):
                return False, str(res["error"])
            return True, ""
        except Exception as e:
            return False, str(e)

    workers = min(12, max(2, len(candidatos) // 5 or 2))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_uno, c): c for c in candidatos}
        for fut in as_completed(futures):
            ok, err = fut.result()
            if ok:
                asignadas += 1
            else:
                errores += 1
                if len(detalle_err) < 8 and err:
                    detalle_err.append(err)

    return {
        "mensaje": f"{asignadas} foto(s) asignada(s) automáticamente",
        "asignadas": asignadas,
        "omitidas": 0,
        "errores": errores,
        "candidatos": len(candidatos),
        "por_genero": por_genero,
        "fuente": "randomuser.me (retratos según género del expediente)",
        "errores_detalle": detalle_err,
    }
