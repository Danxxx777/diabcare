# -*- coding: utf-8 -*-
"""Comprueba que la base OpenSpec siga conectada con la estructura real."""
from pathlib import Path
import runpy

import pytest


ROOT = Path(__file__).resolve().parents[2]
MIGRATOR = runpy.run_path(str(ROOT / "scripts" / "migrar_specs_openspec.py"))
CAPABILITIES = MIGRATOR["CAPABILITIES"]


@pytest.mark.parametrize("capability,source_rel,backend,frontend", CAPABILITIES)
def test_capacidad_openspec_conserva_fuente_y_componentes(
    capability, source_rel, backend, frontend
):
    spec = ROOT / "openspec" / "specs" / capability / "spec.md"
    source = ROOT / "specs" / "003-operativo" / "paquetes" / source_rel
    content = spec.read_text(encoding="utf-8")

    assert source.is_file(), f"Falta la especificación original de {capability}"
    assert (ROOT / backend).exists(), f"Falta el backend trazado de {capability}"
    assert (ROOT / frontend).exists(), f"Falta el frontend trazado de {capability}"
    assert "## Purpose" in content
    assert "## Requirements" in content
    assert "### Requirement:" in content
    assert "#### Scenario:" in content


def test_alertas_vencimiento_conserva_especificacion_codigo_y_prueba():
    capability = ROOT / "openspec" / "specs" / "farmacia" / "alertas-vencimiento" / "spec.md"
    archive = (
        ROOT
        / "openspec"
        / "changes"
        / "archive"
        / "2026-08-29-mostrar-alertas-vencimiento-farmacia"
    )

    assert capability.is_file()
    assert (archive / "proposal.md").is_file()
    assert (archive / "design.md").is_file()
    assert (archive / "tasks.md").is_file()
    assert (ROOT / "backend" / "pruebas" / "test_farmacia_vencimiento.py").is_file()
