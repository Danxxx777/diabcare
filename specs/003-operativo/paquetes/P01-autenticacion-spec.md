# Especificación de Paquete: P1 — Autenticación y Seguridad

**Nivel**: Operativo · **Departamento**: Seguridad e Identidad · **Paquete**: P1

**Caso de uso operativo**: CU-O01 (Iniciar sesión con autenticación JWT) · OO5.1.1

**Estado**: Implementado

**Creado**: 2026-06-19

**Rutas reales**: `backend/api/autenticacion/AutenticacionRutas.py`,
`backend/servicios/autenticacion/AutenticacionServicio.py`,
`frontend/paginas/autenticacion/index.html`

## 1. Objetivo

Permitir que los usuarios accedan de forma segura al sistema mediante
autenticación con token JWT y control de acceso por roles.

## 2. Contexto

Es el paquete base del sistema: todos los demás módulos dependen de una sesión
autenticada. Define los roles y la verificación de tokens usada por el resto.

## 3. Actores

| Actor | Rol | Acciones |
|-------|-----|----------|
| Cualquier usuario | `administrador`, `medico`, `analista` | Iniciar sesión, cerrar sesión, recuperar/cambiar contraseña |

## 4. Requisitos funcionales

- **RF-O-P01-001** (CU-O01): El sistema DEBE autenticar con email y contraseña y
  emitir un token JWT (HS256) con el rol. *Real*: `POST /api/auth/login`.
- **RF-O-P01-002**: El sistema DEBE verificar la validez de un token.
  *Real*: `GET /api/auth/verificar`.
- **RF-O-P01-003**: El sistema DEBE permitir cerrar sesión.
  *Real*: `POST /api/auth/logout`.
- **RF-O-P01-004**: El sistema DEBE permitir recuperar contraseña mediante
  código. *Real*: `POST /api/auth/recuperar`, `POST /api/auth/resetear`.
- **RF-O-P01-005**: El sistema DEBE permitir cambiar la contraseña autenticado.
  *Real*: `PUT /api/auth/cambiar-password`.
- **RF-O-P01-006**: El sistema DEBE restringir el acceso a cada módulo según la
  matriz de permisos por rol. *Real*: `utilidades/Dependencias.require_modulo`.

## 5. Requisitos no funcionales

- **RNF-O-P01-001**: Las contraseñas NO DEBEN almacenarse en texto plano.
- **RNF-O-P01-002**: El token JWT usa algoritmo HS256.
- **RNF-O-P01-003**: Las credenciales inválidas devuelven 401 sin revelar qué
  campo falló.

## 6. Reglas de negocio

- **RN-O-P01-001**: Solo los roles válidos (`administrador`, `medico`,
  `analista`) son aceptados.
- **RN-O-P01-002**: Un token inválido o ausente impide el acceso a módulos
  protegidos.

## 7. Entradas

- Login: email, contraseña.
- Recuperación: email, código, nueva contraseña.
- Cambio: contraseña actual, contraseña nueva, token.

## 8. Salidas

- Token JWT y datos de sesión (rol).
- Mensajes de confirmación o error (401/400/404).

## 9. Escenarios

### Escenario 1: Login exitoso
- **Dado** un usuario registrado con credenciales correctas,
- **Cuando** envía email y contraseña,
- **Entonces** recibe un token JWT y su rol.

### Escenario 2: Login fallido
- **Dado** credenciales incorrectas,
- **Cuando** intenta iniciar sesión,
- **Entonces** el sistema responde 401 con "Credenciales inválidas".

## 10. Criterios de aceptación

- **CA-O-P01-001**: Con credenciales válidas se obtiene token y rol.
- **CA-O-P01-002**: Con credenciales inválidas se recibe 401.
- **CA-O-P01-003**: Un token válido habilita el acceso a los módulos del rol.

## 11. Dependencias

- Ninguna (paquete base). El resto de paquetes dependen de P1.

## 12. Restricciones y fuera de alcance

- Restricción: algoritmo JWT HS256 según constitución.
- Fuera de alcance: SSO/OAuth externo y autenticación multifactor.
