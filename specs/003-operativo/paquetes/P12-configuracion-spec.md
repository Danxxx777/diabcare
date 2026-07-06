# Especificación de Paquete: P12 — Configuración del Sistema

**Nivel**: Operativo · **Departamento**: Gobierno y Cumplimiento · **Paquete**: P12

**Fuente TA06**: parámetros operativos del DWH y plataforma (OE4, OT4.1)

**Estado**: Implementado (entrega GA07)

**Rutas reales**: `backend/paquetes/configuracion/ConfiguracionRutas.py`,
`backend/paquetes/configuracion/ConfiguracionServicio.py`,
`frontend/paginas/gobierno/configuracion/index.html`

## 1. Objetivo

Permitir al administrador consultar y ajustar parámetros del sistema (MinIO,
umbrales clínicos, preferencias) sin modificar código.

## 2. Contexto

Centraliza ajustes que afectan alertas del dashboard (TA06 §13: prevalencia,
HbA1c) y conexión al almacenamiento Parquet.

## 3. Actores

| Actor | Rol | Acciones |
|-------|-----|----------|
| Administrador | `administrador` | Leer y guardar configuración |

Acceso: `PERMISOS_MODULOS["configuracion"] = ["administrador"]`.

## 4. Requisitos funcionales

- **RF-O-P12-001**: Obtener configuración actual. *Real*: `GET /api/configuracion/`.
- **RF-O-P12-002**: Persistir cambios con auditoría. *Real*: `POST /api/configuracion/`.

## 5. Requisitos no funcionales

- **RNF-O-P12-001**: Solo administrador; cambios auditados en P11.

## 6. Reglas de negocio

- **RN-O-P12-001**: Configuración persiste en MinIO `diabcare-app/configuracion/`.

## 7–8. Entradas y salidas

- Entrada: JSON con parámetros válidos.
- Salida: configuración aplicada o mensaje de error.

## 9. Escenarios

### Escenario 1: Consultar configuración
- **Dado** administrador autenticado → **Entonces** recibe parámetros actuales.

### Escenario 2: Guardar cambio
- **Dado** payload válido → **Entonces** persiste y registra evento en P11.

## 10. Criterios de aceptación

- **CA-O-P12-001**: GET devuelve estructura coherente.
- **CA-O-P12-002**: POST persiste y genera auditoría.

## 11. Dependencias

- P1, P11, MinIO.

## 12. Fuera de alcance

- Configuración multi-tenant por institución (futuro TA06 Dim_Institucion).
