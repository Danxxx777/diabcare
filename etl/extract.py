"""Extracción desde PocketBase (paso E del ELT)."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

PB_PAGE_SIZE = 500


def _http_json(url: str, method: str = "GET", data: dict | None = None, token: str | None = None, timeout: float = 60):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = token
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detalle = ""
        try:
            detalle = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise RuntimeError(f"Error HTTP PocketBase ({e.code}): {e.reason}. {detalle[:200]}") from e


def parse_pb_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        s = str(val).replace("Z", "+00:00")
        if " " in s and "T" not in s:
            s = s.replace(" ", "T", 1)
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def fmt_pb_filter(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")


def autenticar_pocketbase(base_url: str, email: str, password: str) -> str | None:
    credenciales = {"identity": email, "password": password}
    for ruta in ("/api/collections/_superusers/auth-with-password", "/api/admins/auth-with-password"):
        try:
            res = _http_json(f"{base_url.rstrip('/')}{ruta}", "POST", credenciales, timeout=15)
            if res.get("token"):
                return res["token"]
        except Exception:
            continue
    return None


def _filtro_incremental(desde: datetime) -> str:
    # Sintaxis PocketBase: comillas dobles en literales de fecha (compatible PB 0.22+).
    return f'updated>"{fmt_pb_filter(desde)}"'


def _paginar(base_url: str, coleccion: str, token: str | None, filtro_pb: str | None) -> list[pd.DataFrame]:
    partes: list[pd.DataFrame] = []
    pagina = 1
    while True:
        url = (
            f"{base_url.rstrip('/')}/api/collections/{coleccion}/records"
            f"?page={pagina}&perPage={PB_PAGE_SIZE}"
        )
        if filtro_pb:
            url += f"&filter={urllib.parse.quote(filtro_pb, safe='')}"
        try:
            data = _http_json(url, token=token, timeout=120)
        except urllib.error.URLError as e:
            raise RuntimeError(f"PocketBase no disponible en {base_url}.") from e
        except RuntimeError as e:
            msg = str(e)
            if "401" in msg or "403" in msg:
                if token is None:
                    raise RuntimeError(
                        "PocketBase requiere autenticación. Revise POCKETBASE_EMAIL/PASSWORD."
                    ) from e
            if "404" in msg:
                raise RuntimeError(f"Colección '{coleccion}' no encontrada.") from e
            raise

        items = data.get("items") or []
        if not items:
            break
        partes.append(pd.DataFrame(items))
        if pagina >= int(data.get("totalPages") or 1):
            break
        pagina += 1
    return partes


def _filtrar_cliente(df: pd.DataFrame, desde: datetime) -> pd.DataFrame:
    if df.empty or "updated" not in df.columns:
        return df.iloc[0:0]
    upd = df["updated"].apply(parse_pb_dt)
    return df[upd > desde].copy()


def extraer_desde_pocketbase(
    *,
    base_url: str,
    coleccion: str,
    token: Optional[str],
    desde: Optional[datetime],
    historico: bool = False,
) -> tuple[pd.DataFrame, str]:
    """
    Extrae registros de PocketBase.
    Si el filtro server-side falla (400 / sintaxis), reintenta sin filtro y
    filtra en cliente (compatibilidad entre versiones de PocketBase).
    """
    filtro_pb = None if historico else (_filtro_incremental(desde) if desde else None)
    filtro_local = False

    try:
        partes = _paginar(base_url, coleccion, token, filtro_pb)
    except RuntimeError as e:
        if filtro_pb and "400" in str(e) and not historico:
            partes = _paginar(base_url, coleccion, token, None)
            filtro_local = True
        else:
            raise

    if not partes:
        if historico:
            return pd.DataFrame(), "0 registros en PocketBase (colección vacía)"
        return pd.DataFrame(), "0 registros nuevos en PocketBase desde la última sincronización"

    df = pd.concat(partes, ignore_index=True)
    if not historico and desde and filtro_local:
        df = _filtrar_cliente(df, desde)

    if df.empty:
        return pd.DataFrame(), "0 registros nuevos en PocketBase desde la última sincronización"

    if historico:
        det = f"{len(df):,} registros extraídos (importación histórica)".replace(",", ".")
    elif filtro_local:
        det = f"{len(df):,} registros nuevos/actualizados (filtro local)".replace(",", ".")
    else:
        det = f"{len(df):,} registros nuevos/actualizados en PocketBase".replace(",", ".")
    return df, det
