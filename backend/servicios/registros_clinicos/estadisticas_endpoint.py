@router.get("/estadisticas")
def estadisticas():
    from servicios.registros_clinicos.RegistrosClinicosServicio import _extraer
    df = _extraer()
    if df.empty:
        return {"total": 0}

    con = df[df["diabetes"] == 1]
    sin = df[df["diabetes"] == 0]

    # --- Género ---
    genero_counts = df["gender"].value_counts().to_dict()

    # --- Tabaquismo vs diabetes ---
    tabaquismo = {}
    for val in df["smoking_history"].dropna().unique():
        sub = df[df["smoking_history"] == val]
        tabaquismo[val] = {
            "con_diabetes": int((sub["diabetes"] == 1).sum()),
            "sin_diabetes": int((sub["diabetes"] == 0).sum()),
        }

    # --- Raza ---
    razas = ["race_AfricanAmerican", "race_Asian", "race_Caucasian", "race_Hispanic", "race_Other"]
    raza_counts = {}
    for r in razas:
        if r in df.columns:
            raza_counts[r] = {
                "con_diabetes": int(df[df["diabetes"] == 1][r].sum()),
                "sin_diabetes": int(df[df["diabetes"] == 0][r].sum()),
            }

    # --- Edad por rangos ---
    bins   = [0, 20, 30, 40, 50, 60, 70, 200]
    labels = ["<20", "20-30", "31-40", "41-50", "51-60", "61-70", "70+"]
    df["rango_edad"] = pd.cut(df["age"], bins=bins, labels=labels, right=True)
    edad_group = df.groupby(["rango_edad", "diabetes"]).size().unstack(fill_value=0)
    edad_data = {}
    for lbl in labels:
        if lbl in edad_group.index:
            edad_data[lbl] = {
                "sin_diabetes": int(edad_group.loc[lbl].get(0, 0)),
                "con_diabetes": int(edad_group.loc[lbl].get(1, 0)),
            }
        else:
            edad_data[lbl] = {"sin_diabetes": 0, "con_diabetes": 0}

    # --- Promedios clínicos ---
    promedios = {
        "bmi":           {"con": round(float(con["bmi"].mean()), 2) if not con.empty else 0,
                          "sin": round(float(sin["bmi"].mean()), 2) if not sin.empty else 0},
        "hba1c":         {"con": round(float(con["hbA1c_level"].mean()), 2) if not con.empty else 0,
                          "sin": round(float(sin["hbA1c_level"].mean()), 2) if not sin.empty else 0},
        "glucosa":       {"con": round(float(con["blood_glucose_level"].mean()), 1) if not con.empty else 0,
                          "sin": round(float(sin["blood_glucose_level"].mean()), 1) if not sin.empty else 0},
    }

    # --- Hipertensión y cardiopatía reales ---
    comorbilidades = {
        "hipertension": {
            "con_diabetes_con": int(df[(df["diabetes"]==1) & (df["hypertension"]==1)].shape[0]),
            "con_diabetes_sin": int(df[(df["diabetes"]==1) & (df["hypertension"]==0)].shape[0]),
            "sin_diabetes_con": int(df[(df["diabetes"]==0) & (df["hypertension"]==1)].shape[0]),
            "sin_diabetes_sin": int(df[(df["diabetes"]==0) & (df["hypertension"]==0)].shape[0]),
        },
        "cardiopatia": {
            "con_diabetes_con": int(df[(df["diabetes"]==1) & (df["heart_disease"]==1)].shape[0]),
            "con_diabetes_sin": int(df[(df["diabetes"]==1) & (df["heart_disease"]==0)].shape[0]),
            "sin_diabetes_con": int(df[(df["diabetes"]==0) & (df["heart_disease"]==1)].shape[0]),
            "sin_diabetes_sin": int(df[(df["diabetes"]==0) & (df["heart_disease"]==0)].shape[0]),
        },
    }

    # --- Top ubicaciones ---
    top_ubicaciones = df["location"].value_counts().head(10).to_dict()

    # --- Tendencia por año ---
    if "year" in df.columns:
        tendencia = df.groupby("year")["diabetes"].agg(
            total="count",
            con_diabetes=lambda x: (x == 1).sum()
        ).reset_index()
        tendencia_data = [
            {"year": int(row["year"]), "total": int(row["total"]), "con_diabetes": int(row["con_diabetes"])}
            for _, row in tendencia.iterrows()
        ]
    else:
        tendencia_data = []

    return {
        "total":          len(df),
        "con_diabetes":   int((df["diabetes"] == 1).sum()),
        "sin_diabetes":   int((df["diabetes"] == 0).sum()),
        "genero":         genero_counts,
        "tabaquismo":     tabaquismo,
        "razas":          raza_counts,
        "edad":           edad_data,
        "promedios":      promedios,
        "comorbilidades": comorbilidades,
        "ubicaciones":    top_ubicaciones,
        "tendencia":      tendencia_data,
    }