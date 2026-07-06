# Arranca DiabCare con consola silenciosa (solo advertencias y errores)
py -3 -m uvicorn Principal:app --reload --host 0.0.0.0 --port 8000 --log-level warning --no-access-log
