import pandas as pd

from paquetes.clinico.admisiones import AdmisionesServicio as admisiones
from paquetes.instrumental import InstrumentalServicio as instrumental


def test_asignacion_vincula_paciente_y_habitacion(monkeypatch):
    item = {"id_instrumental": "eq-1", "codigo": "EQ-1", "nombre": "Monitor", "estado": "disponible", "ubicacion": "Almacén clínico"}
    cambios = {}
    monkeypatch.setattr(instrumental.instrumentos, "obtener", lambda _id: item)
    monkeypatch.setattr(instrumental.instrumentos, "actualizar", lambda _id, data: cambios.update(data) or {"mensaje": "actualizado"})
    monkeypatch.setattr(instrumental.movimientos, "crear", lambda _data: {"mensaje": "creado"})
    monkeypatch.setattr(admisiones, "obtener", lambda _id: {"id_admision": "adm-1", "id_paciente": "pac-1", "paciente_nombre": "Paciente", "tipo": "hospitalizacion", "estado": "activa", "habitacion": "H-101"})
    resultado = instrumental.transicionar("eq-1", "asignar", {"responsable": "Enfermería", "id_admision": "adm-1"})
    assert "error" not in resultado
    assert cambios["id_paciente"] == "pac-1"
    assert cambios["habitacion"] == "H-101"


def test_alta_bloqueada_con_equipo_pendiente(monkeypatch):
    fila = {col: "" for col in admisiones.COLUMNAS}
    fila.update({"id_admision": "adm-1", "id_paciente": "pac-1", "tipo": "hospitalizacion", "estado": "activa", "habitacion": "H-101", "fecha_ingreso": "2026-08-24"})
    monkeypatch.setattr(admisiones, "_extraer", lambda copiar=True: pd.DataFrame([fila]))
    monkeypatch.setattr(instrumental, "asignados_admision", lambda _id: {"instrumentos": [{"id_instrumental": "eq-1"}]})
    resultado = admisiones.actualizar("adm-1", {"estado": "alta"})
    assert "Devuelva el instrumental" in resultado["error"]
