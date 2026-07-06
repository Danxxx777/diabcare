"""Unifica colores login (cyan) e incluye iconos.js en todas las páginas del app."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1] / "frontend" / "paginas"

REPLACEMENTS = [
    (r"rgba\(37,\s*99,\s*235", "rgba(34,211,238"),
    (r"rgba\(96,\s*165,\s*250", "rgba(103,232,249"),
    (r"rgba\(34,\s*197,\s*94", "rgba(74,222,128"),
    (r"rgba\(239,\s*68,\s*68", "rgba(248,113,113"),
    (r"rgba\(245,\s*158,\s*11", "rgba(251,191,36"),
    (r"#2563eb", "#22d3ee"),
    (r"#3b82f6", "#22d3ee"),
    (r"#60a5fa", "#67e8f9"),
    (r"#22c55e", "#4ade80"),
    (r"#ef4444", "#f87171"),
    (r"#f59e0b", "#fbbf24"),
]

ICONOS = '<script src="/estaticos/iconos.js"></script>'

for f in ROOT.rglob("*.html"):
    if "autenticacion" in str(f):
        continue
    c = f.read_text(encoding="utf-8")
    orig = c
    for pat, rep in REPLACEMENTS:
        c = re.sub(pat, rep, c, flags=re.IGNORECASE)
    if "iconos.js" not in c:
        c = c.replace(
            '<script src="/estaticos/navegacion.js"></script>',
            ICONOS + '\n<script src="/estaticos/navegacion.js"></script>',
        )
    if c != orig:
        f.write_text(c, encoding="utf-8")
        print("Recolored", f.relative_to(ROOT.parent.parent))

print("Done.")
