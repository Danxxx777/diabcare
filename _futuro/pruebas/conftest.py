"""
conftest.py — Configuración base para la suite de pruebas de DiabCare Analytics.

Garantiza que el paquete `backend` esté en el path para que las pruebas puedan
importar `Principal:app` y los servicios. Los fixtures de API viven en
`pruebas/api/conftest.py`.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
