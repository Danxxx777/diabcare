# -*- coding: utf-8 -*-
"""
Turno de caja: apertura, cierre y arqueo.

Antes solo existía `cierre_caja()` en farmacia y recibía `monto_esperado` desde
el cliente, así que el cuadre se podía falsear desde el navegador y no había
turno contra el cual cerrar. Aquí el esperado lo calcula el sistema sumando los
pagos registrados dentro de la ventana del turno, que es lo que hace que el
arqueo signifique algo.
"""
from __future__ import annotations

from datetime import datetime, timezone

from nucleo.utilidades.ParquetStore import ParquetStore

COLUMNAS = [
    "id_turno", "estado",
    "abierto_en", "abierto_por", "fondo_inicial",
    "cerrado_en", "cerrado_por",
    "total_efectivo", "total_tarjeta", "total_transferencia", "total_otros",
    "esperado_efectivo", "contado_efectivo", "diferencia",
    "num_pagos", "notas",
    "creado_en", "actualizado_en",
]

turnos = ParquetStore(
    "negocio/oper_turno_caja.parquet",
    COLUMNAS,
    "id_turno", "turnos", modo_borrado="estado", valor_anulado="anulado",
)

# El efectivo es lo único que se cuenta a mano; lo demás deja rastro electrónico.
METODOS_EFECTIVO = ("efectivo",)
METODOS_TARJETA = ("tarjeta", "qr", "stripe")
METODOS_TRANSFERENCIA = ("transferencia", "deposito", "débito", "debito")


