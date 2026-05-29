import os

base = r"D:\6to Software\Construcción de Software\diabcare\frontend\paginas"

paginas = {
    "autenticacion": "autenticacion",
    "analisis": "analisis", 
    "usuarios": "usuarios",
    "registros_clinicos": "registros_clinicos"
}

for carpeta in paginas:
    ruta = os.path.join(base, carpeta, "index.html")
    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()
    print(f"{carpeta}: {len(contenido)} bytes")
