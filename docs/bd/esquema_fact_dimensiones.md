# Esquema de Base de Datos — DiabCare Analytics
# Almacenamiento: MinIO (formato Parquet columnar)

## fact_diabetes
| Campo               | Tipo    | Descripción                    |
|---------------------|---------|--------------------------------|
| encounter_id        | Int64   | ID único del registro (PK)     |
| year                | Int32   | Año del registro               |
| age                 | float64 | Edad del paciente              |
| bmi                 | float64 | Índice de masa corporal        |
| hbA1c_level         | float64 | Hemoglobina glicosilada        |
| blood_glucose_level | Int32   | Glucosa en sangre              |
| diabetes            | Int8    | Diagnóstico (0=No, 1=Sí)      |
| hypertension        | Int8    | Hipertensión (0/1)             |
| heart_disease       | Int8    | Enfermedad cardíaca (0/1)      |
| id_paciente         | Int64   | FK → dim_paciente              |
| id_ubicacion        | Int64   | FK → dim_ubicacion             |
| id_raza             | Int64   | FK → dim_raza                  |
| id_condicion        | Int64   | FK → dim_condicion             |
| id_tiempo           | Int64   | FK → dim_tiempo                |

## dim_paciente
| Campo      | Tipo    | Descripción  |
|------------|---------|--------------|
| id_paciente| Int64   | PK           |
| gender     | string  | Género       |
| age        | float64 | Edad         |

## dim_ubicacion
| Campo       | Tipo   | Descripción          |
|-------------|--------|----------------------|
| id_ubicacion| Int64  | PK                   |
| location    | string | Ubicación geográfica |

## dim_raza
| Campo               | Tipo   | Descripción |
|---------------------|--------|-------------|
| id_raza             | Int64  | PK          |
| race_AfricanAmerican| Int8   | (0/1)       |
| race_Asian          | Int8   | (0/1)       |
| race_Caucasian      | Int8   | (0/1)       |
| race_Hispanic       | Int8   | (0/1)       |
| race_Other          | Int8   | (0/1)       |

## dim_condicion
| Campo           | Tipo   | Descripción          |
|-----------------|--------|----------------------|
| id_condicion    | Int64  | PK                   |
| hypertension    | Int8   | (0/1)                |
| heart_disease   | Int8   | (0/1)                |
| smoking_history | string | Historial tabaquismo |

## dim_tiempo
| Campo    | Tipo  | Descripción |
|----------|-------|-------------|
| id_tiempo| Int64 | PK          |
| year     | Int32 | Año         |
