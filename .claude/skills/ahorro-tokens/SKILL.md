---
name: ahorro-tokens
description: Modo de trabajo de bajo consumo de tokens para DiabCare. Usar SIEMPRE en este repo, en cualquier modelo. Respuestas directas, sin exploración redundante, sin informes largos.
---

# Modo bajo consumo

Regla base: **el contexto es el recurso caro, no el tiempo**. Cada archivo leído
de más y cada párrafo escrito de más se pagan en todas las llamadas siguientes.

## Al responder

- Da **la solución exacta**. Como mucho 2 opciones, nunca más.
- Sin preámbulo, sin resumen de lo que vas a hacer, sin recapitular lo ya dicho.
- Nada de informes largos ni tablas decorativas salvo que se pidan.
- Hay error → corrígelo y dilo en una línea.
- Es caché → dilo en una línea, no lo investigues.
- Hay que reiniciar → dilo en una línea.
- No expliques lo que el usuario ya sabe ni justifiques decisiones obvias.

## Al leer código

- **Nunca releas** un archivo ya leído en esta conversación. El estado se
  mantiene; Edit falla solo si el contenido cambió.
- `Grep` con `output_mode:"content"` y `-n`/`-C` antes que `Read` completo.
- `Read` con `offset`/`limit` sobre el rango que importa. Archivos de este repo
  que superan las 1.000 líneas (`ReportesServicio.py`, `navegacion.js`):
  **siempre** por rango, jamás enteros.
- `head_limit` en todo Grep exploratorio.
- No vuelvas a mapear la estructura del repo: está en `README.md` y en
  `specs/000-sistema-general/spec.md`.

## Al ejecutar

- Agrupa llamadas independientes en un solo bloque.
- Un comando que devuelve 200 líneas cuesta lo mismo que leerlas: filtra en el
  propio comando (`grep`, `head`, `| py -3 -c` que imprima solo el veredicto).
- No repitas un barrido completo de endpoints para validar un cambio puntual;
  prueba lo que tocaste. El barrido completo solo antes de cerrar un lote.
- No relances el servidor si ya hay uno sano: `curl -s -m 5 .../api/health`.
- No verifiques con una lectura extra lo que la herramienta ya confirmó.

## Contexto fijo del repo (no re-descubrir)

- Arranque: `py -3 servidor.py` desde la raíz. App y API en el mismo origen.
- Sesión por **cookie httpOnly**, no JWT en localStorage. No agregues
  cabeceras `Authorization` en el frontend.
- Datos en MinIO (`localhost:9000`, buckets `diabcare-app` y `diabetes-data`),
  en Parquet. Sin base SQL.
- Cambios en `.py` exigen reiniciar el backend; los de `frontend/` no.
- Pruebas rápidas: `backend/pruebas/`.

## Qué NO hacer

- No lances subagentes salvo petición explícita.
- No crees archivos de informe, resumen o documentación no pedidos.
- No propongas refactors fuera del encargo; si detectas algo, una línea y sigue.
- No pidas confirmación para lo que ya fue autorizado en la conversación.
