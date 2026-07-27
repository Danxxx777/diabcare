# Especificación de Paquete: P11 — Auditoría y Trazabilidad

**Nivel**: Operativo · **Departamento**: Gobierno y Cumplimiento · **Paquete**: P11

**Fuente TA06**: trazabilidad de operaciones sensibles (RG-005, Principio V constitución)

**Estado**: Implementado (entrega GA07)

**Rutas reales**: `backend/paquetes/auditoria/AuditoriaRutas.py`,
`backend/paquetes/auditoria/AuditoriaServicio.py`,
`frontend/paginas/gobierno/auditoria/index.html`

## 1. Objetivo

Registrar y consultar eventos del sistema (accesos, consultas, predicciones,
generación de reportes) para cumplimiento y trazabilidad clínica.

## 2. Contexto

Complementa CU-O01–O10: las operaciones sobre datos clínicos y configuración
deben dejar huella auditable. Persistencia en MinIO `diabcare-app/auditoria/eventos.parquet`
con `ip`, `user_agent`, `sesion_id`, `resultado`; filtros por usuario/módulo/resultado.

## 3. Actores

| Actor | Rol | Acciones |
|-------|-----|----------|
| Administrador | `administrador` | Consultar eventos y estadísticas |

Acceso: `PERMISOS_MODULOS["auditoria"] = ["administrador"]`.

## 4. Requisitos funcionales

- **RF-O-P11-001**: Listar eventos con paginación y filtro por tipo.
  *Real*: `GET /api/auditoria/`.
- **RF-O-P11-002**: Exponer estadísticas (total, hoy, errores, usuarios).
  *Real*: `GET /api/auditoria/estadisticas`.
- **RF-O-P11-003**: Registrar eventos desde otros módulos (registros, predicción,
  reportes, configuración) de forma resiliente.

## 5. Requisitos no funcionales

- **RNF-O-P11-001**: Fallo de auditoría no debe interrumpir la operación de negocio.
- **RNF-O-P11-002**: Solo administrador accede al módulo.

## 6. Reglas de negocio

- **RN-O-P11-001**: Cada evento incluye id, fecha, usuario, tipo, módulo, detalle.

## 7. Entradas

- Token JWT de administrador; filtros opcionales `skip`, `limit`, `tipo`.

## 8. Salidas

- Lista `{ total, eventos[] }` y estadísticas agregadas.

## 9. Escenarios

### Escenario 1: Consulta de eventos
- **Dado** un administrador autenticado,
- **Cuando** consulta `/api/auditoria/?limit=20`,
- **Entonces** recibe los eventos más recientes.

### Escenario 2: Acceso denegado
- **Dado** un médico autenticado,
- **Cuando** intenta acceder al módulo,
- **Entonces** recibe HTTP 403.

## 10. Criterios de aceptación

- **CA-O-P11-001**: Tras filtrar registros o predecir, aparece evento en auditoría.
- **CA-O-P11-002**: Rol no autorizado recibe 403.

## 11. Dependencias

- P1 (JWT), MinIO, eventos emitidos por P3, P6, P7, P12.

## 12. Fuera de alcance

- Exportación masiva a SIEM externo; retención legal automatizada (> GA07).
