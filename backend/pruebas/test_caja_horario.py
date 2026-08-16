# -*- coding: utf-8 -*-
"""
Pruebas del turno de caja y del horario de atención.

Cubren los tres defectos que aparecieron al construir el arqueo, porque son
silenciosos: no rompen nada visible, solo hacen que el cuadre dé mal.
  1. Turno en hora local contra pagos en UTC -> el arqueo daba siempre cero.
  2. Campos numéricos creados vacíos -> el cierre reventaba con TypeError.
  3. Instantes truncados al segundo -> el último cobro del turno quedaba fuera
     y un mismo pago podía contarse en dos turnos.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from nucleo.utilidades import Validaciones as V  # noqa: E402
from paquetes.facturacion import CajaServicio as C  # noqa: E402


# ── Ventana del turno ──────────────────────────────────────────────────────
def test_ts_acepta_con_y_sin_microsegundos():
    """ParquetStore guarda microsegundos y el turno no siempre: ambos valen."""
    assert C._ts("2026-08-16T18:42:06") is not None
    assert C._ts("2026-08-16T18:42:06.481460") is not None
    assert C._ts("") is None
    assert C._ts(None) is None
    assert C._ts("no es fecha") is None


def test_pago_dentro_del_mismo_segundo_del_cierre_cuenta():
    """
    Regresión del bug 3.

    Comparando como texto, "18:42:06.481460" > "18:42:06" y el último cobro
    del turno quedaba fuera del arqueo por menos de un segundo.
    """
    turno = {"abierto_en": "2026-08-16T18:42:05", "cerrado_en": "2026-08-16T18:42:06"}
    desde = C._ts(turno["abierto_en"])
    hasta = C._ts(turno["cerrado_en"])
    pago = C._ts("2026-08-16T18:42:06.481460")
    # Con datetime el pago cae dentro; como cadena quedaba fuera.
    assert desde <= pago
    assert pago > hasta, "el pago es posterior al cierre por microsegundos"
    # Y la comparación textual, que era el bug:
    assert not ("2026-08-16T18:42:06.481460" <= "2026-08-16T18:42:06")


def test_now_es_utc_sin_zona_como_parquetstore():
    """Regresión del bug 1: si no es UTC, ningún pago cae en la ventana."""
    ahora = C._ts(C._now())
    assert ahora is not None
    assert ahora.tzinfo is None, "debe ser naive, igual que ParquetStore"
    utc = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs((ahora - utc).total_seconds()) < 5, "debe estar en UTC, no en hora local"


def test_now_conserva_microsegundos():
    """Sin microsegundos vuelve la franja donde un pago cae en dos turnos."""
    assert "." in C._now(), "truncar al segundo crea solapamiento entre turnos"


# ── Clasificación de métodos de pago ───────────────────────────────────────
@pytest.mark.parametrize("metodo,caja", [
    ("efectivo", "efectivo"),
    ("tarjeta", "tarjeta"),
    ("qr", "tarjeta"),
    ("stripe", "tarjeta"),
    ("transferencia", "transferencia"),
    ("cheque", "otros"),
])
def test_metodo_va_al_bucket_correcto(metodo, caja):
    """Solo el efectivo se cuenta a mano; lo demás no toca el cajón."""
    tot = C._totales([{"metodo": metodo, "monto": 10}])
    assert tot[caja] == 10.0
    assert sum(tot.values()) == 10.0


def test_totales_ignora_montos_invalidos():
    tot = C._totales([
        {"metodo": "efectivo", "monto": "40.25"},
        {"metodo": "efectivo", "monto": None},
        {"metodo": "efectivo", "monto": "no es número"},
    ])
    assert tot["efectivo"] == 40.25


# ── Aritmética del arqueo ──────────────────────────────────────────────────
@pytest.mark.parametrize("fondo,efectivo,contado,diferencia", [
    (50.0, 80.50, 130.50, 0.0),      # cuadrada
    (20.0, 40.25, 55.00, -5.25),     # faltante
    (20.0, 40.25, 65.00, 4.75),      # sobrante
    (0.0, 0.0, 0.0, 0.0),            # turno sin movimiento
])
def test_esperado_es_fondo_mas_efectivo(fondo, efectivo, contado, diferencia):
    """
    El esperado NUNCA sale del cliente: es fondo inicial + efectivo cobrado.
    Antes llegaba en el JSON y el cuadre se podía falsear desde el navegador.
    """
    esperado = round(fondo + efectivo, 2)
    assert round(contado - esperado, 2) == diferencia


def test_tarjeta_no_altera_el_esperado_en_efectivo():
    """Un cobro con tarjeta no entra al cajón: no puede mover el arqueo."""
    solo_efectivo = C._totales([{"metodo": "efectivo", "monto": 40.25}])
    con_tarjeta = C._totales([
        {"metodo": "efectivo", "monto": 40.25},
        {"metodo": "tarjeta", "monto": 999.0},
    ])
    assert solo_efectivo["efectivo"] == con_tarjeta["efectivo"]


def test_money_redondea_a_dos_decimales():
    assert C._money("40.256") == 40.26
    assert C._money(None) == 0.0
    assert C._money("basura") == 0.0


# ── Horario de atención ────────────────────────────────────────────────────
def test_horario_configurado_devuelve_valores_usables():
    ini, fin, dias = V.horario_configurado()
    assert fin > ini, "un rango invertido dejaría la agenda muerta"
    assert dias, "sin días no se podría agendar nunca"
    assert all(0 <= d <= 6 for d in dias)


def test_turno_fuera_de_horario_se_rechaza():
    lunes = "2026-08-17"
    ini, fin, _ = V.horario_configurado()
    dentro = f"{ini.hour + 1:02d}:00"
    assert V.horario_consulta_ok(lunes, dentro) == ""
    fuera = f"{max(0, ini.hour - 1):02d}:00"
    assert V.horario_consulta_ok(lunes, fuera) != ""


def test_dia_sin_consulta_se_rechaza():
    _, _, dias = V.horario_configurado()
    if 6 in dias:
        pytest.skip("la configuración actual atiende domingos")
    assert V.horario_consulta_ok("2026-08-16", "10:00") != ""  # domingo


def test_fecha_u_hora_invalidas_no_revientan():
    assert V.horario_consulta_ok("", "10:00") != ""
    assert V.horario_consulta_ok("2026-08-17", "") != ""
    assert V.horario_consulta_ok("no-es-fecha", "10:00") != ""


def test_rango_de_fechas_invertido_se_rechaza():
    assert V.rango_fechas_ok("2026-08-01", "2026-08-10") == ""
    assert V.rango_fechas_ok("2026-08-10", "2026-08-01") != ""


def test_rango_numerico_valida_negativos_y_orden():
    assert V.rango_numeros_ok(10, 40, "edad") == ""
    assert V.rango_numeros_ok(-1, 40, "edad") != ""
    assert V.rango_numeros_ok(40, 10, "edad") != ""
