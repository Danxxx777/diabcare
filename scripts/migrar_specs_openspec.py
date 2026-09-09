"""Migra las especificaciones operativas existentes al formato principal de OpenSpec."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "specs" / "003-operativo" / "paquetes"
DEST = ROOT / "openspec" / "specs"

CAPABILITIES = [
    ("clinico/admisiones", "P-admisiones-spec.md", "backend/paquetes/clinico/admisiones/", "frontend/paginas/clinico/admisiones/"),
    ("clinico/citas", "P-citas-spec.md", "backend/paquetes/clinico/citas/", "frontend/paginas/clinico/agenda/"),
    ("clinico/pacientes", "P-pacientes-spec.md", "backend/paquetes/clinico/pacientes/", "frontend/paginas/clinico/pacientes/"),
    ("seguridad/autenticacion", "P01-autenticacion-spec.md", "backend/paquetes/autenticacion/", "frontend/paginas/seguridad/autenticacion/"),
    ("seguridad/usuarios", "P02-usuarios-spec.md", "backend/paquetes/usuarios/", "frontend/paginas/seguridad/usuarios/"),
    ("clinico/comorbilidades", "P03-comorbilidades-ext-spec.md", "backend/paquetes/comorbilidades/", "frontend/paginas/clinico/comorbilidades/"),
    ("clinico/registros-clinicos", "P03-registros-clinicos-spec.md", "backend/paquetes/registros_clinicos/", "frontend/paginas/clinico/registros_clinicos/"),
    ("datos/dataset", "P04-dataset-spec.md", "backend/paquetes/dataset/", "frontend/paginas/datos/dataset/"),
    ("analitica/analisis", "P05-analisis-spec.md", "backend/paquetes/registros_clinicos/", "frontend/paginas/clinico/analisis/"),
    ("analitica/prediccion", "P06-prediccion-spec.md", "backend/paquetes/prediccion/", "frontend/paginas/clinico/prediccion/"),
    ("analitica/reportes", "P07-reportes/spec.md", "backend/paquetes/reportes/", "frontend/paginas/clinico/reportes/"),
    ("datos/pipeline-elt", "P08-pipeline-elt-spec.md", "backend/paquetes/pipeline_elt/", "frontend/paginas/datos/pipeline_elt/"),
    ("seguridad/notificaciones", "P10-notificaciones-spec.md", "backend/paquetes/notificaciones/", "frontend/paginas/seguridad/notificaciones/"),
    ("seguridad/auditoria", "P11-auditoria-spec.md", "backend/paquetes/auditoria/", "frontend/paginas/gobierno/auditoria/"),
    ("gobierno/configuracion", "P12-configuracion-spec.md", "backend/paquetes/configuracion/", "frontend/paginas/gobierno/configuracion/"),
    ("datos/modelo-ml", "P14-modelo-ml-spec.md", "backend/paquetes/modelo_ml/", "frontend/paginas/datos/modelo_ml/"),
    ("negocio/facturacion", "P16-facturacion-spec.md", "backend/paquetes/facturacion/", "frontend/paginas/negocio/facturacion/"),
    ("negocio/farmacia", "P17-farmacia-spec.md", "backend/paquetes/farmacia/", "frontend/paginas/negocio/farmacia/"),
    ("clinico/laboratorio", "P18-laboratorio-spec.md", "backend/paquetes/laboratorio/", "frontend/paginas/clinico/laboratorio/"),
    ("clinico/urgencias", "P19-urgencias-spec.md", "backend/paquetes/urgencias/", "frontend/paginas/clinico/urgencias/"),
    ("negocio/rrhh-costeo", "P20-rrhh-costeo-spec.md", "backend/paquetes/rrhh/", "frontend/paginas/negocio/rrhh/"),
]


def clean(text: str) -> str:
    text = text.replace("—", "-").replace("–", "-").replace("·", "-")
    text = re.sub(r"\s*\*Real\*:[^\r\n]*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def section(text: str, heading_pattern: str) -> str:
    match = re.search(
        rf"^##\s+(?:\d+(?:[.-]\d+)?\.\s*)?{heading_pattern}\s*$\n(.*?)(?=^##\s|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def title(text: str) -> str:
    first = text.splitlines()[0].lstrip("# ").strip()
    return clean(first.split(":", 1)[-1])


def purpose(text: str, capability_title: str) -> str:
    objective = section(text, "Objetivo")
    value = clean(objective)
    if len(value) < 50:
        value = f"Definir el comportamiento observable de {capability_title} dentro de DiabCare y las reglas que deben respetar sus usuarios autorizados."
    return value


def functional_requirements(text: str, capability_title: str, objective: str) -> list[tuple[str, str]]:
    body = section(text, "Requisitos funcionales") or section(text, "Requisitos")
    blocks = re.findall(
        r"^-\s+\*\*([^*]+)\*\*:?\s*(.*?)(?=^-\s+\*\*|^##\s|\Z)",
        body,
        flags=re.MULTILINE | re.DOTALL,
    )
    requirements = []
    for identifier, statement in blocks:
        normalized = clean(statement)
        if not normalized:
            continue
        normalized = re.sub(r"\bDEBE\b", "SHALL", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bNO SHALL\b", "MUST NOT", normalized, flags=re.IGNORECASE)
        requirements.append((clean(identifier), normalized))

    if requirements:
        return requirements

    fallback = clean(objective)
    if not fallback:
        fallback = f"El sistema SHALL proporcionar la capacidad {capability_title} a los usuarios autorizados."
    elif "SHALL" not in fallback and "MUST" not in fallback:
        fallback = f"El sistema SHALL {fallback[0].lower() + fallback[1:]}"
    return [(f"Comportamiento de {capability_title}", fallback)]


def render_spec(capability: str, source: Path) -> str:
    raw = source.read_text(encoding="utf-8")
    capability_title = title(raw)
    objective = purpose(raw, capability_title)
    requirements = functional_requirements(raw, capability_title, objective)
    lines = [
        f"# {capability_title} Specification",
        "",
        "## Purpose",
        "",
        objective,
        "",
        "## Requirements",
        "",
    ]
    for identifier, statement in requirements:
        lines.extend([
            f"### Requirement: {identifier}",
            "",
            statement,
            "",
            f"#### Scenario: Cumplimiento de {identifier}",
            f"- **WHEN** un usuario autorizado utiliza la capacidad `{capability}`",
            f"- **THEN** el sistema SHALL cumplir el comportamiento definido en `{identifier}`",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def discover_tests(terms: list[str]) -> list[str]:
    roots = [ROOT / "backend" / "pruebas", ROOT / "_futuro" / "pruebas"]
    matches = []
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("test_*.py"):
            searchable = path.name.lower() + "\n" + path.read_text(encoding="utf-8", errors="ignore").lower()
            if any(term in searchable for term in terms):
                matches.append(path.relative_to(ROOT).as_posix())
    traceability_test = ROOT / "backend" / "pruebas" / "test_openspec_trazabilidad.py"
    if traceability_test.exists():
        matches.append(traceability_test.relative_to(ROOT).as_posix())
    return sorted(set(matches))


def main() -> None:
    trace_rows = []
    for capability, source_rel, backend, frontend in CAPABILITIES:
        source = LEGACY / source_rel
        destination = DEST / capability / "spec.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render_spec(capability, source), encoding="utf-8", newline="\n")
        terms = [part for part in re.split(r"[/\-]", capability.split("/", 1)[-1]) if len(part) > 4]
        tests = discover_tests(terms)
        trace_rows.append((capability, source.relative_to(ROOT).as_posix(), backend, frontend, tests))

    trace_rows.append((
        "farmacia/alertas-vencimiento",
        "openspec/changes/archive/2026-08-29-mostrar-alertas-vencimiento-farmacia/specs/farmacia/alertas-vencimiento/spec.md",
        "backend/paquetes/farmacia/",
        "frontend/paginas/negocio/farmacia/",
        ["backend/pruebas/test_farmacia_vencimiento.py"],
    ))

    trace = [
        "# Trazabilidad principal de DiabCare",
        "",
        "Relaciona cada capacidad de OpenSpec con su especificación original, código y pruebas enfocadas localizadas.",
        "",
    ]
    for capability, source, backend, frontend, tests in trace_rows:
        trace.extend([
            f"## {capability}",
            "",
            f"- OpenSpec: `openspec/specs/{capability}/spec.md`",
            f"- Fuente original: `{source}`",
            f"- Backend: `{backend}`",
            f"- Frontend: `{frontend}`",
            "- Pruebas: " + (", ".join(f"`{test}`" for test in tests) if tests else "sin prueba enfocada localizada"),
            "",
        ])
    (ROOT / "openspec" / "TRAZABILIDAD.md").write_text("\n".join(trace), encoding="utf-8", newline="\n")
    print(f"Migradas {len(CAPABILITIES)} capacidades de DiabCare.")


if __name__ == "__main__":
    main()
