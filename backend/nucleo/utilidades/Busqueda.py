# -*- coding: utf-8 -*-
"""Búsqueda rankeada reutilizable (prefijo > contiene > tokens)."""
from __future__ import annotations

import pandas as pd


def rankear_dataframe(df: pd.DataFrame, q: str, campos: list[str] | None = None) -> pd.DataFrame:
    """
    Filtra y ordena por similitud.
    Prefijos suman más; tokens (palabras) permiten 'sof tor' ~ 'Sofía Torres'.
    """
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()
    ql = str(q or "").strip().lower()
    if not ql:
        return df

    cols = [c for c in (campos or list(df.columns)) if c in df.columns]
    if not cols:
        return df.iloc[0:0]

    score = pd.Series(0, index=df.index, dtype=int)
    series = {c: df[c].astype(str).str.lower() for c in cols}

    for c, s in series.items():
        score = score + s.str.startswith(ql).astype(int) * 100
        score = score + s.str.contains(ql, na=False, regex=False).astype(int) * 50

    for tok in [t for t in ql.replace(",", " ").split() if len(t) >= 2]:
        for s in series.values():
            score = score + s.str.contains(tok, na=False, regex=False).astype(int) * 15

    out = df.assign(_score=score)
    out = out[out["_score"] > 0].sort_values("_score", ascending=False)
    return out.drop(columns=["_score"])
