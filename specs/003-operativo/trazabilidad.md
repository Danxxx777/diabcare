# Trazabilidad Empresarial — Nivel Operativo

**Creado**: 2026-06-19 · **Actualizado**: 2026-06-20 (GA07)

**Fuentes**:

- **TA06** — *Estrategia Documental Empresarial DiabCare Analytics* (`TA 06.docx`,
  Byron Loor Mendoza): OE, OT, OO, CU-O01–CU-O16, modelo Fact-Dim, pipeline ELT.
- Código verificado: `backend/paquetes/`, `backend/nucleo/`, `frontend/paginas/`, `specs/`.

**Estructura de código (2026-07)**: paquetes en `backend/paquetes/{nombre}/`;
frontend por departamento (`seguridad/`, `clinico/`, `datos/`, `gobierno/`).
Los identificadores P1–P15 siguen en esta trazabilidad; no van en nombres de carpeta.
Mapeo completo: `specs/000-sistema-general/spec.md` §5.1.

Cumple el **Principio VI** de la constitución: cada CU-O es trazable en la cadena
**OE → OT → OO → Departamento → Paquete → CU-O → Historia de usuario**.

---

## 1. Tabla de trazabilidad (CU-O01 – CU-O16)

| CU-O | OE (TA06) | OT | OO (TA06) | Departamento | Paquete | Estado GA07 |
|------|-----------|-----|-----------|--------------|---------|-------------|
| CU-O01 Login JWT | OE4 | OT4.1 | OO5.1.1 | Seguridad e Identidad | P1 | Implementado |
| CU-O02 Gestionar usuarios | OE4 | OT4.1 | OO5.1.1 | Seguridad e Identidad | P2 | Implementado |
| CU-O03 CRUD registros | OE4 | OT4.1 | OO5.2.1 | Operaciones Clínicas | P3 | Implementado |
| CU-O04 Filtrar registros | OE4 | OT4.1 | OO5.2.1 | Operaciones Clínicas | P3 | Implementado |
| CU-O05 Datos sintéticos | OE4 | OT4.1 | OO5.4.1 | Datos e Ingeniería | P4 | Implementado |
| CU-O06 Pipeline ELT | OE4 | OT4.1 | OO5.3.1 | Datos e Ingeniería | P8 | Implementado (DAGs E·T·L + benchmark SQL) |
| CU-O07 Estadísticas clínicas | OE4 | OT4.2 | OO5.5.1 | Operaciones Clínicas | P5 | Implementado |
| CU-O08 Predecir diabetes | OE4 | OT4.2 | OO5.6.1 | Operaciones Clínicas | P6 | Implementado |
| CU-O09 Métricas ML | OE4 | OT4.2 | OO5.6.1 | Datos e Ingeniería | P14 | Implementado |
| CU-O10 Dashboard ejecutivo | OE4 | OT4.2 | OO4.3.3 / alertas TA06 §13 | Operaciones Clínicas | P5 | Implementado |
| — Reportes PDF clínicos | OE4 | OT4.2 | salida analítica | Operaciones Clínicas | P7 | Implementado |
| — Auditoría operaciones | OE4 | OT4.1 | trazabilidad RG-005 | Gobierno y Cumplimiento | P11 | Implementado |
| — Configuración sistema | OE4 | OT4.1 | parámetros DWH | Gobierno y Cumplimiento | P12 | Implementado |
| CU-O11 Lead HubSpot | OE1 | OT1.1 | OO1.1.1 | Crecimiento | P15 | Fuera demo GA07 |
| CU-O12 Pago Stripe | OE1 | OT1.2 | OO1.2.1 | Crecimiento | P15 | Fuera demo GA07 |
| CU-O13 API partner | OE2 | OT2.1 | OO2.1.1 | Crecimiento | P15 | Fuera demo GA07 |
| CU-O14 Doc OpenAPI | OE2 | OT2.1 | OO2.1.2 | Crecimiento | P15 | Parcial (`/docs`) |
| CU-O15 CI/CD | OE3 | OT3.2 | OO3.2.1 | Infraestructura | — | Fuera demo GA07 |
| CU-O16 Alerta churn | OE4 | OT4.2 | OO4.2.1 | Crecimiento | P10 | Parcial (alertas clínicas + correo; churn pendiente) |
| CU-O17 Expediente paciente (HCE) | OE4 | OT4.1 | OO5.2.1 | Operaciones Clínicas | Pacientes | Implementado |
| CU-O18 Agendar cita (admin) | OE4 | OT4.1 | OO5.2.1 | Operaciones Clínicas | Citas | Implementado |
| CU-O19 Registrar admisión | OE4 | OT4.1 | OO5.2.1 | Operaciones Clínicas | Admisiones | Implementado |
| CU-O20 Mis citas (médico) | OE4 | OT4.1 | OO5.2.1 | Operaciones Clínicas | Citas | Implementado |
| — Notificaciones / alertas clínicas | OE4 | OT4.2 | OO4.3.3 | Crecimiento / Clínico | P10 | Implementado (parcial GA07) |
| — Reportes PDF clínicos | OE4 | OT4.2 | salida analítica | Operaciones Clínicas | P7 | Implementado |

