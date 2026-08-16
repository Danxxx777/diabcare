"""Cookie httpOnly para la sesión JWT (el navegador no puede leerla con JS)."""
from __future__ import annotations

import os

from fastapi import Response

COOKIE_SESION = "diabcare_session"
# En localhost HTTP Secure=False; en producción con HTTPS poner DIABCARE_COOKIE_SECURE=1
COOKIE_SECURE = os.environ.get("DIABCARE_COOKIE_SECURE", "").strip().lower() in ("1", "true", "yes")
COOKIE_SAMESITE = os.environ.get("DIABCARE_COOKIE_SAMESITE", "lax")


def aplicar_cookie_sesion(response: Response, token: str, max_age_segundos: int) -> None:
    response.set_cookie(
        key=COOKIE_SESION,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=int(max_age_segundos),
        path="/",
    )


def borrar_cookie_sesion(response: Response) -> None:
    response.delete_cookie(
        key=COOKIE_SESION,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )
