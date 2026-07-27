# Especificación de Paquete: P2 — Gestión de Usuarios

**Nivel**: Operativo · **Departamento**: Seguridad e Identidad · **Paquete**: P2

**Caso de uso operativo**: CU-O02 (Gestionar usuarios: crear, rol, desactivar) · OO5.1.1

**Estado**: Implementado

**Creado**: 2026-06-19

**Rutas reales**: `backend/paquetes/usuarios/UsuariosRutas.py`,
`backend/paquetes/usuarios/UsuariosServicio.py`,
`frontend/paginas/seguridad/usuarios/index.html`

## 1. Objetivo

Permitir al administrador gestionar las cuentas de usuario del sistema: creación,
consulta, edición, desactivación y asignación de roles.

## 2. Contexto

Complementa a P1: mientras P1 autentica, P2 administra el ciclo de vida de las
cuentas. Solo el administrador tiene acceso.

## 3. Actores

| Actor | Rol | Acciones |
|-------|-----|----------|
| Administrador | `administrador` | CRUD de usuarios y asignación de roles |

- **RF-O-P02-010**: Solicitud pública de acceso sin contraseña; al aprobar, se genera
  clave temporal, se envía por correo (o `password_temp_dev` si email off) y la cuenta
  queda con `debe_cambiar_password=true`.

## 4. Requisitos funcionales

- **RF-O-P02-001** (CU-O02): El administrador DEBE poder listar usuarios.
  *Real*: `GET /api/usuarios/`.
- **RF-O-P02-002**: El administrador DEBE poder consultar los roles válidos.
  *Real*: `GET /api/usuarios/roles`.
- **RF-O-P02-003**: El administrador DEBE poder obtener un usuario por id.
  *Real*: `GET /api/usuarios/{id_usuario}`.
- **RF-O-P02-004**: El administrador DEBE poder crear un usuario con rol válido.
  *Real*: `POST /api/usuarios/`.
- **RF-O-P02-005**: El administrador DEBE poder editar un usuario.
  *Real*: `PUT /api/usuarios/{id_usuario}`.
- **RF-O-P02-006**: El administrador DEBE poder desactivar un usuario.
  *Real*: `DELETE /api/usuarios/{id_usuario}`.
- **RF-O-P02-007**: El administrador DEBE poder asignar/cambiar el rol.
  *Real*: `PUT /api/usuarios/{id_usuario}/rol`.

## 5. Requisitos no funcionales

- **RNF-O-P02-001**: Todos los endpoints exigen rol `administrador` (403 si no).
- **RNF-O-P02-002**: Un rol inválido en creación/edición devuelve 400.

## 6. Reglas de negocio

- **RN-O-P02-001**: Roles válidos: `administrador`, `medico`, `analista`.
- **RN-O-P02-002**: El administrador NO PUEDE desactivar su propia cuenta.
- **RN-O-P02-003**: El administrador NO PUEDE cambiar su propio rol.

## 7. Entradas

- Crear: nombre, email, password, rol.
- Editar: nombre, email, rol (opcionales).
- Asignar rol: rol.

## 8. Salidas

- Usuario creado/editado, listados de usuarios y roles, mensajes de error
  (400/404/403).

## 9. Escenarios

### Escenario 1: Crear usuario
- **Dado** un administrador autenticado,
- **Cuando** crea un usuario con rol válido,
- **Entonces** el sistema lo registra y lo devuelve.

### Escenario 2: Auto-desactivación bloqueada
- **Dado** un administrador autenticado,
- **Cuando** intenta desactivar su propia cuenta,
- **Entonces** el sistema responde 400 e impide la operación.

## 10. Criterios de aceptación

- **CA-O-P02-001**: El administrador completa el CRUD de un usuario.
- **CA-O-P02-002**: La creación con rol inválido devuelve 400.
- **CA-O-P02-003**: La auto-desactivación y el auto-cambio de rol se bloquean.

## 11. Dependencias

- P1 (autenticación y verificación de rol administrador).

## 12. Restricciones y fuera de alcance

- Fuera de alcance: autoregistro público de usuarios y gestión de equipos/grupos.
