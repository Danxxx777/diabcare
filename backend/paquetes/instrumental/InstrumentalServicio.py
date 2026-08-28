"""Inventario y transiciones trazables de instrumental hospitalario."""

from datetime import datetime
from nucleo.utilidades.ParquetStore import ParquetStore

instrumentos = ParquetStore(
    "operativo/instrumental.parquet",
    ["id_instrumental", "codigo", "nombre", "tipo", "serie", "estado", "ubicacion", "responsable", "id_admision", "id_paciente", "paciente_nombre", "habitacion", "existencia", "notas", "activo", "creado_en", "actualizado_en"],
    "id_instrumental", "instrumentos", modo_borrado="activo",
)
movimientos = ParquetStore(
    "operativo/instrumental_movimientos.parquet",
    ["id_movimiento", "id_instrumental", "accion", "estado_anterior", "estado_nuevo", "ubicacion", "responsable", "detalle", "fecha", "id_admision", "id_paciente", "paciente_nombre", "habitacion", "creado_en", "actualizado_en"],
    "id_movimiento", "movimientos", modo_borrado="estado",
)


def listar(offset: int = 0, limit: int = 100, q: str = "", estado: str = "") -> dict:
    filtros = {"estado": estado} if estado else None
    return instrumentos.listar(offset, limit, filtros=filtros, q=q, q_campos=["codigo", "nombre", "tipo", "serie", "ubicacion", "responsable", "paciente_nombre", "habitacion"], incluir_inactivos=True)


def _codigo_automatico(tipo: str) -> str:
    prefijos = {"instrumental": "INS", "equipo": "EQP", "dispositivo": "DIS"}
    prefijo = prefijos.get(tipo, "EQP")
    filas = instrumentos.listar(limit=10**9, incluir_inactivos=True).get("instrumentos", [])
    usados = []
    for fila in filas:
        codigo = str(fila.get("codigo") or "").upper()
        if codigo.startswith(prefijo + "-"):
            try:
                usados.append(int(codigo.split("-", 1)[1]))
            except (TypeError, ValueError):
                pass
    return f"{prefijo}-{(max(usados, default=0) + 1):04d}"


def crear(datos: dict) -> dict:
    tipo = str(datos.get("tipo") or "instrumental").strip().lower()
    codigo = str(datos.get("codigo") or "").strip().upper() or _codigo_automatico(tipo)
    nombre = str(datos.get("nombre") or "").strip()
    if not nombre:
        return {"error": "El nombre del equipo es obligatorio"}
    if instrumentos.listar(limit=10**9, filtros={"codigo": codigo}, incluir_inactivos=True).get("instrumentos"):
        return {"error": "Ya existe instrumental con ese código"}
    existencia = int(datos.get("existencia") or 1)
    if existencia < 1:
        return {"error": "La existencia debe ser mayor que cero"}
    return instrumentos.crear({
        "codigo": codigo, "nombre": nombre, "tipo": tipo,
        "serie": str(datos.get("serie") or "").strip(), "estado": "disponible",
        "ubicacion": str(datos.get("ubicacion") or "Almacén clínico").strip(), "responsable": "",
        "id_admision": "", "id_paciente": "", "paciente_nombre": "", "habitacion": "",
        "existencia": existencia, "notas": str(datos.get("notas") or "").strip(), "activo": True,
    })


def _registrar_movimiento(item: dict, accion: str, estado_nuevo: str, datos: dict) -> None:
    movimientos.crear({
        "id_instrumental": item["id_instrumental"], "accion": accion,
        "estado_anterior": item.get("estado") or "", "estado_nuevo": estado_nuevo,
        "ubicacion": str(datos.get("ubicacion") or item.get("ubicacion") or ""),
        "responsable": str(datos.get("responsable") or ""), "detalle": str(datos.get("detalle") or ""),
        "id_admision": str(datos.get("id_admision") or ""), "id_paciente": str(datos.get("id_paciente") or ""),
        "paciente_nombre": str(datos.get("paciente_nombre") or ""), "habitacion": str(datos.get("habitacion") or ""),
        "fecha": datetime.now().isoformat(),
    })


