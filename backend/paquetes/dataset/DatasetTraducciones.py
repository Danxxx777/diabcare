"""Traducción y normalización de valores del dataset clínico (ES)."""

GENERO_CANON = {
    "Masculino": ["Masculino", "Male", "male", "M", "masculino"],
    "Femenino": ["Femenino", "Female", "female", "F", "femenino"],
    "Otro": ["Otro", "Other", "other", "otro"],
}

TABACO_MAP = {
    "never": "nunca",
    "Never": "nunca",
    "no": "nunca",
    "No Info": "Sin información",
    "No info": "Sin información",
    "not current": "no actual",
    "Not current": "no actual",
    "current": "actual",
    "Current": "actual",
    "ever": "anterior",
    "Former": "anterior",
    "former": "anterior",
}

RAZA_ES = {
    "race_AfricanAmerican": "Afroamericano",
    "race_Asian": "Asiático",
    "race_Caucasian": "Caucásico",
    "race_Hispanic": "Hispano",
    "race_Other": "Otro",
    "AfricanAmerican": "Afroamericano",
    "Asian": "Asiático",
    "Caucasian": "Caucásico",
    "Hispanic": "Hispano",
    "Other": "Otro",
}


def normalizar_genero(val) -> str:
    if val is None or (isinstance(val, float) and str(val) == "nan"):
        return "—"
    v = str(val).strip()
    for canon, aliases in GENERO_CANON.items():
        if v in aliases or v.lower() == canon.lower():
            return canon
    return v


def aliases_genero(genero: str) -> list:
    for canon, aliases in GENERO_CANON.items():
        if genero == canon or genero in aliases:
            return list(set(aliases + [canon]))
    return [genero]


def normalizar_tabaco(val) -> str:
    if val is None or (isinstance(val, float) and str(val) == "nan"):
        return "Sin información"
    v = str(val).strip()
    return TABACO_MAP.get(v, v)


def normalizar_raza(clave: str) -> str:
    return RAZA_ES.get(clave, clave.replace("race_", "").replace("_", " "))


def traducir_registro(reg: dict) -> dict:
    out = dict(reg)
    if "gender" in out:
        out["gender"] = normalizar_genero(out["gender"])
    if "smoking_history" in out:
        out["smoking_history"] = normalizar_tabaco(out["smoking_history"])
    return out
