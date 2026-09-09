# -*- coding: utf-8 -*-
from datetime import date, timedelta

from paquetes.farmacia import FarmaciaRutas as rutas
from paquetes.farmacia import FarmaciaServicio as servicio


def test_clasificar_vencimiento_cubre_limites_y_fechas_invalidas():
    hoy = date(2026, 8, 29)

    assert servicio.clasificar_vencimiento(hoy - timedelta(days=1), hoy) == "Vencido"
    assert servicio.clasificar_vencimiento(hoy, hoy) == "Próximo a vencer"
    assert servicio.clasificar_vencimiento(hoy + timedelta(days=30), hoy) == "Próximo a vencer"
    assert servicio.clasificar_vencimiento(hoy + timedelta(days=31), hoy) == "Vigente"
    assert servicio.clasificar_vencimiento("", hoy) == "Sin fecha"
    assert servicio.clasificar_vencimiento("fecha-invalida", hoy) == "Sin fecha"


def test_listar_inventario_agrega_estado_sin_modificar_campos(monkeypatch):
    lote_original = {
        "id_inventario": "INV-001",
        "id_medicamento": "MED-001",
        "lote": "L-2026-01",
        "fecha_vencimiento": "2099-12-31",
        "cantidad": 25,
        "activo": True,
    }

    monkeypatch.setattr(
        servicio.inventario,
        "listar",
        lambda *args, **kwargs: {"lotes": [lote_original.copy()], "total": 1},
    )

    respuesta = rutas.list_inv(offset=0, limit=50, q="", payload={"sub": "prueba"})
    lote = respuesta["lotes"][0]

    assert respuesta["total"] == 1
    assert lote["estado_vencimiento"] == "Vigente"
    assert {clave: lote[clave] for clave in lote_original} == lote_original
    assert "estado_vencimiento" not in lote_original
