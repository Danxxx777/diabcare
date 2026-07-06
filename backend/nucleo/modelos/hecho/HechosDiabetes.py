# DiabCare Analytics â€” Tabla de Hecho: HechoDiabetes
# Columnas:
#   encounter_id   : Int64   â€” ID Ãºnico del registro (PK)
#   year           : Int32   â€” AÃ±o del registro
#   age            : float64 â€” Edad del paciente
#   bmi            : float64 â€” Ãndice de masa corporal
#   hbA1c_level    : float64 â€” Hemoglobina glicosilada
#   blood_glucose  : Int32   â€” Glucosa en sangre
#   diabetes       : Int8    â€” DiagnÃ³stico (0=No, 1=SÃ­)
#   hypertension   : Int8    â€” HipertensiÃ³n (0/1)
#   heart_disease  : Int8    â€” Enfermedad cardÃ­aca (0/1)
#   id_paciente    : Int64   â€” FK â†’ DimPaciente
#   id_ubicacion   : Int64   â€” FK â†’ DimUbicacion
#   id_raza        : Int64   â€” FK â†’ DimRaza
#   id_condicion   : Int64   â€” FK â†’ DimCondicion
#   id_tiempo      : Int64   â€” FK â†’ DimTiempo

