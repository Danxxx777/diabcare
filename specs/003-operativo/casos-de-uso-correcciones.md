# Correcciones documentales — entrega GA07 (2026-07-05)

**Para copiar en** `corregir.docx`, `TA 06.docx` o documento de casos de uso de la universidad.

Este archivo lista **qué corregir** tras implementar el flujo clínico (pacientes, admisiones, agenda, mis citas, notificaciones, foto).

---

## 1. ¿Hay que corregir el Word (`corregir.docx`)?

**Sí**, si tu documento de entrega aún dice:

| Texto viejo (incorrecto) | Corregir a |
|--------------------------|------------|
| El médico agenda citas | **El administrador** agenda citas y **asigna** al médico |
| Médico accede a Agenda | Médico accede a **Mis citas** (solo lectura + confirmar/atender) |
| Admisiones: médico y admin | **Solo administrador** registra admisiones |
| Médico elige su nombre en cita | Admin elige médico del **listado de usuarios rol médico** |
| CU-O03 = único flujo clínico | Añadir expediente (CU-O17), admisión (CU-O19), agenda (CU-O18), mis citas (CU-O20) |
| Matriz permisos sin pacientes/admisiones/citas | Ver §3 de este documento |
| P10 notificaciones “planificado” | **Implementado** (alertas clínicas + Brevo; churn CU-O16 pendiente) |
| Sin foto de paciente | **Implementado** (HCE + MinIO) |

---

## 2. Casos de uso nuevos / ampliados (extensión GA07)

> Numeración **CU-O17–CU-O20** extiende TA06 (CU-O01–CU-O16) sin reemplazar los originales.

### CU-O17 — Gestionar expediente del paciente (HCE)

| Campo | Descripción |
|-------|-------------|
| **Actor principal** | Administrador, Médico |
| **Objetivo** | Mantener la historia clínica electrónica del paciente |
| **Precondición** | Usuario autenticado con rol permitido |
| **Flujo principal** | 1. Actor accede a Pacientes / HCE. 2. Crea o edita datos (nombre, documento, sede). 3. Opcional: sube foto. 4. Sistema guarda en Parquet y MinIO. |
| **Postcondición** | Expediente disponible para agenda, admisiones y consultas |
| **Paquete** | Pacientes (`P-pacientes-spec.md`) |
| **Estado** | Implementado |

### CU-O18 — Agendar cita clínica (administración)

| Campo | Descripción |
|-------|-------------|
| **Actor principal** | **Administrador** |
| **Objetivo** | Programar una cita asignando paciente, médico, fecha y motivo |
| **Precondición** | Paciente registrado; al menos un usuario rol **médico** activo |
| **Flujo principal** | 1. Admin abre Agenda. 2. Selecciona paciente y **médico asignado**. 3. Indica fecha, hora y motivo. 4. Sistema crea cita en estado `programada`. |
| **Regla** | El médico **no** crea citas en este módulo |
| **Paquete** | Citas / Agenda (`P-citas-spec.md`) |
| **Estado** | Implementado |

### CU-O19 — Registrar admisión hospitalaria

| Campo | Descripción |
|-------|-------------|
| **Actor principal** | **Administrador** |
| **Objetivo** | Registrar ingreso (ambulatoria, urgencia u hospitalización) |
| **Precondición** | Paciente registrado |
| **Flujo principal** | 1. Admin abre Admisiones. 2. Selecciona paciente, tipo, servicio y **médico tratante**. 3. Registra fechas y motivo. 4. Sistema guarda admisión. |
| **Paquete** | Admisiones (`P-admisiones-spec.md`) |
| **Estado** | Implementado |

### CU-O20 — Consultar y atender mis citas (médico)

| Campo | Descripción |
|-------|-------------|
| **Actor principal** | **Médico** |
| **Objetivo** | Ver citas asignadas por administración y registrar la atención |
| **Precondición** | Médico autenticado; cita asignada a su nombre de usuario |
| **Flujo principal** | 1. Médico abre **Mis citas**. 2. Ve listado filtrado por su nombre. 3. Confirma cita (`confirmada`). 4. Pulsa **Atender** → estado `atendida` → redirige a Consultas. |
| **Flujo alterno** | Marcar `no_asistio` si el paciente no acude |
| **Paquete** | Citas (`P-citas-spec.md`) |
| **Estado** | Implementado |

### CU-O03 / CU-O04 — Sin cambio de numeración

Siguen siendo **CRUD y filtros de registros clínicos** (consulta médica documentada). El flujo CU-O20 enlaza con CU-O03 al pulsar **Atender**.

### CU-O10 / CU-O16 / P10 — Actualizar redacción

| CU | Corrección en Word |
|----|-------------------|
| **CU-O10** | Incluir dashboard + **alertas clínicas** (umbrales HbA1c/glucosa) |
| **CU-O16** | Dejar como **parcial**: alertas clínicas sí; **churn comercial ML** pendiente |
| **P10** | Estado **Implementado (parcial GA07)** — ver `P10-notificaciones-spec.md` |

---

## 3. Matriz de permisos (pegar en corregir.docx)

| Módulo | administrador | medico | analista |
|--------|:---:|:---:|:---:|
| Pacientes / HCE | ✅ | ✅ | |
| Admisiones | ✅ | | |
| Agenda (citas) | ✅ | | |
| Mis citas | | ✅ | |
| Consultas (registros) | ✅ | ✅ | |
| Análisis / BI | ✅ | ✅ | ✅ |
| Predicción ML | ✅ | ✅ | ✅ |
| Reportes PDF | ✅ | ✅ | |
| Notificaciones | ✅ | ✅ | ✅ |
| Usuarios / Config / Auditoría | ✅ | | |
| Dataset / Pipeline / Modelo ML | ✅ | | ✅ |

---

## 4. Diagrama de flujo (texto para Word)

```
[Admin: Alta paciente HCE]
        ↓
   ┌────┴────┐
   ↓         ↓
[Agenda]  [Admisión]
   ↓         ↓
[Médico: Mis citas → Atender]
        ↓
[Consulta / Registro clínico CU-O03]
        ↓
[Alertas P10] → [Análisis / Reporte / Predicción]
```

Referencia completa: `flujo-clinico.md`

---

## 5. Actores — tabla corregida (operativo-spec / TA06)

| Actor | Rol | Casos de uso principales (actualizado) |
|-------|-----|----------------------------------------|
| **Administrador** | `administrador` | CU-O01, CU-O02, **CU-O17, CU-O18, CU-O19** + gobierno |
| **Médico** | `medico` | **CU-O20**, CU-O03, CU-O04, CU-O07, CU-O08, reportes |
| **Analista** | `analista` | CU-O05, CU-O06, CU-O07, CU-O09 |

---

## 6. Archivos del repo ya actualizados (no duplicar trabajo)

- `specs/003-operativo/flujo-clinico.md`
- `specs/003-operativo/paquetes/P-pacientes-spec.md`
- `specs/003-operativo/paquetes/P-admisiones-spec.md`
- `specs/003-operativo/paquetes/P-citas-spec.md`
- `specs/003-operativo/trazabilidad.md`
- `specs/000-sistema-general/spec.md` (§10 permisos)
- `specs/design.md`

---

## 7. Checklist entrega (2 horas)

- [ ] Pegar CU-O17–CU-O20 en documento Word de casos de uso
- [ ] Corregir actor en “Agendar cita” → Administrador
- [ ] Añadir “Mis citas” para Médico
- [ ] Actualizar matriz de permisos (§3)
- [ ] Mencionar foto paciente y notificaciones Brevo como implementados
- [ ] Demo en vivo según `flujo-clinico.md` §5
