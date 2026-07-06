"""Actualiza páginas del frontend: favicon, api.js, getApi(), topbar health."""
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "frontend" / "paginas"
FAVICON = """<link rel="icon" href="/estaticos/img/favicon.ico" sizes="32x32">
<link rel="icon" href="/estaticos/img/favicon.svg" type="image/svg+xml">"""
API_SCRIPT = '<script src="/estaticos/api.js"></script>'
DASH_CSS = '<link rel="stylesheet" href="/estaticos/dashboard.css">'

for f in ROOT.rglob("*.html"):
    if "autenticacion" in str(f):
        continue
    c = f.read_text(encoding="utf-8")
    orig = c
    if "favicon.ico" not in c:
        c = re.sub(r"(<title>[^<]+</title>)", r"\1\n" + FAVICON, c, count=1)
    if "api.js" not in c:
        c = c.replace(
            '<script src="/estaticos/navegacion.js"></script>',
            '<script src="/estaticos/navegacion.js"></script>\n' + API_SCRIPT,
        )
    if "dashboard.css" not in c and "estilos.css" in c:
        c = c.replace(
            '<link rel="stylesheet" href="/estaticos/estilos.css">',
            '<link rel="stylesheet" href="/estaticos/estilos.css">\n' + DASH_CSS,
        )
    c = re.sub(
        r"const API\s*=\s*'http://localhost:8000'",
        "const API = DiabCareNav.getApi()",
        c,
    )
    c = c.replace(
        '<div class="tb-online"><div class="tb-online-dot"></div>MinIO conectado</div>',
        '<div class="tb-online"><div class="tb-online-dot"></div>'
        '<span class="tb-online-label">MinIO conectado</span></div>',
    )
    if c != orig:
        f.write_text(c, encoding="utf-8")
        print("Updated", f.relative_to(ROOT.parent.parent))

print("Done.")
