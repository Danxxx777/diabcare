# Trazabilidad principal de DiabCare

Relaciona cada capacidad de OpenSpec con su especificación original, código y pruebas enfocadas localizadas.

## clinico/admisiones

- OpenSpec: `openspec/specs/clinico/admisiones/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P-admisiones-spec.md`
- Backend: `backend/paquetes/clinico/admisiones/`
- Frontend: `frontend/paginas/clinico/admisiones/`
- Pruebas: `backend/pruebas/test_habitaciones.py`, `backend/pruebas/test_internacion_instrumental.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## clinico/citas

- OpenSpec: `openspec/specs/clinico/citas/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P-citas-spec.md`
- Backend: `backend/paquetes/clinico/citas/`
- Frontend: `frontend/paginas/clinico/agenda/`
- Pruebas: `backend/pruebas/test_openspec_trazabilidad.py`

## clinico/pacientes

- OpenSpec: `openspec/specs/clinico/pacientes/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P-pacientes-spec.md`
- Backend: `backend/paquetes/clinico/pacientes/`
- Frontend: `frontend/paginas/clinico/pacientes/`
- Pruebas: `backend/pruebas/test_openspec_trazabilidad.py`

## seguridad/autenticacion

- OpenSpec: `openspec/specs/seguridad/autenticacion/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P01-autenticacion-spec.md`
- Backend: `backend/paquetes/autenticacion/`
- Frontend: `frontend/paginas/seguridad/autenticacion/`
- Pruebas: `_futuro/pruebas/api/test_auditoria.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## seguridad/usuarios

- OpenSpec: `openspec/specs/seguridad/usuarios/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P02-usuarios-spec.md`
- Backend: `backend/paquetes/usuarios/`
- Frontend: `frontend/paginas/seguridad/usuarios/`
- Pruebas: `_futuro/pruebas/api/test_auditoria.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## clinico/comorbilidades

- OpenSpec: `openspec/specs/clinico/comorbilidades/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P03-comorbilidades-ext-spec.md`
- Backend: `backend/paquetes/comorbilidades/`
- Frontend: `frontend/paginas/clinico/comorbilidades/`
- Pruebas: `_futuro/pruebas/api/test_hospital_negocio.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## clinico/registros-clinicos

- OpenSpec: `openspec/specs/clinico/registros-clinicos/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P03-registros-clinicos-spec.md`
- Backend: `backend/paquetes/registros_clinicos/`
- Frontend: `frontend/paginas/clinico/registros_clinicos/`
- Pruebas: `_futuro/pruebas/api/test_benchmarking.py`, `_futuro/pruebas/api/test_modelo_ml.py`, `_futuro/pruebas/api/test_reportes.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## datos/dataset

- OpenSpec: `openspec/specs/datos/dataset/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P04-dataset-spec.md`
- Backend: `backend/paquetes/dataset/`
- Frontend: `frontend/paginas/datos/dataset/`
- Pruebas: `_futuro/pruebas/api/test_dataset.py`, `_futuro/pruebas/api/test_dwh.py`, `_futuro/pruebas/api/test_modelo_ml.py`, `backend/pruebas/test_hospital_api.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## analitica/analisis

- OpenSpec: `openspec/specs/analitica/analisis/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P05-analisis-spec.md`
- Backend: `backend/paquetes/registros_clinicos/`
- Frontend: `frontend/paginas/clinico/analisis/`
- Pruebas: `backend/pruebas/test_openspec_trazabilidad.py`

## analitica/prediccion

- OpenSpec: `openspec/specs/analitica/prediccion/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P06-prediccion-spec.md`
- Backend: `backend/paquetes/prediccion/`
- Frontend: `frontend/paginas/clinico/prediccion/`
- Pruebas: `_futuro/pruebas/api/test_benchmarking.py`, `_futuro/pruebas/api/test_modelo_ml.py`, `_futuro/pruebas/api/test_reportes.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## analitica/reportes

- OpenSpec: `openspec/specs/analitica/reportes/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P07-reportes/spec.md`
- Backend: `backend/paquetes/reportes/`
- Frontend: `frontend/paginas/clinico/reportes/`
- Pruebas: `_futuro/pruebas/api/test_auditoria.py`, `_futuro/pruebas/api/test_reportes.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## datos/pipeline-elt

