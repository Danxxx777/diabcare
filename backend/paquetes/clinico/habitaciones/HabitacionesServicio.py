# -*- coding: utf-8 -*-
"""Modulo de habitaciones: catalogo de camas y su estado operativo.

Reparto de responsabilidades:
  - La OCUPACION se deriva de admisiones (cama ocupada = admision activa de
    hospitalizacion con esa habitacion). No se duplica aqui.
  - El ESTADO OPERATIVO (limpieza, mantenimiento, bloqueada) si vive aqui,
    porque no depende de ninguna admision: una cama recien desocupada sigue
    sin poder recibir paciente hasta que alguien la marque lista.

Toda mutacion sobre la admision se delega en AdmisionesServicio.actualizar,
que ya valida camas y reubica el instrumental.
"""
from datetime import datetime

import pandas as pd

from nucleo.utilidades.ParquetCache import leer, escribir
from paquetes.clinico.admisiones import AdmisionesServicio as admisiones

BUCKET_APP = "diabcare-app"
ARCHIVO = "operativo/camas.parquet"
COLUMNAS = [
    "codigo", "piso", "estado_operativo", "nota",
    "actualizado_en", "actualizado_por",
]
ESTADOS_OPERATIVOS = {"disponible", "limpieza", "mantenimiento", "bloqueada"}
ESTANCIA_LARGA_DIAS = 7


def _ahora() -> str:
    return datetime.utcnow().isoformat()


def _semilla() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "codigo": codigo, "piso": codigo[2], "estado_operativo": "disponible",
            "nota": "", "actualizado_en": _ahora(), "actualizado_por": "sistema",
        }
        for codigo in admisiones.CAMAS
    ], columns=COLUMNAS)


def _catalogo(copiar: bool = True) -> pd.DataFrame:
    df = leer(BUCKET_APP, ARCHIVO, COLUMNAS, copiar=copiar)
    if df.empty:
        df = _semilla()
        escribir(BUCKET_APP, ARCHIVO, df)
        return df.copy() if copiar else df
    faltantes = [c for c in admisiones.CAMAS if c not in set(df["codigo"].astype(str))]
    if faltantes:
        # El catalogo crecio en codigo: incorpora las camas nuevas sin tocar las viejas
        nuevas = _semilla()
        nuevas = nuevas[nuevas["codigo"].isin(faltantes)]
        df = pd.concat([df, nuevas], ignore_index=True)
        escribir(BUCKET_APP, ARCHIVO, df)
    return df


def _guardar(df: pd.DataFrame):
    escribir(BUCKET_APP, ARCHIVO, df[[c for c in COLUMNAS if c in df.columns]])


def _equipos_por_admision() -> dict:
    por_admision = {}
    try:
        from paquetes.instrumental import InstrumentalServicio as instrumental
        for item in instrumental.listar(limit=500, estado="asignado").get("instrumentos", []):
            aid = str(item.get("id_admision") or "")
            if aid:
                por_admision.setdefault(aid, []).append(
                    str(item.get("nombre") or item.get("codigo") or "Equipo")
                )
    except Exception:
        pass
    return por_admision


def _internados() -> pd.DataFrame:
    df = admisiones._extraer(copiar=False)
    if df.empty:
        return df
    return df[(df["estado"].astype(str) == "activa") & (df["tipo"].astype(str) == "hospitalizacion")]


