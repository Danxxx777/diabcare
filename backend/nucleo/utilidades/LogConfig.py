"""
Configuración de logs: solo advertencias y errores en consola.
"""

import logging
import sys

_LOGGERS_SILENCIAR = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "fastapi",
    "watchfiles",
    "watchfiles.main",
)


def silenciar_logs() -> None:
    """Oculta INFO/DEBUG de uvicorn, peticiones HTTP y recarga automática."""
    if not logging.root.handlers:
        logging.basicConfig(
            level=logging.WARNING,
            format="%(levelname)s [DiabCare] %(message)s",
            stream=sys.stderr,
        )
    logging.root.setLevel(logging.WARNING)
    for nombre in _LOGGERS_SILENCIAR:
        log = logging.getLogger(nombre)
        log.setLevel(logging.WARNING)
        log.handlers.clear()
        log.propagate = False
    logging.getLogger("uvicorn.access").disabled = True


def log_advertencia(mensaje: str) -> None:
    logging.getLogger("diabcare").warning(mensaje)
