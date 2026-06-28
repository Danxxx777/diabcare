# Trazabilidad Empresarial — Nivel Operativo

**Creado**: 2026-06-19 · **Actualizado**: 2026-06-20 (GA07)

**Fuentes**:

- **TA06** — *Estrategia Documental Empresarial DiabCare Analytics* (`TA 06.docx`,
  Byron Loor Mendoza): OE, OT, OO, CU-O01–CU-O16, modelo Fact-Dim, pipeline ELT.
- Código verificado: `backend/`, `frontend/`, `specs/`.

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
| CU-O06 Pipeline ELT | OE4 | OT4.1 | OO5.3.1 | Datos e Ingeniería | P8 | Parcial (consulta + UI; DAG Airflow) |
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
| CU-O16 Alerta churn | OE4 | OT4.2 | OO4.2.1 | Crecimiento | P10 | Fuera demo GA07 |

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

**HU-O06 (P8)** — Consultar/ejecutar pipeline ELT. → Parcial.

**HU-O07 (P5)** — Estadísticas clínicas (prevalencia, gráficas). → Implementado.

**HU-O10 (P5)** — Dashboard KPIs y alertas clínicas (TA06 §13). → Implementado.

**HU-O08 (P6)** — Predecir con factores clínicos interpretables. → Implementado.

**HU-O09 (P14)** — Gestionar modelo ML (info, reentrenar, historial). → Implementado.

**HU-O-P07 (P7)** — Generar reportes PDF con agregados (sin IDs paciente). → Implementado.

### Gobierno

**HU-O-P11 (P11)** — Consultar auditoría de accesos y operaciones. → Implementado.

**HU-O-P12 (P12)** — Configurar parámetros del sistema. → Implementado.

---

## 4. Resumen cobertura GA07

| Ámbito | CUs / paquetes |
|--------|----------------|
| **Demo video** | CU-O01–O10 + P7, P11, P12, P14 |
| **Implementado** | 12 capacidades operativas clínicas/datos |
| **Parcial** | CU-O06 (orquestación Airflow completa), CU-O14 (Swagger) |
| **Fuera GA07** | CU-O11, O12, O13, O15, O16; P9, P10, P13, P15 |

**Flujo de datos TA06 demostrable**:

```
Generador (P4) → Pipeline ELT (P8) → Dataset Fact-Dim (P4)
  → Registros/Stats/Dashboard (P3/P5) → Modelo ML (P14) → Predicción (P6)
  → Reportes (P7) → Auditoría (P11)
```
