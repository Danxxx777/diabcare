"""
Catálogo del DWH clínico-hospitalario DiabCare (GA07).

Estado por tabla:
  - implementado: materializado desde stage/ o operativo en demo
  - derivado:     calculado en ELT desde hechos base
  - esquema:      definido; servicios clínicos hospitalarios (fase 2)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TablaDwh:
    id: str
    nombre: str
    grupo: str  # hechos | dimensiones | agregados | puente | operativo | gobierno
    path: str
    descripcion: str
    cu_o: tuple[str, ...]
    oo: tuple[str, ...]
    paquete: str
    estado: str  # implementado | derivado | esquema
    columnas: tuple[str, ...]


# ── HECHOS ─────────────────────────────────────────────────────────────────────
TABLAS: list[TablaDwh] = [
    TablaDwh(
        "hechos_diabetes", "Hechos diabetes", "hechos",
        "hechos/hechos_diabetes.parquet",
        "Encuentro clínico con métricas metabólicas y FKs al star schema.",
        ("CU-O03", "CU-O04", "CU-O07"), ("OO5.2.1", "OO5.5.1"), "P3", "implementado",
        ("encounter_id", "year", "age", "bmi", "hbA1c_level", "blood_glucose_level",
         "diabetes", "hypertension", "heart_disease",
         "id_paciente", "id_ubicacion", "id_raza", "id_condicion", "id_tiempo"),
    ),
    TablaDwh(
        "hechos_consulta", "Hechos consulta", "hechos",
        "hechos/hechos_consulta.parquet",
        "Vista clínica del encuentro: flags de riesgo y clasificación metabólica.",
        ("CU-O03", "CU-O07"), ("OO5.2.1",), "P3", "derivado",
        ("encounter_id", "id_paciente", "id_hospital", "id_edad_grupo",
         "clasificacion_hba1c", "clasificacion_glucosa", "nivel_riesgo", "diabetes"),
    ),
    TablaDwh(
        "hechos_prediccion", "Hechos predicción ML", "hechos",
        "hechos/hechos_prediccion.parquet",
        "Registro de inferencias del modelo (auditoría clínica ML).",
        ("CU-O08", "CU-O09"), ("OO5.6.1",), "P6", "derivado",
        ("id_prediccion", "encounter_id", "probabilidad", "diagnostico_estimado",
         "modelo_version", "fecha_prediccion", "id_medico"),
    ),
    TablaDwh(
        "hechos_alertas", "Hechos alertas clínicas", "hechos",
        "hechos/hechos_alertas.parquet",
        "Alertas generadas por umbrales clínicos (RN-O-005).",
        ("CU-O10", "CU-O16"), ("OO4.3.3",), "P10", "derivado",
        ("id_alerta", "tipo", "titulo", "severidad", "valor_medido", "umbral", "fecha"),
    ),

    # ── DIMENSIONES CORE (GA07) ───────────────────────────────────────────────
    TablaDwh(
        "dim_paciente", "Dim. paciente", "dimensiones",
        "dimensiones/dim_paciente.parquet", "Paciente anonimizado (edad, género).",
        ("CU-O03", "CU-O05"), ("OO5.2.1", "OO5.4.1"), "P4", "implementado",
        ("id_paciente", "gender", "age"),
    ),
    TablaDwh(
        "dim_ubicacion", "Dim. ubicación", "dimensiones",
        "dimensiones/dim_ubicacion.parquet", "Ubicación geográfica / sede.",
        ("CU-O04", "CU-O07"), ("OO5.2.1",), "P4", "implementado",
        ("id_ubicacion", "location"),
    ),
    TablaDwh(
        "dim_raza", "Dim. raza", "dimensiones",
        "dimensiones/dim_raza.parquet", "Etnia (one-hot clínico).",
        ("CU-O07",), ("OO5.5.1",), "P4", "implementado",
        ("id_raza", "race_AfricanAmerican", "race_Asian", "race_Caucasian",
         "race_Hispanic", "race_Other"),
    ),
    TablaDwh(
        "dim_condicion", "Dim. condición", "dimensiones",
        "dimensiones/dim_condicion.parquet", "Comorbilidades y tabaquismo.",
        ("CU-O03", "CU-O07"), ("OO5.2.1",), "P4", "implementado",
        ("id_condicion", "hypertension", "heart_disease", "smoking_history"),
    ),
    TablaDwh(
        "dim_tiempo", "Dim. tiempo", "dimensiones",
        "dimensiones/dim_tiempo.parquet", "Periodo temporal (año).",
        ("CU-O07", "CU-O06"), ("OO5.5.1",), "P4", "implementado",
        ("id_tiempo", "year"),
    ),

    # ── DIMENSIONES EXTENDIDAS (clínica / hospital) ───────────────────────────
    TablaDwh(
        "dim_hospital", "Dim. hospital / sede", "dimensiones",
        "dimensiones/dim_hospital.parquet",
        "Sede hospitalaria derivada de ubicación geográfica.",
        ("CU-O07",), ("OO5.5.1",), "P9", "derivado",
        ("id_hospital", "nombre", "ubicacion", "region"),
    ),
    TablaDwh(
        "dim_edad_grupo", "Dim. grupo etario", "dimensiones",
        "dimensiones/dim_edad_grupo.parquet", "Bandas de edad para análisis epidemiológico.",
        ("CU-O04", "CU-O07"), ("OO5.2.1", "OO5.5.1"), "P5", "derivado",
        ("id_edad_grupo", "rango", "edad_min", "edad_max"),
    ),
    TablaDwh(
        "dim_genero", "Dim. género", "dimensiones",
        "dimensiones/dim_genero.parquet", "Catálogo de género normalizado.",
        ("CU-O04",), ("OO5.2.1",), "P4", "derivado",
        ("id_genero", "genero"),
    ),
    TablaDwh(
        "dim_tabaquismo", "Dim. tabaquismo", "dimensiones",
        "dimensiones/dim_tabaquismo.parquet", "Historial de tabaquismo.",
        ("CU-O07",), ("OO5.5.1",), "P4", "derivado",
        ("id_tabaco", "smoking_history"),
    ),
    TablaDwh(
        "dim_riesgo_metabolico", "Dim. riesgo metabólico", "dimensiones",
        "dimensiones/dim_riesgo_metabolico.parquet",
        "Estratificación por BMI, HbA1c y glucosa.",
        ("CU-O08", "CU-O10"), ("OO5.6.1",), "P6", "derivado",
        ("id_riesgo", "nivel", "bmi_rango", "hba1c_rango", "glucosa_rango"),
    ),
    TablaDwh(
        "dim_diagnostico", "Dim. diagnóstico diabetes", "dimensiones",
        "dimensiones/dim_diagnostico.parquet",
        "Clasificación clínica: sin diabetes, prediabetes, diabetes.",
        ("CU-O08", "CU-O07"), ("OO5.6.1",), "P6", "derivado",
        ("id_diagnostico", "codigo", "descripcion"),
    ),
    TablaDwh(
        "dim_comorbilidad", "Dim. comorbilidad", "dimensiones",
        "dimensiones/dim_comorbilidad.parquet",
        "Combinación hipertensión + cardiopatía.",
        ("CU-O07",), ("OO5.5.1",), "P5", "derivado",
        ("id_comorbilidad", "hypertension", "heart_disease", "etiqueta"),
    ),
    TablaDwh(
        "dim_medico", "Dim. médico", "dimensiones",
        "dimensiones/dim_medico.parquet",
        "Profesional de salud (usuarios rol médico).",
        ("CU-O02", "CU-O03"), ("OO5.1.1", "OO5.2.1"), "P2", "derivado",
        ("id_medico", "nombre", "especialidad", "correo"),
    ),
    TablaDwh(
        "dim_servicio", "Dim. servicio clínico", "dimensiones",
        "dimensiones/dim_servicio.parquet",
        "Servicio hospitalario (Endocrinología, Medicina interna…).",
        ("CU-O03",), ("OO5.2.1",), "P3", "esquema",
        ("id_servicio", "nombre", "tipo"),
    ),

    # ── AGREGADOS ANALÍTICOS ──────────────────────────────────────────────────
    TablaDwh(
        "agg_prevalencia_ubicacion", "Agg. prevalencia por ubicación", "agregados",
        "agregados/agg_prevalencia_ubicacion.parquet",
        "Prevalencia de diabetes por sede geográfica.",
        ("CU-O07", "CU-O10"), ("OO5.5.1",), "P5", "derivado",
        ("id_ubicacion", "location", "total", "con_diabetes", "prevalencia_pct"),
    ),
    TablaDwh(
        "agg_prevalencia_edad", "Agg. prevalencia por edad", "agregados",
        "agregados/agg_prevalencia_edad.parquet",
        "Prevalencia por grupo etario.",
        ("CU-O07",), ("OO5.5.1",), "P5", "derivado",
        ("id_edad_grupo", "rango", "total", "con_diabetes", "prevalencia_pct"),
    ),
    TablaDwh(
        "agg_promedios_clinicos", "Agg. promedios clínicos", "agregados",
        "agregados/agg_promedios_clinicos.parquet",
        "BMI, HbA1c y glucosa promedio por cohorte diabetes.",
        ("CU-O07", "CU-O10"), ("OO5.5.1",), "P5", "derivado",
        ("cohorte", "total", "bmi_prom", "hba1c_prom", "glucosa_prom"),
    ),
    TablaDwh(
        "agg_cohorte_riesgo", "Agg. cohorte por riesgo", "agregados",
        "agregados/agg_cohorte_riesgo.parquet",
        "Distribución de pacientes por nivel de riesgo metabólico.",
        ("CU-O08", "CU-O10"), ("OO5.6.1",), "P6", "derivado",
        ("nivel_riesgo", "total", "pct_diabetes"),
    ),

    # ── PUENTES ───────────────────────────────────────────────────────────────
    TablaDwh(
        "bridge_paciente_comorbilidad", "Bridge paciente-comorbilidad", "puente",
        "puentes/bridge_paciente_comorbilidad.parquet",
        "Relación N:M paciente ↔ comorbilidades.",
        ("CU-O07",), ("OO5.5.1",), "P5", "derivado",
        ("id_paciente", "id_comorbilidad", "frecuencia"),
    ),

    # ── GOBIERNO / OPERATIVO ──────────────────────────────────────────────────
    TablaDwh(
        "cat_fuentes", "Cat. fuentes de datos", "operativo",
        "catalogo/cat_fuentes.parquet",
        "Origen de registros: generador, PocketBase, manual, pipeline.",
        ("CU-O05", "CU-O06"), ("OO5.3.1", "OO5.4.1"), "P8", "derivado",
        ("id_fuente", "nombre", "descripcion"),
    ),
    TablaDwh(
        "cat_casos_uso", "Cat. trazabilidad CU-O", "operativo",
        "catalogo/cat_casos_uso.parquet",
        "Mapa CU-O → OO → paquete para la app hospitalaria.",
        ("CU-O01",), ("OO5.1.1",), "P1", "derivado",
        ("cu_o", "oo", "paquete", "modulo_ui", "estado"),
    ),
    TablaDwh(
        "oper_fotos_entidad", "Fotos de personas", "operativo",
        "operativo/fotos_entidad.parquet",
        "Metadatos de fotos de pacientes, médicos, usuarios y contactos (binarios en MinIO).",
        ("CU-O03", "CU-O02"), ("OO5.2.1", "OO5.1.1"), "P3", "implementado",
        ("id_foto", "tipo_entidad", "id_entidad", "nombre_archivo", "mime_type",
         "ruta_minio", "es_principal", "subido_en", "subido_por"),
    ),
    TablaDwh(
        "oper_citas", "Agenda clínica", "operativo",
        "operativo/citas.parquet",
        "Citas programadas, estados de consulta y seguimiento.",
        ("CU-O03",), ("OO5.2.1",), "P3", "implementado",
        ("id_cita", "id_paciente", "paciente_nombre", "medico", "fecha", "hora",
         "estado", "motivo", "sede", "notas", "proximo_control", "creado_en", "actualizado_en"),
    ),
    TablaDwh(
        "oper_admisiones", "Admisiones hospitalarias", "operativo",
        "operativo/admisiones.parquet",
        "Ingresos ambulatorios, urgencia u hospitalización.",
        ("CU-O03",), ("OO5.2.1",), "Admisiones", "implementado",
        ("id_admision", "id_paciente", "paciente_nombre", "documento", "tipo", "servicio",
         "medico_id", "medico_nombre", "sede", "habitacion", "estado", "motivo",
         "fecha_ingreso", "fecha_egreso", "notas", "creado_en", "actualizado_en"),
    ),

    # ── HECHOS HOSPITALARIOS (esquema Fase 2) ─────────────────────────────────
    TablaDwh(
        "hechos_admision", "Hechos admisión", "hechos",
        "hechos/hechos_admision.parquet", "Eventos de ingreso hospitalario.",
        ("CU-O03",), ("OO5.2.1",), "Admisiones", "esquema",
        ("id_admision", "id_paciente", "id_servicio", "id_hospital", "tipo", "fecha_ingreso"),
    ),
    TablaDwh(
        "hechos_signos_vitales", "Hechos signos vitales", "hechos",
        "hechos/hechos_signos_vitales.parquet", "TA, FC, FR, temperatura, SpO2.",
        ("CU-O03",), ("OO5.2.1",), "P3", "esquema",
        ("id_registro", "id_paciente", "fecha", "presion_sistolica", "presion_diastolica", "frecuencia_cardiaca", "temperatura"),
    ),
    TablaDwh(
        "hechos_laboratorio", "Hechos laboratorio", "hechos",
        "hechos/hechos_laboratorio.parquet", "Resultados de pruebas clínicas.",
        ("CU-O03",), ("OO5.2.1",), "Laboratorio", "esquema",
        ("id_orden", "id_paciente", "id_prueba", "valor", "unidad", "fecha_resultado", "flag_alerta"),
    ),
    TablaDwh(
        "hechos_procedimiento", "Hechos procedimiento", "hechos",
        "hechos/hechos_procedimiento.parquet", "Procedimientos y cirugías.",
        ("CU-O03",), ("OO5.2.1",), "Quirófano", "esquema",
        ("id_procedimiento", "id_paciente", "codigo_cie10", "descripcion", "fecha", "id_medico"),
    ),
    TablaDwh(
        "hechos_hospitalizacion", "Hechos hospitalización", "hechos",
        "hechos/hechos_hospitalizacion.parquet", "Estadía en cama hospitalaria.",
        ("CU-O03",), ("OO5.2.1",), "Hospitalización", "esquema",
        ("id_estadia", "id_paciente", "id_habitacion", "fecha_ingreso", "fecha_egreso", "dias_estadia"),
    ),
    TablaDwh(
        "hechos_emergencia", "Hechos urgencias", "hechos",
        "hechos/hechos_emergencia.parquet", "Atenciones en servicio de urgencias.",
        ("CU-O03",), ("OO5.2.1",), "Urgencias", "esquema",
        ("id_urgencia", "id_paciente", "triage_nivel", "hora_llegada", "hora_atencion", "derivacion"),
    ),
    TablaDwh(
        "hechos_tratamiento_insulina", "Hechos tratamiento insulina", "hechos",
        "hechos/hechos_tratamiento_insulina.parquet", "Esquemas insulinoterapia diabetes.",
        ("CU-O08",), ("OO5.6.1",), "P6", "esquema",
        ("id_tratamiento", "id_paciente", "tipo_insulina", "dosis", "frecuencia", "fecha_inicio"),
    ),
    TablaDwh(
        "hechos_facturacion", "Hechos facturación", "hechos",
        "hechos/hechos_facturacion.parquet", "Cargos y facturas por atención.",
        ("CU-O03",), ("OO5.2.1",), "Facturación", "esquema",
        ("id_factura", "id_paciente", "id_admision", "monto", "moneda", "estado_pago", "fecha"),
    ),
    TablaDwh(
        "hechos_farmacia_dispensacion", "Hechos dispensación farmacia", "hechos",
        "hechos/hechos_farmacia_dispensacion.parquet", "Entrega de medicamentos.",
        ("CU-O03",), ("OO5.2.1",), "Farmacia", "esquema",
        ("id_dispensacion", "id_paciente", "id_medicamento", "cantidad", "lote", "fecha"),
    ),

    # ── DIMENSIONES HOSPITALARIAS ─────────────────────────────────────────────
    TablaDwh(
        "dim_especialidad", "Dim. especialidad médica", "dimensiones",
        "dimensiones/dim_especialidad.parquet", "Especialidades clínicas.",
        ("CU-O03",), ("OO5.2.1",), "P3", "esquema",
        ("id_especialidad", "nombre", "servicio"),
    ),
    TablaDwh(
        "dim_departamento_hospital", "Dim. departamento", "dimensiones",
        "dimensiones/dim_departamento_hospital.parquet", "Departamentos administrativos.",
        ("CU-O07",), ("OO5.5.1",), "P9", "esquema",
        ("id_departamento", "nombre", "tipo"),
    ),
    TablaDwh(
        "dim_cie10", "Dim. CIE-10", "dimensiones",
        "dimensiones/dim_cie10.parquet", "Diagnósticos y procedimientos CIE-10.",
        ("CU-O03",), ("OO5.2.1",), "P3", "esquema",
        ("codigo_cie10", "descripcion", "capitulo"),
    ),
    TablaDwh(
        "dim_medicamento", "Dim. medicamento", "dimensiones",
        "dimensiones/dim_medicamento.parquet", "Catálogo farmacéutico.",
        ("CU-O03",), ("OO5.2.1",), "Farmacia", "esquema",
        ("id_medicamento", "nombre", "principio_activo", "via", "controlado"),
    ),
    TablaDwh(
        "dim_laboratorio_prueba", "Dim. prueba laboratorio", "dimensiones",
        "dimensiones/dim_laboratorio_prueba.parquet", "Pruebas de laboratorio.",
        ("CU-O03",), ("OO5.2.1",), "Laboratorio", "esquema",
        ("id_prueba", "nombre", "unidad", "rango_min", "rango_max"),
    ),
    TablaDwh(
        "dim_seguro", "Dim. aseguradora", "dimensiones",
        "dimensiones/dim_seguro.parquet", "Planes y EPS.",
        ("CU-O03",), ("OO5.2.1",), "Facturación", "esquema",
        ("id_seguro", "nombre", "tipo_plan"),
    ),
    TablaDwh(
        "dim_proveedor", "Dim. proveedor", "dimensiones",
        "dimensiones/dim_proveedor.parquet", "Proveedores de insumos.",
        ("CU-O03",), ("OO5.2.1",), "Inventario", "esquema",
        ("id_proveedor", "nombre", "contacto"),
    ),
    TablaDwh(
        "dim_habitacion", "Dim. habitación / cama", "dimensiones",
        "dimensiones/dim_habitacion.parquet", "Camas hospitalarias.",
        ("CU-O03",), ("OO5.2.1",), "Hospitalización", "esquema",
        ("id_habitacion", "piso", "numero", "tipo", "estado"),
    ),
    TablaDwh(
        "dim_equipo_medico", "Dim. equipo médico", "dimensiones",
        "dimensiones/dim_equipo_medico.parquet", "Equipos biomédicos.",
        ("CU-O03",), ("OO5.2.1",), "Inventario", "esquema",
        ("id_equipo", "nombre", "ubicacion", "estado_mantenimiento"),
    ),
    TablaDwh(
        "dim_dieta", "Dim. dieta clínica", "dimensiones",
        "dimensiones/dim_dieta.parquet", "Dietas hospitalarias.",
        ("CU-O03",), ("OO5.2.1",), "Hospitalización", "esquema",
        ("id_dieta", "nombre", "restricciones"),
    ),

    # ── AGREGADOS HOSPITALARIOS ───────────────────────────────────────────────
    TablaDwh(
        "agg_ocupacion_camas", "Agg. ocupación camas", "agregados",
        "agregados/agg_ocupacion_camas.parquet", "Ocupación por piso/servicio.",
        ("CU-O10",), ("OO5.5.1",), "Hospitalización", "esquema",
        ("fecha", "id_hospital", "camas_totales", "camas_ocupadas", "pct_ocupacion"),
    ),
    TablaDwh(
        "agg_productividad_medica", "Agg. productividad médica", "agregados",
        "agregados/agg_productividad_medica.parquet", "Consultas por médico/periodo.",
        ("CU-O07",), ("OO5.5.1",), "P5", "esquema",
        ("id_medico", "periodo", "consultas", "pacientes_unicos"),
    ),
    TablaDwh(
        "agg_costo_servicio", "Agg. costo por servicio", "agregados",
        "agregados/agg_costo_servicio.parquet", "Costos promedio por servicio.",
        ("CU-O10",), ("OO5.5.1",), "Facturación", "esquema",
        ("id_servicio", "periodo", "costo_promedio", "atenciones"),
    ),
    TablaDwh(
        "agg_tiempos_espera", "Agg. tiempos de espera", "agregados",
        "agregados/agg_tiempos_espera.parquet", "Espera urgencias y consulta.",
        ("CU-O07",), ("OO5.5.1",), "Urgencias", "esquema",
        ("servicio", "periodo", "espera_prom_min", "atenciones"),
    ),
    TablaDwh(
        "agg_medicamentos_top", "Agg. medicamentos más dispensados", "agregados",
        "agregados/agg_medicamentos_top.parquet", "Ranking farmacia.",
        ("CU-O07",), ("OO5.5.1",), "Farmacia", "esquema",
        ("id_medicamento", "nombre", "total_dispensaciones", "periodo"),
    ),

    # ── PUENTES ADICIONALES ───────────────────────────────────────────────────
    TablaDwh(
        "bridge_medico_servicio", "Bridge médico-servicio", "puente",
        "puentes/bridge_medico_servicio.parquet", "Asignación médico ↔ servicio.",
        ("CU-O02", "CU-O03"), ("OO5.1.1", "OO5.2.1"), "P2", "esquema",
        ("id_medico", "id_servicio", "fecha_desde", "fecha_hasta"),
    ),
    TablaDwh(
        "bridge_paciente_seguro", "Bridge paciente-seguro", "puente",
        "puentes/bridge_paciente_seguro.parquet", "Cobertura del paciente.",
        ("CU-O03",), ("OO5.2.1",), "Facturación", "esquema",
        ("id_paciente", "id_seguro", "numero_poliza", "vigencia_hasta"),
    ),
    TablaDwh(
        "bridge_tratamiento_medicamento", "Bridge tratamiento-medicamento", "puente",
        "puentes/bridge_tratamiento_medicamento.parquet", "Medicamentos por plan terapéutico.",
        ("CU-O08",), ("OO5.6.1",), "Farmacia", "esquema",
        ("id_tratamiento", "id_medicamento", "dosis", "frecuencia"),
    ),

    # ── OPERATIVO ADICIONAL ───────────────────────────────────────────────────
    TablaDwh(
        "oper_inventario", "Inventario insumos", "operativo",
        "operativo/inventario.parquet", "Stock de almacén hospitalario.",
        ("CU-O03",), ("OO5.2.1",), "Inventario", "esquema",
        ("id_item", "nombre", "categoria", "stock", "unidad", "punto_reorden"),
    ),
    TablaDwh(
        "oper_recetas", "Recetas médicas", "operativo",
        "operativo/recetas.parquet", "Prescripciones pendientes de farmacia.",
        ("CU-O03",), ("OO5.2.1",), "Farmacia", "esquema",
        ("id_receta", "id_paciente", "id_medico", "medicamentos_json", "estado", "fecha"),
    ),
    TablaDwh(
        "oper_ordenes_lab", "Órdenes laboratorio", "operativo",
        "operativo/ordenes_lab.parquet", "Solicitudes de laboratorio.",
        ("CU-O03",), ("OO5.2.1",), "Laboratorio", "esquema",
        ("id_orden", "id_paciente", "id_prueba", "estado", "fecha_solicitud"),
    ),
    TablaDwh(
        "oper_auditoria_eventos", "Eventos auditoría", "operativo",
        "operativo/auditoria.parquet", "Trazabilidad de acciones.",
        ("CU-O01",), ("OO5.1.1",), "P11", "implementado",
        ("id", "usuario", "tipo", "modulo", "detalle", "fecha"),
    ),
]

TABLA_POR_ID = {t.id: t for t in TABLAS}


def listar_por_grupo() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for t in TABLAS:
        out.setdefault(t.grupo, []).append({
            "id": t.id,
            "nombre": t.nombre,
            "path": t.path,
            "descripcion": t.descripcion,
            "cu_o": list(t.cu_o),
            "oo": list(t.oo),
            "paquete": t.paquete,
            "estado_esquema": t.estado,
            "columnas": list(t.columnas),
        })
    return out