---

## 2. Objetivos de referencia (extraídos del TA06)

| Código | Descripción (TA06) |
|--------|-------------------|
| OE1 | Penetración digital y adquisición automatizada (Growth). |
| OE2 | Escalabilidad comercial vía APIs y ecosistemas. |
| OE3 | Infraestructura cloud alta disponibilidad (≥ 99,9% uptime). |
| OE4 | Inteligencia de negocio centralizada (BI + ML clínico). |
| OT4.1 | Data Warehouse unificado modelo Hecho-Dimensión (MinIO/Parquet). |
| OT4.2 | BI, modelos ML clínicos y de negocio. |
| OO5.1.1 | JWT con control de acceso por roles. |
| OO5.2.1 | CRUD registros clínicos con filtros. |
| OO5.3.1 | Pipeline ELT sin intervención manual (600K &lt; 15 min). |
| OO5.4.1 | Datos sintéticos 1K–500K en español. |
| OO5.5.1 | Estadísticas clínicas con Chart.js. |
| OO5.6.1 | Predicción diabetes RandomForest (meta 96% accuracy). |

---

## 3. Historias de usuario — bloque demo GA07

### Seguridad e Identidad

**HU-O01 (CU-O01, P1)** — *Como* usuario, *quiero* iniciar sesión con JWT, *para*
acceder solo a mis módulos. → Implementado.

**HU-O02 (CU-O02, P2)** — *Como* administrador, *quiero* gestionar usuarios y
roles. → Implementado.

### Operaciones Clínicas y datos

**HU-O03–O04 (P3)** — CRUD y filtros (diabetes, género, ubicación, edad). → Implementado.

**HU-O05 (P4)** — Generar datos sintéticos → Parquet MinIO. → Implementado.

**HU-O06 (P8)** — Consultar/ejecutar pipeline ELT. → Implementado.

**HU-O07 (P5)** — Estadísticas clínicas (prevalencia, gráficas). → Implementado.

**HU-O10 (P5)** — Dashboard KPIs y alertas clínicas (TA06 §13). → Implementado.

**HU-O08 (P6)** — Predecir con factores clínicos interpretables. → Implementado.

**HU-O09 (P14)** — Gestionar modelo ML (info, reentrenar, historial). → Implementado.

**HU-O-P10 (P10, CU-O10 / CU-O01)** — Alertas clínicas in-app, correo Brevo (umbrales HbA1c/glucosa),
recuperación de contraseña por email. → Implementado (parcial; CU-O16 churn pendiente).

**HU-O-P10b** — Configurar SMTP/API Brevo en P12. → Implementado.

**HU-O-Pacientes (CU-O17)** — Expediente HCE + foto MinIO. → Implementado.

**HU-O-Agenda (CU-O18)** — Admin agenda citas y asigna médico. → Implementado.

**HU-O-Admisiones (CU-O19)** — Admin registra ingresos y médico tratante. → Implementado.

**HU-O-Mis-citas (CU-O20)** — Médico ve citas asignadas, confirma y atiende. → Implementado.

> Texto listo para Word: `specs/003-operativo/casos-de-uso-correcciones.md`

### Gobierno

**HU-O-P11 (P11)** — Consultar auditoría de accesos y operaciones. → Implementado.

**HU-O-P12 (P12)** — Configurar parámetros del sistema. → Implementado.

---

## 4. Resumen cobertura GA07

| Ámbito | CUs / paquetes |
|--------|----------------|
| **Demo GA07** | CU-O01–O10 + P7, P11, P12, P14 |
| **Implementado** | CU-O01–O10 + **CU-O17–CU-O20** + P7, P11, P12, P14 |
| **Parcial** | CU-O14 (Swagger) |
| **Fuera GA07** | CU-O11, O12, O13, O15; churn CU-O16 (ML negocio); P9, P13, P15 |

**Flujo de datos TA06 demostrable**:

```
Generador (P4) → Pipeline ELT (P8) → Dataset Fact-Dim (P4)
  → Registros/Stats/Dashboard (P3/P5) → Modelo ML (P14) → Predicción (P6)
  → Reportes (P7) → Auditoría (P11)
```
