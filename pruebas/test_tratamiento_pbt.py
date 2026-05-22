"""
test_tratamiento_pbt.py — Pruebas basadas en propiedades para asignar_tratamiento.

Requiere que load_data.py sea importable como módulo (Tarea 1).
Para que trat_map esté poblado, se inicializa con valores de prueba antes de los tests.

Feature: diabcare-analytics
"""

import pytest
from hypothesis import given, settings, strategies as st

# Poblar trat_map con IDs de prueba antes de importar asignar_tratamiento
import load_data

# Inicializar trat_map con IDs ficticios para los tests (sin BD real)
load_data.trat_map.update({
    "Normal": 1,
    "Prediabetes": 2,
    "Diabetes leve": 3,
    "Diabetes moderada": 4,
    "Diabetes severa": 5,
})

from load_data import asignar_tratamiento, trat_map

VALID_IDS = set(trat_map.values())


# ── Property 4: asignar_tratamiento cubre todos los rangos clínicos ───────────
# Feature: diabcare-analytics, Property 4: asignación de tratamiento cubre todos los rangos clínicos

@given(
    st.floats(allow_nan=False, allow_infinity=False),
    st.floats(allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_asignar_tratamiento_siempre_retorna_id_valido(hba1c, glucosa):
    """
    Para cualquier par (hba1c, glucosa) de floats finitos,
    asignar_tratamiento debe retornar un id_tratamiento presente en trat_map.values().
    Nunca debe retornar None ni un valor fuera del mapa.
    """
    resultado = asignar_tratamiento(hba1c, glucosa)
    assert resultado in VALID_IDS, (
        f"asignar_tratamiento({hba1c}, {glucosa}) = {resultado!r} "
        f"no está en los IDs válidos {VALID_IDS}"
    )


# ── Property 5: asignar_tratamiento es determinista ───────────────────────────
# Feature: diabcare-analytics, Property 5: asignación de tratamiento es determinista

@given(
    st.floats(allow_nan=False, allow_infinity=False),
    st.floats(allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_asignar_tratamiento_es_determinista(hba1c, glucosa):
    """
    Para cualquier par (hba1c, glucosa), invocar asignar_tratamiento dos veces
    con los mismos argumentos debe producir el mismo resultado.
    """
    resultado1 = asignar_tratamiento(hba1c, glucosa)
    resultado2 = asignar_tratamiento(hba1c, glucosa)
    assert resultado1 == resultado2, (
        f"asignar_tratamiento({hba1c}, {glucosa}) no es determinista: "
        f"{resultado1!r} != {resultado2!r}"
    )


# ── Tests unitarios de umbrales exactos ───────────────────────────────────────

@pytest.mark.parametrize("hba1c,glucosa,nivel_esperado", [
    # Umbrales exactos de hba1c
    (5.6, 100, "Normal"),
    (5.7, 100, "Prediabetes"),
    (6.4, 100, "Prediabetes"),
    (6.5, 100, "Diabetes leve"),
    (8.0, 100, "Diabetes leve"),   # 8.0 no supera > 8.0
    (8.01, 100, "Diabetes moderada"),
    (10.0, 100, "Diabetes moderada"),  # 10.0 no supera > 10.0
    (10.01, 100, "Diabetes severa"),
    # Umbrales exactos de glucosa
    (4.0, 139, "Normal"),
    (4.0, 140, "Prediabetes"),
    (4.0, 199, "Prediabetes"),
    (4.0, 200, "Diabetes leve"),
    (4.0, 300, "Diabetes leve"),   # 300 no supera > 300
    (4.0, 301, "Diabetes moderada"),
    (4.0, 400, "Diabetes moderada"),  # 400 no supera > 400
    (4.0, 401, "Diabetes severa"),
    # Valores no convertibles → Normal
    (None, None, "Normal"),
    ("abc", "xyz", "Normal"),
])
def test_asignar_tratamiento_umbrales(hba1c, glucosa, nivel_esperado):
    """Verifica el nivel correcto para valores en los umbrales exactos."""
    id_esperado = trat_map[nivel_esperado]
    assert asignar_tratamiento(hba1c, glucosa) == id_esperado, (
        f"hba1c={hba1c}, glucosa={glucosa}: "
        f"esperado '{nivel_esperado}' (id={id_esperado}), "
        f"obtenido id={asignar_tratamiento(hba1c, glucosa)}"
    )
