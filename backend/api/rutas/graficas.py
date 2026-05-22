"""
graficas.py — Endpoints de visualizaciones analíticas del dataset
"""

from fastapi import APIRouter
from servicios.cliente_minio import get_df
import pandas as pd

enrutador = APIRouter()


@enrutador.get("/api/chart/diabetes-por-anio")
def diabetes_por_anio():
    """Diagnósticos de diabetes agrupados por año."""
    df = get_df()
    agrupado = df.groupby("year")["diabetes"].agg(
        con_diabetes=lambda x: (x == 1).sum(),
        sin_diabetes=lambda x: (x == 0).sum()
    ).reset_index()
    return agrupado.rename(columns={"year": "anio"}).to_dict(orient="records")


@enrutador.get("/api/chart/pacientes-por-ubicacion")
def pacientes_por_ubicacion():
    """Top 15 ubicaciones con más pacientes."""
    df = get_df()
    resultado = df.groupby("location").size().reset_index(name="total")
    resultado = resultado.sort_values("total", ascending=False).head(15)
    return resultado.rename(columns={"location": "ubicacion"}).to_dict(orient="records")


@enrutador.get("/api/chart/distribucion-bmi")
def distribucion_bmi():
    """Distribución de pacientes por rangos de IMC."""
    df = get_df()
    rangos = [0, 18.5, 25, 30, 35, 40, 100]
    etiquetas = ["<18.5", "18.5-25", "25-30", "30-35", "35-40", ">40"]
    df = df.copy()
    df["categoria_bmi"] = pd.cut(df["bmi"], bins=rangos, labels=etiquetas)
    resultado = df.groupby("categoria_bmi", observed=True).size().reset_index(name="total")
    return resultado.rename(columns={"categoria_bmi": "categoria"}).to_dict(orient="records")


@enrutador.get("/api/chart/glucosa-vs-diabetes")
def glucosa_vs_diabetes():
    """Promedio de glucosa en sangre según diagnóstico de diabetes."""
    df = get_df()
    resultado = df.groupby("diabetes")["blood_glucose_level"].mean().reset_index()
    resultado["diabetes"] = resultado["diabetes"].map({0: "Sin diabetes", 1: "Con diabetes"})
    return resultado.rename(columns={"blood_glucose_level": "glucosa_promedio"}).to_dict(orient="records")
@enrutador.get("/api/chart/diabetes")
def chart_diabetes():
    df = get_df()
    return {
        "con_diabetes": int((df["diabetes"] == 1).sum()),
        "sin_diabetes": int((df["diabetes"] == 0).sum())
    }

@enrutador.get("/api/chart/gender")
def chart_gender():
    df = get_df()
    resultado = df.groupby("gender").size().reset_index(name="total")
    return {
        "labels": resultado["gender"].tolist(),
        "values": resultado["total"].tolist()
    }

@enrutador.get("/api/chart/bmi")
def chart_bmi():
    df = get_df()
    resultado = df.groupby("diabetes")["bmi"].mean().reset_index()
    resultado["diabetes"] = resultado["diabetes"].map({0: "Sin diabetes", 1: "Con diabetes"})
    return {
        "labels": resultado["diabetes"].tolist(),
        "values": resultado["bmi"].round(2).tolist()
    }

@enrutador.get("/api/chart/glucose")
def chart_glucose():
    df = get_df()
    resultado = df.groupby("diabetes")["blood_glucose_level"].mean().reset_index()
    resultado["diabetes"] = resultado["diabetes"].map({0: "Sin diabetes", 1: "Con diabetes"})
    return {
        "labels": resultado["diabetes"].tolist(),
        "values": resultado["blood_glucose_level"].round(1).tolist()
    }

@enrutador.get("/api/chart/hba1c")
def chart_hba1c():
    df = get_df()
    rangos = [3, 4, 5, 6, 7, 8, 9, 10]
    etiquetas = ["3-4", "4-5", "5-6", "6-7", "7-8", "8-9", "9-10"]
    df = df.copy()
    df["rango"] = pd.cut(df["hbA1c_level"], bins=rangos, labels=etiquetas)
    resultado = df.groupby("rango", observed=True).size().reset_index(name="total")
    return {
        "labels": resultado["rango"].astype(str).tolist(),
        "values": resultado["total"].tolist()
    }

@enrutador.get("/api/chart/conditions")
def chart_conditions():
    df = get_df()
    resultado = df.groupby("diabetes").agg(
        hipertension=("hypertension", "sum"),
        cardiopatia=("heart_disease", "sum")
    ).reset_index()
    resultado["diabetes"] = resultado["diabetes"].map({0: "Sin diabetes", 1: "Con diabetes"})
    return {
        "labels": resultado["diabetes"].tolist(),
        "hipertension": resultado["hipertension"].tolist(),
        "cardiopatia": resultado["cardiopatia"].tolist()
    }