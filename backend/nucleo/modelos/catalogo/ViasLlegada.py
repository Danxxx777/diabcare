# -*- coding: utf-8 -*-
"""Vías de llegada del paciente, compartidas por Admisiones y Urgencias.

Estaban duplicadas y desalineadas: la pantalla de Admisiones ofrecía seis
opciones y su servicio solo aceptaba tres, así que "Rescate o bomberos" o
"Policía o autoridad" fallaban al guardar.
"""
from __future__ import annotations

VIAS_LLEGADA: dict[str, str] = {
    "propia": "Por sus medios",
    "ambulancia": "Ambulancia",
    "referido": "Referido de otro centro",
    "traslado_interno": "Traslado interno",
    "rescate": "Rescate o bomberos",
    "autoridad": "Policía o autoridad",
}

VIAS = set(VIAS_LLEGADA)


def etiqueta_via(valor) -> str:
    return VIAS_LLEGADA.get(str(valor or "").strip().lower(), "—")


def via_valida(valor) -> bool:
    return str(valor or "").strip().lower() in VIAS
