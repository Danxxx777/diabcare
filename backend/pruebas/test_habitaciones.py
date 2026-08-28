# -*- coding: utf-8 -*-
"""Modulo de habitaciones: ocupacion derivada y reglas de las acciones.

El catalogo y las admisiones se sustituyen por DataFrames en memoria, asi que
estas pruebas no tocan MinIO.
"""
import pandas as pd
import pytest

from paquetes.clinico.admisiones import AdmisionesServicio as admisiones
from paquetes.clinico.habitaciones import HabitacionesServicio as habitaciones


def _catalogo(estados=None):
    estados = estados or {}
    return pd.DataFrame([
        {
            "codigo": codigo, "piso": codigo[2],
            "estado_operativo": estados.get(codigo, "disponible"),
            "nota": "", "actualizado_en": "", "actualizado_por": "sistema",
        }
        for codigo in ("H-101", "H-102", "H-201")
    ], columns=habitaciones.COLUMNAS)


def _admision(**campos):
    fila = {col: "" for col in admisiones.COLUMNAS}
    fila.update({"tipo": "hospitalizacion", "estado": "activa", "fecha_ingreso": "2026-08-20"})
    fila.update(campos)
    return fila


@pytest.fixture
def entorno(monkeypatch):
    """Catalogo y admisiones en memoria; devuelve lo que se intento guardar."""
    guardado = {}

    def preparar(catalogo, filas_admisiones):
        monkeypatch.setattr(habitaciones, "_catalogo", lambda copiar=True: catalogo.copy())
        monkeypatch.setattr(habitaciones, "_guardar", lambda df: guardado.update({"catalogo": df.copy()}))
        monkeypatch.setattr(habitaciones, "_equipos_por_admision", dict)
        monkeypatch.setattr(
            admisiones, "_extraer",
            lambda copiar=True: pd.DataFrame(filas_admisiones, columns=admisiones.COLUMNAS),
        )
        return guardado

    return preparar


def test_mapa_separa_ocupadas_libres_y_lista_de_espera(entorno):
    entorno(
        _catalogo({"H-201": "mantenimiento"}),
        [
            _admision(id_admision="a1", paciente_nombre="Elena", habitacion="H-101", servicio="Endocrinología"),
            _admision(id_admision="a2", paciente_nombre="Jose", habitacion=""),
        ],
    )
    m = habitaciones.mapa()
    assert (m["total"], m["ocupadas"], m["libres"], m["mantenimiento"]) == (3, 1, 1, 1)
    assert m["porcentaje"] == 33
    ocupada = next(c for c in m["camas"] if c["codigo"] == "H-101")
    assert ocupada["estado"] == "ocupada" and ocupada["paciente"] == "Elena"
    assert [p["paciente"] for p in m["esperando"]] == ["Jose"]


def test_cama_fuera_del_catalogo_no_descuadra_el_conteo(entorno):
    entorno(
        _catalogo(),
        [_admision(id_admision="a1", paciente_nombre="Historico", habitacion="A-178")],
    )
    m = habitaciones.mapa()
    assert m["ocupadas"] == 0
    assert m["libres"] == 3
    assert m["fuera_catalogo"] == 1


def test_traslado_mueve_al_paciente_y_deja_el_origen_en_limpieza(entorno, monkeypatch):
    guardado = entorno(
        _catalogo(),
        [_admision(id_admision="a1", paciente_nombre="Elena", habitacion="H-101")],
    )
    cambios = {}
    monkeypatch.setattr(
        admisiones, "actualizar",
        lambda _id, datos: cambios.update(datos) or {"mensaje": "ok"},
    )
    res = habitaciones.trasladar("H-101", "H-102")
    assert "error" not in res
    assert cambios == {"habitacion": "H-102"}
    origen = guardado["catalogo"].set_index("codigo").loc["H-101"]
    assert origen["estado_operativo"] == "limpieza"


def test_no_se_asigna_una_cama_en_mantenimiento(entorno):
    entorno(_catalogo({"H-102": "mantenimiento"}), [])
    res = habitaciones.asignar("H-102", "a1")
    assert "mantenimiento" in res["error"]


def test_no_se_cambia_el_estado_de_una_cama_ocupada(entorno):
    entorno(
        _catalogo(),
        [_admision(id_admision="a1", paciente_nombre="Elena", habitacion="H-101")],
    )
    res = habitaciones.cambiar_estado("H-101", "mantenimiento")
    assert "ocupada" in res["error"]


def test_liberar_con_alta_cierra_la_admision(entorno, monkeypatch):
    guardado = entorno(
        _catalogo(),
        [_admision(id_admision="a1", paciente_nombre="Elena", habitacion="H-101")],
    )
    cambios = {}
    monkeypatch.setattr(
        admisiones, "actualizar",
        lambda _id, datos: cambios.update(datos) or {"mensaje": "ok"},
    )
    res = habitaciones.liberar("H-101", dar_alta=True)
    assert res["alta"] is True
    assert cambios == {"estado": "alta"}
    assert guardado["catalogo"].set_index("codigo").loc["H-101"]["estado_operativo"] == "limpieza"


def test_liberar_sin_alta_manda_al_paciente_a_la_lista_de_espera(entorno, monkeypatch):
    """Antes esto era imposible: la admision exigia cama, asi que 'liberar sin
    alta' fallaba. La espera de cama ahora es un estado legitimo."""
    filas = [_admision(id_admision="a1", paciente_nombre="Elena", habitacion="H-101")]
    entorno(_catalogo(), filas)
    escrito = {}
    monkeypatch.setattr(admisiones, "_cargar", lambda df: escrito.update({"df": df.copy()}))

    res = habitaciones.liberar("H-101", dar_alta=False)

    assert "error" not in res
    assert escrito["df"].iloc[0]["habitacion"] == ""
    assert escrito["df"].iloc[0]["estado"] == "activa"


def test_una_hospitalizacion_sin_cama_aparece_esperando(entorno):
    entorno(_catalogo(), [_admision(id_admision="a1", paciente_nombre="Elena", habitacion="")])
    assert [p["paciente"] for p in habitaciones.esperando_cama()] == ["Elena"]