- OpenSpec: `openspec/specs/datos/pipeline-elt/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P08-pipeline-elt-spec.md`
- Backend: `backend/paquetes/pipeline_elt/`
- Frontend: `frontend/paginas/datos/pipeline_elt/`
- Pruebas: `backend/pruebas/test_openspec_trazabilidad.py`

## seguridad/notificaciones

- OpenSpec: `openspec/specs/seguridad/notificaciones/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P10-notificaciones-spec.md`
- Backend: `backend/paquetes/notificaciones/`
- Frontend: `frontend/paginas/seguridad/notificaciones/`
- Pruebas: `_futuro/pruebas/api/test_notificaciones.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## seguridad/auditoria

- OpenSpec: `openspec/specs/seguridad/auditoria/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P11-auditoria-spec.md`
- Backend: `backend/paquetes/auditoria/`
- Frontend: `frontend/paginas/gobierno/auditoria/`
- Pruebas: `_futuro/pruebas/api/test_auditoria.py`, `_futuro/pruebas/api/test_configuracion.py`, `_futuro/pruebas/api/test_modelo_ml.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## gobierno/configuracion

- OpenSpec: `openspec/specs/gobierno/configuracion/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P12-configuracion-spec.md`
- Backend: `backend/paquetes/configuracion/`
- Frontend: `frontend/paginas/gobierno/configuracion/`
- Pruebas: `_futuro/pruebas/api/test_configuracion.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## datos/modelo-ml

- OpenSpec: `openspec/specs/datos/modelo-ml/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P14-modelo-ml-spec.md`
- Backend: `backend/paquetes/modelo_ml/`
- Frontend: `frontend/paginas/datos/modelo_ml/`
- Pruebas: `_futuro/pruebas/api/test_auditoria.py`, `_futuro/pruebas/api/test_benchmarking.py`, `_futuro/pruebas/api/test_modelo_ml.py`, `_futuro/pruebas/api/test_reportes.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## negocio/facturacion

- OpenSpec: `openspec/specs/negocio/facturacion/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P16-facturacion-spec.md`
- Backend: `backend/paquetes/facturacion/`
- Frontend: `frontend/paginas/negocio/facturacion/`
- Pruebas: `backend/pruebas/test_caja_horario.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## negocio/farmacia

- OpenSpec: `openspec/specs/negocio/farmacia/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P17-farmacia-spec.md`
- Backend: `backend/paquetes/farmacia/`
- Frontend: `frontend/paginas/negocio/farmacia/`
- Pruebas: `_futuro/pruebas/api/test_hospital_negocio.py`, `backend/pruebas/test_farmacia_vencimiento.py`, `backend/pruebas/test_hospital_api.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## clinico/laboratorio

- OpenSpec: `openspec/specs/clinico/laboratorio/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P18-laboratorio-spec.md`
- Backend: `backend/paquetes/laboratorio/`
- Frontend: `frontend/paginas/clinico/laboratorio/`
- Pruebas: `backend/pruebas/test_hospital_api.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## clinico/urgencias

- OpenSpec: `openspec/specs/clinico/urgencias/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P19-urgencias-spec.md`
- Backend: `backend/paquetes/urgencias/`
- Frontend: `frontend/paginas/clinico/urgencias/`
- Pruebas: `_futuro/pruebas/api/test_hospital_negocio.py`, `backend/pruebas/test_hospital_api.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## negocio/rrhh-costeo

- OpenSpec: `openspec/specs/negocio/rrhh-costeo/spec.md`
- Fuente original: `specs/003-operativo/paquetes/P20-rrhh-costeo-spec.md`
- Backend: `backend/paquetes/rrhh/`
- Frontend: `frontend/paginas/negocio/rrhh/`
- Pruebas: `backend/pruebas/test_hospital_api.py`, `backend/pruebas/test_openspec_trazabilidad.py`

## farmacia/alertas-vencimiento

- OpenSpec: `openspec/specs/farmacia/alertas-vencimiento/spec.md`
- Fuente original: `openspec/changes/archive/2026-08-29-mostrar-alertas-vencimiento-farmacia/specs/farmacia/alertas-vencimiento/spec.md`
- Backend: `backend/paquetes/farmacia/`
- Frontend: `frontend/paginas/negocio/farmacia/`
- Pruebas: `backend/pruebas/test_farmacia_vencimiento.py`