def asignados_admision(id_admision: str) -> dict:
    return instrumentos.listar(limit=500, filtros={"estado": "asignado", "id_admision": str(id_admision)}, incluir_inactivos=True)


def reubicar_por_admision(id_admision: str, habitacion: str) -> None:
    for item in asignados_admision(id_admision).get("instrumentos", []):
        cambios = {"habitacion": habitacion, "ubicacion": f"Habitación {habitacion}"}
        _registrar_movimiento(item, "trasladar", "asignado", {**item, **cambios, "detalle": "Traslado de habitación"})
        instrumentos.actualizar(str(item["id_instrumental"]), cambios)


def transicionar(id_instrumental: str, accion: str, datos: dict | None = None) -> dict:
    datos = datos or {}
    item = instrumentos.obtener(id_instrumental)
    if item.get("error"):
        return item
    estado = str(item.get("estado") or "disponible").lower()
    accion = str(accion or "").lower().strip()
    vacio = {"id_admision": "", "id_paciente": "", "paciente_nombre": "", "habitacion": ""}

    if accion == "asignar":
        if estado != "disponible":
            return {"error": "Solo el instrumental disponible puede asignarse"}
        responsable = str(datos.get("responsable") or "").strip()
        if not responsable:
            return {"error": "El responsable es obligatorio para asignar"}
        vinculacion = dict(vacio)
        id_admision = str(datos.get("id_admision") or "").strip()
        if id_admision:
            from paquetes.clinico.admisiones.AdmisionesServicio import obtener
            admision = obtener(id_admision)
            if admision.get("error"):
                return admision
            if str(admision.get("tipo")) != "hospitalizacion" or str(admision.get("estado")) != "activa":
                return {"error": "El instrumental solo puede vincularse a una hospitalización activa"}
            habitacion = str(admision.get("habitacion") or "").strip()
            if not habitacion:
                return {"error": "La hospitalización no tiene una habitación asignada"}
            vinculacion = {"id_admision": id_admision, "id_paciente": str(admision.get("id_paciente") or ""), "paciente_nombre": str(admision.get("paciente_nombre") or ""), "habitacion": habitacion}
        cambios = {"estado": "asignado", "responsable": responsable, "ubicacion": f"Habitación {vinculacion['habitacion']}" if vinculacion["habitacion"] else str(datos.get("ubicacion") or item.get("ubicacion") or "Área clínica"), **vinculacion}
    elif accion == "devolver":
        if estado != "asignado":
            return {"error": "Solo el instrumental asignado puede devolverse"}
        cambios = {"estado": "disponible", "responsable": "", "ubicacion": str(datos.get("ubicacion") or "Almacén clínico"), **vacio}
    elif accion == "mantenimiento":
        if estado == "baja":
            return {"error": "El instrumental dado de baja no puede entrar a mantenimiento"}
        cambios = {"estado": "mantenimiento", "responsable": "", "ubicacion": str(datos.get("ubicacion") or "Mantenimiento"), **vacio}
    elif accion == "habilitar":
        if estado != "mantenimiento":
            return {"error": "Solo el instrumental en mantenimiento puede habilitarse"}
        cambios = {"estado": "disponible", "ubicacion": "Almacén clínico", "responsable": "", **vacio}
    elif accion == "baja":
        if estado == "baja":
            return {"error": "El instrumental ya fue dado de baja"}
        cambios = {"estado": "baja", "activo": False, "responsable": "", **vacio}
    else:
        return {"error": "Acción inválida"}

    _registrar_movimiento(item, accion, cambios["estado"], {**datos, **cambios})
    resultado = instrumentos.actualizar(id_instrumental, cambios)
    return resultado if resultado.get("error") else {**resultado, "estado": cambios["estado"]}


def historial(id_instrumental: str) -> dict:
    return movimientos.listar(limit=500, filtros={"id_instrumental": id_instrumental}, incluir_inactivos=True, orden="fecha")
