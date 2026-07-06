# Especificación de Paquete: P3 — Gestión de Registros Clínicos

**Nivel**: Operativo · **Departamento**: Operaciones Clínicas · **Paquete**: P3

**Casos de uso operativos**: CU-O03 (CRUD registros) y CU-O04 (Filtrar) · OO5.2.1

**Estado**: Implementado

**Creado**: 2026-06-19

**Rutas reales**: `backend/paquetes/registros_clinicos/RegistrosClinicosRutas.py`,
`backend/paquetes/registros_clinicos/RegistrosClinicosServicio.py`,
`frontend/paginas/clinico/registros_clinicos/index.html`

## 1. Objetivo

Permitir al médico gestionar registros clínicos de pacientes (alta, consulta,
edición, baja) y buscarlos con filtros.

## 2. Contexto

Es el núcleo de las operaciones clínicas diarias. Los registros alimentan las
estadísticas (P5), la predicción (P6) y los reportes (P7).

## 3. Actores

| Actor | Rol | Acciones |
|-------|-----|----------|
| Médico | `medico` | CRUD y búsqueda de registros |
| Administrador | `administrador` | Acceso total |

Acceso: `PERMISOS_MODULOS["registros"] = ["administrador", "medico"]`.

## 4. Requisitos funcionales

- **RF-O-P03-001** (CU-O03): El sistema DEBE permitir crear un registro clínico.
  *Real*: `POST /api/registros/`.
- **RF-O-P03-002** (CU-O03): El sistema DEBE permitir listar registros con
  paginación. *Real*: `GET /api/registros/` (limit, offset).
- **RF-O-P03-003** (CU-O03): El sistema DEBE permitir obtener un registro por id.
  *Real*: `GET /api/registros/{encounter_id}`.
- **RF-O-P03-004** (CU-O03): El sistema DEBE permitir actualizar un registro.
  *Real*: `PUT /api/registros/{encounter_id}`.
- **RF-O-P03-005** (CU-O03): El sistema DEBE permitir eliminar un registro.
  *Real*: `DELETE /api/registros/{encounter_id}`.
- **RF-O-P03-006** (CU-O04): El sistema DEBE permitir buscar/filtrar por diabetes,
  género, ubicación y rango de edad. *Real*: `GET /api/registros/buscar`.
- **RF-O-P03-007**: El sistema DEBE exponer estadísticas de los registros.
  *Real*: `GET /api/registros/estadisticas`.

## 5. Requisitos no funcionales

- **RNF-O-P03-001**: El acceso exige rol `medico` o `administrador`.
- **RNF-O-P03-002**: El listado limita el tamaño de página (límite máximo 500).

## 6. Reglas de negocio

- **RN-O-P03-001**: Los campos clínicos siguen los rangos del modelo de datos
  (gender, age, bmi, hbA1c_level, blood_glucose_level, diabetes, etc.).
- **RN-O-P03-002**: La actualización aplica solo los campos provistos.

## 7. Entradas

- Crear: year, gender, age, location, hypertension, heart_disease,
  smoking_history, bmi, hbA1c_level, blood_glucose_level, diabetes.
- Buscar: diabetes, gender, location, age_min, age_max.

## 8. Salidas

- Registros creados/actualizados, listados paginados, resultados de búsqueda,
  estadísticas.

## 9. Escenarios

### Escenario 1: Crear y consultar
- **Dado** un médico autenticado,
- **Cuando** crea un registro válido,
- **Entonces** el registro aparece en el listado y puede consultarse por id.

### Escenario 2: Búsqueda filtrada
- **Dado** registros existentes,
- **Cuando** busca con `diabetes=1` y un rango de edad,
- **Entonces** el sistema devuelve solo los registros que cumplen los filtros.

## 10. Criterios de aceptación

- **CA-O-P03-001**: El médico completa el ciclo CRUD de un registro.
- **CA-O-P03-002**: La búsqueda filtrada devuelve el subconjunto correcto.
- **CA-O-P03-003**: Un rol sin permiso recibe 403.

## 11. Dependencias

- P1 (sesión y rol). Datos cargados por P4/P8 en el DWH.

## 12. Restricciones y fuera de alcance

- Fuera de alcance: historia clínica longitudinal y adjuntos de imágenes médicas.
