"""Lookup rápido de pacientes para enriquecer listados (sin N+1 de fotos binarias)."""
from __future__ import annotations


def mapa_pacientes(ids: set[str] | None = None) -> dict[str, dict]:
    """
    Devuelve {id_paciente: {nombre_completo, documento, tiene_foto}}.
    Si `ids` viene, solo carga esos (mucho más rápido en listados).
    """
    try:
        from paquetes.clinico.pacientes.PacientesServicio import _extraer, _ids_con_foto_paciente
        df = _extraer()
        if df.empty:
            return {}
        df = df.copy()
        df["id_paciente"] = df["id_paciente"].astype(str)
        if ids is not None:
            ids_norm = {str(i) for i in ids if i}
            if not ids_norm:
                return {}
            df = df[df["id_paciente"].isin(ids_norm)]
        if df.empty:
            return {}
        if "nombre" not in df.columns:
            df["nombre"] = ""
        if "apellido" not in df.columns:
            df["apellido"] = ""
        if "documento" not in df.columns:
            df["documento"] = ""
        df["nombre"] = df["nombre"].fillna("").astype(str)
        df["apellido"] = df["apellido"].fillna("").astype(str)
        df["documento"] = df["documento"].fillna("").astype(str)
        fotos = _ids_con_foto_paciente()
        out: dict[str, dict] = {}
        for pid, nom, ape, doc in zip(
            df["id_paciente"].tolist(),
            df["nombre"].tolist(),
            df["apellido"].tolist(),
            df["documento"].tolist(),
        ):
            pid_s = str(pid)
            out[pid_s] = {
                "nombre_completo": f"{nom.strip()} {ape.strip()}".strip(),
                "documento": str(doc).strip(),
                "tiene_foto": pid_s in fotos,
            }
        return out
    except Exception:
        return {}