def mapa() -> dict:
    """Estado completo del piso: cada cama, sus contadores y quien espera cama."""
    catalogo = _catalogo(copiar=False)
    internados = _internados()
    equipos = _equipos_por_admision()

    ocupacion, fuera_catalogo = {}, 0
    codigos = set(catalogo["codigo"].astype(str))
    if not internados.empty:
        for _, fila in internados.iterrows():
            codigo = str(fila.get("habitacion") or "").strip()
            if not codigo:
                continue
            if codigo not in codigos:
                fuera_catalogo += 1
                continue
            aid = str(fila.get("id_admision") or "")
            lista = equipos.get(aid, [])
            dias = admisiones._dias_estancia(fila.get("fecha_ingreso"))
            ocupacion[codigo] = {
                "id_admision": aid,
                "id_paciente": str(fila.get("id_paciente") or ""),
                "paciente": str(fila.get("paciente_nombre") or ""),
                "documento": str(fila.get("documento") or ""),
                "servicio": str(fila.get("servicio") or ""),
                "medico": str(fila.get("medico_nombre") or ""),
                "motivo": str(fila.get("motivo") or ""),
                "fecha_ingreso": str(fila.get("fecha_ingreso") or "")[:10],
                "dias": dias,
                "estancia_larga": dias >= ESTANCIA_LARGA_DIAS,
                "instrumental_total": len(lista),
                "instrumental": lista,
            }

    camas, contadores = [], {e: 0 for e in ESTADOS_OPERATIVOS}
    contadores["ocupada"] = 0
    for _, fila in catalogo.iterrows():
        codigo = str(fila["codigo"])
        operativo = str(fila.get("estado_operativo") or "disponible")
        if operativo not in ESTADOS_OPERATIVOS:
            operativo = "disponible"
        ocupada = ocupacion.get(codigo)
        estado = "ocupada" if ocupada else ("libre" if operativo == "disponible" else operativo)
        contadores["ocupada" if ocupada else operativo] += 1
        camas.append({
            "codigo": codigo,
            "piso": str(fila.get("piso") or codigo[2:3]),
            "estado": estado,
            "estado_operativo": operativo,
            "nota": str(fila.get("nota") or ""),
            "actualizado_en": str(fila.get("actualizado_en") or ""),
            "actualizado_por": str(fila.get("actualizado_por") or ""),
            **(ocupada or {}),
        })
    camas.sort(key=lambda c: c["codigo"])

    pisos = {}
    for cama in camas:
        p = pisos.setdefault(cama["piso"], {"piso": cama["piso"], "total": 0, "ocupadas": 0})
        p["total"] += 1
        if cama["estado"] == "ocupada":
            p["ocupadas"] += 1

    total = len(camas)
    ocupadas = contadores["ocupada"]
    return {
        "total": total,
        "ocupadas": ocupadas,
        "libres": contadores["disponible"],
        "limpieza": contadores["limpieza"],
        "mantenimiento": contadores["mantenimiento"],
        "bloqueadas": contadores["bloqueada"],
        "fuera_catalogo": fuera_catalogo,
        "porcentaje": round(ocupadas / total * 100) if total else 0,
        "pisos": sorted(pisos.values(), key=lambda p: p["piso"]),
        "camas": camas,
        "esperando": esperando_cama(),
        "generado_en": _ahora(),
    }


def esperando_cama() -> list:
    """Hospitalizaciones activas que todavia no tienen cama asignada."""
    internados = _internados()
    if internados.empty:
        return []
    sin_cama = internados[internados["habitacion"].astype(str).str.strip() == ""]
    filas = []
    for _, fila in sin_cama.fillna("").iterrows():
        filas.append({
            "id_admision": str(fila.get("id_admision") or ""),
            "paciente": str(fila.get("paciente_nombre") or ""),
            "documento": str(fila.get("documento") or ""),
            "servicio": str(fila.get("servicio") or ""),
            "medico": str(fila.get("medico_nombre") or ""),
            "motivo": str(fila.get("motivo") or ""),
            "fecha_ingreso": str(fila.get("fecha_ingreso") or "")[:10],
            "dias_espera": admisiones._dias_estancia(fila.get("fecha_ingreso")),
        })
    return sorted(filas, key=lambda f: f["dias_espera"], reverse=True)


def _buscar_cama(codigo: str) -> tuple:
    df = _catalogo()
    idx = df.index[df["codigo"].astype(str) == str(codigo)].tolist()
    if not idx:
        return df, None
    return df, idx[0]


def _ocupante(codigo: str) -> dict:
    internados = _internados()
    if internados.empty:
        return {}
    fila = internados[internados["habitacion"].astype(str) == str(codigo)]
    if fila.empty:
        return {}
    return fila.fillna("").iloc[0].to_dict()


