# Especificación de Paquete: Agenda / Citas clínicas

**Nivel**: Operativo · **Departamento**: Operaciones Clínicas

**Casos de uso operativos**: CU-O18 (Agendar cita, admin) y CU-O20 (Mis citas, médico) · OO5.2.1

**Estado**: Implementado · **Actualizado**: 2026-07-05

**Rutas**: `backend/paquetes/clinico/citas/`, `frontend/paginas/clinico/agenda/`, `frontend/paginas/clinico/mis_citas/`

## 1. Objetivo

Programar citas médicas: la **administración** agenda y asigna médico; el **médico** consulta su agenda y actualiza el estado de atención.

## 2. Actores

| Actor | Rol | Acciones |
|-------|-----|----------|
| Administrador | `administrador` | CRUD citas (Agenda) |
| Médico | `medico` | Ver mis citas, confirmar, marcar atendida |

Acceso agenda: `PERMISOS_MODULOS["citas"] = ["administrador"]`.  
Mis citas: `GET /api/citas/mis-citas` con `require_medico`.

## 3. Requisitos funcionales

### Administración (Agenda)
- **RF-O-CIT-001**: Listar y filtrar citas. *Real*: `GET /api/citas/`
- **RF-O-CIT-002**: Crear/editar/cancelar cita. *Real*: `POST/PUT/DELETE /api/citas/`
- **RF-O-CIT-003**: Citas del día. *Real*: `GET /api/citas/hoy`
- **RF-O-CIT-004**: Asignar médico desde catálogo. *Real*: `GET /api/usuarios/medicos`

### Médico (Mis citas)
- **RF-O-CIT-005**: Listar citas asignadas al médico logueado. *Real*: `GET /api/citas/mis-citas`
- **RF-O-CIT-006**: Confirmar o marcar atendida/no_asistio. *Real*: `PUT /api/citas/{id}/estado`
- **RF-O-CIT-007**: Botón **Atender** redirige a Consultas tras marcar `atendida`.

## 4. Estados de cita

`programada` → `confirmada` → `atendida`  
También: `cancelada` (admin), `no_asistio` (médico).

## 5. Reglas de negocio

- **RN-O-CIT-001**: El médico no crea citas; solo admin en Agenda.
- **RN-O-CIT-002**: Emparejamiento médico–cita por **nombre** del usuario (P2).
- **RN-O-CIT-003**: El médico solo cambia estado de **sus** citas asignadas.

## 6. Criterios de aceptación

- **CA-O-CIT-001**: Admin agenda cita para paciente X con médico Y.
- **CA-O-CIT-002**: Médico Y ve la cita en Mis citas, confirma y atiende.
- **CA-O-CIT-003**: Médico no accede a `/paginas/clinico/agenda/`.
