# -*- coding: utf-8 -*-
"""Utilidad compartida: CRUD Parquet en MinIO con borrado lógico (RN-CRUD-001)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable, Optional

import pandas as pd

from nucleo.utilidades.Busqueda import rankear_dataframe
from nucleo.utilidades.ParquetCache import leer, escribir

BUCKET_APP = "diabcare-app"


def _valor_simple(v):
    """Valor legible para el registro de auditoria (sin tipos de pandas)."""
    if v is None:
        return ""
    try:
        import pandas as _pd
        if _pd.isna(v):
            return ""
    except Exception:
        pass
    if isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


def _now() -> str:
    return datetime.utcnow().isoformat()


class ParquetStore:
    """CRUD genérico sobre un archivo Parquet en diabcare-app."""

    def __init__(
        self,
        archivo: str,
        columnas: list[str],
        id_campo: str,
        coleccion: str,
        *,
        modo_borrado: str = "estado",  # "estado" | "activo"
        valor_anulado: str = "anulado",
    ):
        self.archivo = archivo
        self.columnas = list(columnas)
        self.id_campo = id_campo
        self.coleccion = coleccion
        self.modo_borrado = modo_borrado
        self.valor_anulado = valor_anulado

    def extraer(self, copiar: bool = True) -> pd.DataFrame:
        return leer(BUCKET_APP, self.archivo, self.columnas, copiar=copiar)

    def cargar(self, df: pd.DataFrame) -> None:
        for col in self.columnas:
            if col not in df.columns:
                df[col] = "" if col != "activo" else True
        cols = [c for c in self.columnas if c in df.columns]
        escribir(BUCKET_APP, self.archivo, df[cols] if cols else df)

    def listar(
        self,
        offset: int = 0,
        limit: int = 50,
        filtros: Optional[dict] = None,
        q: str = "",
        q_campos: Optional[list[str]] = None,
        incluir_inactivos: bool = False,
        orden: Optional[str] = None,
    ) -> dict:
        df = self.extraer(copiar=False)
        if df.empty:
            return {"total": 0, self.coleccion: []}
        if not incluir_inactivos:
            if self.modo_borrado == "activo" and "activo" in df.columns:
                df = df[df["activo"].astype(str).str.lower().isin(["true", "1", "yes"]) | (df["activo"] == True)]  # noqa: E712
            elif self.modo_borrado == "estado" and "estado" in df.columns:
                df = df[~df["estado"].astype(str).str.lower().isin([self.valor_anulado, "anulada", "anulado"])]
        if filtros:
            for k, v in filtros.items():
                if v is None or v == "" or k not in df.columns:
                    continue
                df = df[df[k].astype(str) == str(v)]
        if q and q_campos:
            df = rankear_dataframe(df, q, list(q_campos))
        elif q:
            # Si no se pasan campos, busca en todas las columnas texto
            df = rankear_dataframe(df, q, [c for c in df.columns if c != self.id_campo])
        total = int(len(df))
        if orden and orden in df.columns:
            # Mantener score si ya ordenó por relevancia; solo orden secundario si no hay q
            if not q:
                df = df.sort_values(orden, ascending=False)
        chunk = df.iloc[offset: offset + limit]
        return {"total": total, self.coleccion: chunk.fillna("").to_dict(orient="records")}

    def obtener(self, id_valor: str) -> dict:
        df = self.extraer(copiar=False)
        fila = df[df[self.id_campo].astype(str) == str(id_valor)]
        if fila.empty:
            return {"error": f"{self.coleccion[:-1] if self.coleccion.endswith('s') else self.coleccion} no encontrado"}
        return fila.fillna("").iloc[0].to_dict()

    def crear(self, datos: dict, defaults: Optional[dict] = None, validar: Optional[Callable[[dict], Optional[str]]] = None) -> dict:
        row = dict(defaults or {})
        row.update({k: v for k, v in datos.items() if k in self.columnas})
        if validar:
            err = validar(row)
            if err:
                return {"error": err}
        if not row.get(self.id_campo):
            row[self.id_campo] = str(uuid.uuid4())
        now = _now()
        if "creado_en" in self.columnas:
            row.setdefault("creado_en", now)
        if "actualizado_en" in self.columnas:
            row["actualizado_en"] = now
        if self.modo_borrado == "activo" and "activo" in self.columnas:
            row.setdefault("activo", True)
        if self.modo_borrado == "estado" and "estado" in self.columnas:
            row.setdefault("estado", "activo" if "activo" in (row.get("estado"), None) or True else row.get("estado", "registrado"))
        for k in self.columnas:
            row.setdefault(k, "" if k != "activo" else True)
        df = self.extraer(copiar=True)
        nueva = pd.DataFrame([{k: row.get(k, "") for k in self.columnas}])
        self.cargar(pd.concat([df, nueva], ignore_index=True) if not df.empty else nueva)
        return {"mensaje": "creado", self.id_campo: row[self.id_campo], "registro": {k: row.get(k) for k in self.columnas}}

    def actualizar(self, id_valor: str, cambios: dict) -> dict:
        df = self.extraer()
        idx = df.index[df[self.id_campo].astype(str) == str(id_valor)].tolist()
        if not idx:
            return {"error": "no encontrado"}
        antes, despues = {}, {}
        for k, v in cambios.items():
            if k in self.columnas and k not in (self.id_campo, "creado_en"):
                previo = df.at[idx[0], k]
                # Solo lo que de verdad cambia: el evento debe leerse de un vistazo.
                if str(previo) != str(v):
                    antes[k] = _valor_simple(previo)
                    despues[k] = _valor_simple(v)
                df.at[idx[0], k] = v
        if "actualizado_en" in self.columnas:
            df.at[idx[0], "actualizado_en"] = _now()
        self.cargar(df)
        self._pendiente_diff = {"antes": antes, "despues": despues} if antes else None
        return {"mensaje": "actualizado", self.id_campo: id_valor}

    def eliminar_logico(self, id_valor: str) -> dict:
        df = self.extraer()
        idx = df.index[df[self.id_campo].astype(str) == str(id_valor)].tolist()
        if not idx:
            return {"error": "no encontrado"}
        estado_previo = df.at[idx[0], "activo" if self.modo_borrado == "activo" else "estado"]
        if self.modo_borrado == "activo":
            df.at[idx[0], "activo"] = False
        else:
            campo_estado = "estado" if "estado" in self.columnas else None
            if not campo_estado:
                return {"error": "sin campo de borrado lógico"}
            # prefer femenino si el valor actual parece femenino
            actual = str(df.at[idx[0], "estado"] or "")
            valor = "anulada" if actual.endswith("a") or actual in ("emitida", "pagada", "pendiente", "registrada") else self.valor_anulado
            if valor not in ("anulado", "anulada"):
                valor = "anulada" if "factura" in self.archivo or "receta" in self.archivo or "compra" in self.archivo or "orden" in self.archivo else "anulado"
            df.at[idx[0], "estado"] = valor
        if "actualizado_en" in self.columnas:
            df.at[idx[0], "actualizado_en"] = _now()
        self.cargar(df)
        campo = "activo" if self.modo_borrado == "activo" else "estado"
        self._pendiente_diff = {
            "antes": {campo: _valor_simple(estado_previo)},
            "despues": {campo: _valor_simple(df.at[idx[0], campo])},
        }
        return {"mensaje": "eliminado_logico", self.id_campo: id_valor}

    def auditar(self, usuario: str, tipo: str, detalle: str, modulo: str) -> None:
        diff = getattr(self, "_pendiente_diff", None)
        self._pendiente_diff = None
        try:
            from paquetes.auditoria.AuditoriaServicio import registrar
            registrar(
                usuario, tipo, modulo, detalle,
                antes=(diff or {}).get("antes"),
                despues=(diff or {}).get("despues"),
            )
        except Exception:
            pass