def _now() -> str:
    """
    UTC, igual que ParquetStore.

    La ventana del turno se compara como texto contra el `creado_en` de cada
    pago, y ese lo sella ParquetStore en UTC. Usar hora local aquí dejaba el
    turno cinco horas por detrás y ningún cobro caía dentro: el arqueo daba
    siempre cero.
    """
    # Con microsegundos, igual que ParquetStore: truncar al segundo creaba una
    # franja ambigua entre el cierre de un turno y la apertura del siguiente, y
    # un mismo cobro podia contarse en los dos.
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def _ts(valor) -> datetime | None:
    """
    ISO a datetime. La ventana del turno NO puede compararse como texto: el
    turno sella los instantes truncados al segundo y ParquetStore los guarda
    con microsegundos, así que "18:42:06.481" > "18:42:06" y el último cobro
    del turno quedaba fuera del arqueo por menos de un segundo.
    """
    s = str(valor or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", ""))
    except ValueError:
        return None


def _money(v) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def turno_abierto() -> dict | None:
    """El turno vigente, o None. Solo puede haber uno a la vez."""
    try:
        filas = turnos.listar(limit=500, incluir_inactivos=True).get("turnos") or []
    except Exception:
        return None
    abiertos = [t for t in filas if str(t.get("estado") or "").lower() == "abierto"]
    if not abiertos:
        return None
    abiertos.sort(key=lambda t: str(t.get("abierto_en") or ""), reverse=True)
    return abiertos[0]


def abrir_turno(usuario: str, fondo_inicial: float = 0.0, notas: str = "") -> dict:
    if turno_abierto():
        return {"error": "Ya hay un turno de caja abierto. Ciérrelo antes de abrir otro."}
    fondo = _money(fondo_inicial)
    if fondo < 0:
        return {"error": "El fondo inicial no puede ser negativo"}
    creado = turnos.crear({
        "estado": "abierto",
        "abierto_en": _now(),
        "abierto_por": str(usuario or "sistema"),
        "fondo_inicial": fondo,
        "notas": str(notas or ""),
        # Sembrar los numericos en cero, no dejarlos vacios: ParquetStore rellena
        # los faltantes con "" y pandas fija la columna como texto, de modo que
        # el cierre no podria escribir un float encima.
        "total_efectivo": 0.0, "total_tarjeta": 0.0,
        "total_transferencia": 0.0, "total_otros": 0.0,
        "esperado_efectivo": 0.0, "contado_efectivo": 0.0,
        "diferencia": 0.0, "num_pagos": 0,
    })
    if creado.get("error"):
        return creado
    return {"mensaje": "Turno de caja abierto", "turno": estado_caja()}


def _pagos_del_turno(turno: dict) -> list[dict]:
    """Pagos registrados entre la apertura y ahora (o el cierre)."""
    from paquetes.facturacion.FacturacionServicio import pagos

    desde = _ts(turno.get("abierto_en"))
    hasta = _ts(turno.get("cerrado_en")) or datetime.utcnow()
    if desde is None:
        return []
    try:
        # Leer sin caché: ParquetCache sirve hasta 12 s de antigüedad y cerrar
        # la caja justo después de cobrar dejaba ese último pago fuera del
        # arqueo. Un cuadre no puede depender de la frescura de un caché.
        from nucleo.utilidades.ParquetCache import invalidar
        invalidar(pagos.__dict__.get("bucket", "diabcare-app"), pagos.archivo)
    except Exception:
        pass
    try:
        filas = pagos.listar(limit=100_000).get("pagos") or []
    except Exception:
        return []
    out = []
    for p in filas:
        # `creado_en` es el instante real del cobro; `fecha` es solo el día.
        ts = _ts(p.get("creado_en"))
        if ts is None:
            continue
        if desde <= ts <= hasta:
            out.append(p)
    return out


def _totales(pagos_turno: list[dict]) -> dict:
    tot = {"efectivo": 0.0, "tarjeta": 0.0, "transferencia": 0.0, "otros": 0.0}
    for p in pagos_turno:
        metodo = str(p.get("metodo") or "").strip().lower()
        monto = _money(p.get("monto"))
        if metodo in METODOS_EFECTIVO:
            tot["efectivo"] += monto
        elif metodo in METODOS_TARJETA:
            tot["tarjeta"] += monto
        elif metodo in METODOS_TRANSFERENCIA:
            tot["transferencia"] += monto
        else:
            tot["otros"] += monto
    return {k: round(v, 2) for k, v in tot.items()}


def estado_caja() -> dict:
    """Situación actual: turno abierto con lo acumulado, o caja cerrada."""
    t = turno_abierto()
    if not t:
        return {"abierta": False, "mensaje": "Caja cerrada. Abra un turno para poder cobrar."}
    pg = _pagos_del_turno(t)
    tot = _totales(pg)
    fondo = _money(t.get("fondo_inicial"))
    return {
        "abierta": True,
        "id_turno": t.get("id_turno"),
        "abierto_en": t.get("abierto_en"),
        "abierto_por": t.get("abierto_por"),
        "fondo_inicial": fondo,
        "num_pagos": len(pg),
        "totales": tot,
        # Lo que debería haber en el cajón: fondo + lo cobrado en efectivo.
        "esperado_efectivo": round(fondo + tot["efectivo"], 2),
        "total_cobrado": round(sum(tot.values()), 2),
    }


def cerrar_turno(usuario: str, contado_efectivo: float, notas: str = "") -> dict:
    t = turno_abierto()
    if not t:
        return {"error": "No hay un turno de caja abierto"}
    pg = _pagos_del_turno(t)
    tot = _totales(pg)
    fondo = _money(t.get("fondo_inicial"))
    esperado = round(fondo + tot["efectivo"], 2)
    contado = _money(contado_efectivo)
    diferencia = round(contado - esperado, 2)

    actualizado = turnos.actualizar(str(t.get("id_turno")), {
        "estado": "cerrado",
        "cerrado_en": _now(),
        "cerrado_por": str(usuario or "sistema"),
        "total_efectivo": tot["efectivo"],
        "total_tarjeta": tot["tarjeta"],
        "total_transferencia": tot["transferencia"],
        "total_otros": tot["otros"],
        "esperado_efectivo": esperado,
        "contado_efectivo": contado,
        "diferencia": diferencia,
        "num_pagos": len(pg),
        "notas": str(notas or t.get("notas") or ""),
    })
    if actualizado.get("error"):
        return actualizado
    if diferencia > 0:
        veredicto = f"Sobrante de {abs(diferencia):.2f}"
    elif diferencia < 0:
        veredicto = f"Faltante de {abs(diferencia):.2f}"
    else:
        veredicto = "Caja cuadrada"
    return {
        "mensaje": f"Turno cerrado. {veredicto}.",
        "id_turno": t.get("id_turno"),
        "fondo_inicial": fondo,
        "totales": tot,
        "esperado_efectivo": esperado,
        "contado_efectivo": contado,
        "diferencia": diferencia,
        "cuadrada": diferencia == 0,
        "num_pagos": len(pg),
    }


def historial(limite: int = 30) -> dict:
    try:
        filas = turnos.listar(limit=limite, incluir_inactivos=True).get("turnos") or []
    except Exception:
        return {"turnos": [], "total": 0}
    filas.sort(key=lambda t: str(t.get("abierto_en") or ""), reverse=True)
    return {"turnos": filas[:limite], "total": len(filas)}


def exigir_caja_abierta() -> str:
    """Mensaje de error si no se puede cobrar, o cadena vacía."""
    if not turno_abierto():
        return "La caja está cerrada. Abra el turno en Caja → Apertura antes de cobrar."
    return ""
