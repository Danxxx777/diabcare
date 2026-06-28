# Glosario — DiabCare Analytics

**Fuente**: Banco de Abreviaciones del `docs/TA06_DiabCare.pdf` y
`documentacion/EsquemaFactDimensiones.md`. Términos usados de forma transversal
en todas las especificaciones.

## Niveles y objetivos empresariales

| Término | Significado | Descripción |
|---------|-------------|-------------|
| BSC | Balanced Scorecard | Cuadro de Mando Integral: organiza objetivos en 4 perspectivas (financiera, cliente, procesos, aprendizaje). |
| OE | Objetivo Estratégico | Meta de largo plazo (growth digital, APIs, cloud, BI global). |
| OT | Objetivo Táctico | Meta de mediano plazo que descompone un OE por área. |
| OO | Objetivo Operativo | Meta de corto plazo, ejecutada día a día. |
| CU | Caso de Uso | Interacción entre actor y sistema para lograr un objetivo. |
| CU-E | Caso de Uso Estratégico | Nivel gerencial (decisiones de largo plazo). |
| CU-T | Caso de Uso Táctico | Nivel intermedio (planeación y control). |
| CU-O | Caso de Uso Operativo | Ejecución diaria del sistema. |

## Métricas de negocio

| Término | Significado | Descripción |
|---------|-------------|-------------|
| KPI | Key Performance Indicator | Métrica cuantificable de cumplimiento de objetivos. |
| CAC | Customer Acquisition Cost | Costo de adquirir un cliente nuevo. |
| MRR | Monthly Recurring Revenue | Ingresos mensuales recurrentes por suscripciones. |
| ARR | Annual Recurring Revenue | MRR × 12. |
| LTV | Lifetime Value | Ingreso total esperado de un cliente. |
| NPS | Net Promoter Score | % promotores − % detractores. |
| Churn | Tasa de abandono | Clientes que cancelan el servicio. |
| Uptime | Tiempo de disponibilidad | Meta ≥ 99.9%. |
| SLA | Service Level Agreement | Compromiso de disponibilidad con clientes. |

## Tecnología y arquitectura

| Término | Significado | Descripción |
|---------|-------------|-------------|
| SaaS | Software as a Service | Plataforma web por suscripción. |
| API | Application Programming Interface | Endpoints para integración de partners. |
| SDD | Specification-Driven Development | La especificación define el contrato antes de implementar. |
| OpenAPI | Estándar de especificación de APIs REST | Contrato de la API pública. |
| ELT | Extract, Load, Transform | PocketBase → MinIO → pandas. Orquestado por Airflow. |
| `pipeline_etl` | Identificador técnico P8 | Nombre legacy en código; el proceso funcional es ELT. |
| DWH | Data Warehouse | Repositorio centralizado con modelo Hecho-Dimensión. |
| BI | Business Intelligence | Dashboards para decisiones empresariales. |
| ML | Machine Learning | RandomForest para diabetes y churn. |
| MLOps | Machine Learning Operations | Entrenar, desplegar y monitorear modelos ML. |
| JWT | JSON Web Token | Autenticación HS256. |
| CRUD | Create, Read, Update, Delete | Operaciones sobre registros y usuarios. |
| CI/CD | Continuous Integration/Deployment | Despliegues automatizados. |
| CDN | Content Delivery Network | Reduce latencia de contenido. |
| K8s | Kubernetes | Orquestador de contenedores. |
| Fact | Tabla de Hechos | Almacena eventos medibles. |
| Dim | Dimensión | Describe contexto (tiempo, país, paciente). |

## Dominio clínico

| Término | Significado | Descripción |
|---------|-------------|-------------|
| HbA1c | Hemoglobina Glicosilada | Indicador clínico; alerta si promedio > 7.5. |
| BMI | Body Mass Index | Índice de masa corporal; feature del modelo ML. |
| HIS | Hospital Information System | Sistema hospitalario que integra vía API. |
| HIPAA | Ley de protección de datos de salud (EE.UU.) | Cumplimiento normativo. |
| GDPR | Reglamento de protección de datos (UE) | Cumplimiento normativo. |

## Entidades del modelo de datos

| Entidad | Tipo | Descripción |
|---------|------|-------------|
| `HechosDiabetes` | Hecho | Tabla principal (encounter_id, glucosa, BMI, HbA1c, diagnóstico). |
| `DimensionPaciente` | Dimensión | Género, edad. |
| `DimensionUbicacion` | Dimensión | Ubicación geográfica. |
| `DimensionRaza` | Dimensión | Raza/etnia. |
| `DimensionCondicion` | Dimensión | Hipertensión, cardiopatía, tabaquismo. |
| `DimensionTiempo` | Dimensión | Año del registro. |