def cambiar_estado(codigo: str, estado: str, nota: str = "", usuario: str = "sistema") -> dict:
    estado = str(estado or "").lower()
    if estado not in ESTADOS_OPERATIVOS:
        return {"error": f"Estado invalido. Use: {', '.join(sorted(ESTADOS_OPERATIVOS))}"}
    df, idx = _buscar_cama(codigo)
    if idx is None:
        return {"error": "Esa cama no existe en el catalogo"}
    if _ocupante(codigo):
        return {"error": "La cama esta ocupada: da de alta o traslada al paciente antes de cambiar su estado"}
    df.at[idx, "estado_operativo"] = estado
    df.at[idx, "nota"] = str(nota or "")
    df.at[idx, "actualizado_en"] = _ahora()
    df.at[idx, "actualizado_por"] = usuario
    _guardar(df)
    return {"mensaje": f"Cama {codigo}: {estado}", "codigo": codigo, "estado_operativo": estado}


def asignar(codigo: str, id_admision: str, usuario: str = "sistema") -> dict:
    df, idx = _buscar_cama(codigo)
    if idx is None:
        return {"error": "Esa cama no existe en el catalogo"}
    operativo = str(df.at[idx, "estado_operativo"] or "disponible")
    if operativo != "disponible":
        return {"error": f"La cama {codigo} esta en {operativo}: marcala como lista antes de asignarla"}
    if _ocupante(codigo):
        return {"error": f"La cama {codigo} ya esta ocupada"}
    res = admisiones.actualizar(str(id_admision), {"habitacion": codigo, "tipo": "hospitalizacion"})
    if "error" in res:
        return res
    return {"mensaje": f"Paciente asignado a {codigo}", "codigo": codigo, "id_admision": id_admision}


def liberar(codigo: str, dar_alta: bool = False, usuario: str = "sistema") -> dict:
    """Saca al paciente de la cama y la deja en limpieza."""
    df, idx = _buscar_cama(codigo)
    if idx is None:
        return {"error": "Esa cama no existe en el catalogo"}
    ocupante = _ocupante(codigo)
    if not ocupante:
        return {"error": f"La cama {codigo} no tiene paciente"}
    id_admision = str(ocupante.get("id_admision") or "")
    cambios = {"estado": "alta"} if dar_alta else {"habitacion": ""}
    res = admisiones.actualizar(id_admision, cambios)
    if "error" in res:
        return res
    df.at[idx, "estado_operativo"] = "limpieza"
    df.at[idx, "nota"] = "Liberada, pendiente de limpieza"
    df.at[idx, "actualizado_en"] = _ahora()
    df.at[idx, "actualizado_por"] = usuario
    _guardar(df)
    return {
        "mensaje": f"Cama {codigo} liberada y en limpieza",
        "codigo": codigo, "id_admision": id_admision, "alta": bool(dar_alta),
    }


def trasladar(origen: str, destino: str, usuario: str = "sistema") -> dict:
    if str(origen) == str(destino):
        return {"error": "Origen y destino son la misma cama"}
    df, idx_destino = _buscar_cama(destino)
    if idx_destino is None:
        return {"error": "La cama destino no existe en el catalogo"}
    _, idx_origen = _buscar_cama(origen)
    if idx_origen is None:
        return {"error": "La cama origen no existe en el catalogo"}
    operativo = str(df.at[idx_destino, "estado_operativo"] or "disponible")
    if operativo != "disponible":
        return {"error": f"La cama {destino} esta en {operativo}: no puede recibir pacientes"}
    if _ocupante(destino):
        return {"error": f"La cama {destino} ya esta ocupada"}
    ocupante = _ocupante(origen)
    if not ocupante:
        return {"error": f"La cama {origen} no tiene paciente que trasladar"}
    id_admision = str(ocupante.get("id_admision") or "")
    res = admisiones.actualizar(id_admision, {"habitacion": destino})
    if "error" in res:
        return res
    df.at[idx_origen, "estado_operativo"] = "limpieza"
    df.at[idx_origen, "nota"] = f"Traslado a {destino}, pendiente de limpieza"
    df.at[idx_origen, "actualizado_en"] = _ahora()
    df.at[idx_origen, "actualizado_por"] = usuario
    _guardar(df)
    return {
        "mensaje": f"Traslado {origen} → {destino}",
        "origen": origen, "destino": destino, "id_admision": id_admision,
        "paciente": str(ocupante.get("paciente_nombre") or ""),
    }
