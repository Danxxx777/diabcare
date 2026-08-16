"""URL que un celular puede abrir (QR de informes y de cobro)."""
from __future__ import annotations

import os
from urllib.parse import urlparse


def _ip_lan() -> str | None:
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    try:
        import socket
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass
    return None


def _es_loopback(url: str) -> bool:
    low = (url or "").lower()
    return "localhost" in low or "127.0.0.1" in low


def _es_privada(host: str) -> bool:
    h = (host or "").strip().lower()
    if not h:
        return True
    if h in ("localhost", "127.0.0.1"):
        return True
    if h.startswith("10.") or h.startswith("192.168.") or h.startswith("169.254."):
        return True
    if h.startswith("172."):
        try:
            seg = int(h.split(".")[1])
            return 16 <= seg <= 31
        except (IndexError, ValueError):
            return False
    return False


def _desde_config() -> str:
    try:
        from paquetes.configuracion.ConfiguracionServicio import obtener_configuracion
        cfg = obtener_configuracion(enmascarar_secretos=False)
        return str(cfg.get("url_publica") or "").strip().rstrip("/")
    except Exception:
        return ""


def base_publica(base_url: str | None = None) -> str:
    """Preferir túnel/HTTPS (DIABCARE_PUBLIC_URL o Configuración). Si no, IP LAN."""
    env = (os.getenv("DIABCARE_PUBLIC_URL") or "").strip().rstrip("/")
    if env:
        return env
    cfg = _desde_config()
    if cfg:
        return cfg
    base = (base_url or "http://localhost:8000").strip().rstrip("/")
    if _es_loopback(base):
        ip = _ip_lan()
        if ip:
            p = urlparse(base if "://" in base else f"http://{base}")
            port = p.port or 8000
            scheme = p.scheme or "http"
            return f"{scheme}://{ip}:{port}"
    return base


def alcance_url(url: str | None = None) -> dict:
    """local = misma Wi‑Fi; internet = cualquiera con datos/4G."""
    u = (url or base_publica()).strip().rstrip("/")
    host = urlparse(u if "://" in u else f"http://{u}").hostname or ""
    internet = bool(u) and not _es_loopback(u) and not _es_privada(host)
    return {
        "url": u,
        "alcance": "internet" if internet else "local",
        "internet": internet,
    }
