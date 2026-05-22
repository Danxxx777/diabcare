"""
procesador_datos.py — Genera tablas de hecho y dimensiones desde el DataFrame
"""

import pandas as pd


def get_dim_paciente(df: pd.DataFrame) -> pd.DataFrame:
    """Dimensión paciente: género y edad únicos."""
    dim = df[["gender", "age"]].drop_duplicates().reset_index(drop=True)
    dim.index.name = "id_paciente"
    return dim.reset_index()


def get_dim_ubicacion(df: pd.DataFrame) -> pd.DataFrame:
    """Dimensión ubicación: localidad y año únicos."""
    dim = df[["location", "year"]].drop_duplicates().reset_index(drop=True)
    dim.index.name = "id_ubicacion"
    return dim.reset_index()


def get_dim_raza(df: pd.DataFrame) -> pd.DataFrame:
    """Dimensión raza: combinaciones únicas de razas."""
    columnas = ["race_AfricanAmerican", "race_Asian", "race_Caucasian", "race_Hispanic", "race_Other"]
    dim = df[columnas].drop_duplicates().reset_index(drop=True)
    dim.index.name = "id_raza"
    return dim.reset_index()


def get_dim_condicion(df: pd.DataFrame) -> pd.DataFrame:
    """Dimensión condición: hipertensión, enf. cardíaca e historial de tabaquismo únicos."""
    columnas = ["hypertension", "heart_disease", "smoking_history"]
    dim = df[columnas].drop_duplicates().reset_index(drop=True)
    dim.index.name = "id_condicion"
    return dim.reset_index()


def get_fact_diabetes(df: pd.DataFrame) -> pd.DataFrame:
    """Tabla de hechos: métricas clínicas y diagnóstico de diabetes."""
    hecho = df[["bmi", "hbA1c_level", "blood_glucose_level", "diabetes"]].copy()
    hecho.index.name = "id_fact"
    return hecho.reset_index()


# Mapa de tablas disponibles
TABLAS_MAP = {
    "diabetes_dataset": lambda df: df,
    "dim_paciente":     get_dim_paciente,
    "dim_ubicacion":    get_dim_ubicacion,
    "dim_raza":         get_dim_raza,
    "dim_condicion":    get_dim_condicion,
    "fact_diabetes":    get_fact_diabetes,
}
