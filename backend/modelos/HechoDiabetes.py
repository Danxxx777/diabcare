# DiabCare Analytics — Tabla de Hecho: HechoDiabetes
# Columnas:
#   encounter_id   : Int64   — ID único del registro (PK)
#   year           : Int32   — Año del registro
#   age            : float64 — Edad del paciente
#   bmi            : float64 — Índice de masa corporal
#   hbA1c_level    : float64 — Hemoglobina glicosilada
#   blood_glucose  : Int32   — Glucosa en sangre
#   diabetes       : Int8    — Diagnóstico (0=No, 1=Sí)
#   hypertension   : Int8    — Hipertensión (0/1)
#   heart_disease  : Int8    — Enfermedad cardíaca (0/1)
#   id_paciente    : Int64   — FK → DimPaciente
#   id_ubicacion   : Int64   — FK → DimUbicacion
#   id_raza        : Int64   — FK → DimRaza
#   id_condicion   : Int64   — FK → DimCondicion
#   id_tiempo      : Int64   — FK → DimTiempo
