"""Preparación del entorno clínico (DWH, pacientes, integraciones, alertas)."""

from __future__ import annotations

from servicios.configuracion.ConfiguracionClienteMinio import verificar_conexion


def preparar_clinica(usuario: str = "sistema") -> dict:
    resultado = {"pasos": [], "ok": True}

    def paso(nombre: str, fn):
        try:
            r = fn()
            resultado["pasos"].append({"paso": nombre, "ok": True, "detalle": r})
        except Exception as e:
            resultado["pasos"].append({"paso": nombre, "ok": False, "error": str(e)})
            resultado["ok"] = False

    paso("minio", lambda: {"conectado": verificar_conexion()})

    def dwh():
        from servicios.dataset.DatasetDwhServicio import materializar_dwh, resumen_dwh
        r = materializar_dwh()
        if not r.get("ok"):
            return resumen_dwh()
        return r

    paso("dwh", dwh)

    def pacientes():
        from servicios.pacientes.PacientesServicio import importar_desde_dataset, resumen
        r = importar_desde_dataset()
        if r.get("error") and "No hay datos" not in str(r.get("error", "")):
            return r
        return {**r, **resumen()}

    paso("pacientes_dataset", pacientes)

    def api_key():
        from servicios.integraciones.IntegracionesServicio import _obtener_api_key_info, generar_api_key
        if _obtener_api_key_info().get("configurada"):
            return {"mensaje": "API key ya existe"}
        return generar_api_key(usuario)

    paso("api_partner", api_key)

    def lead():
        from servicios.integraciones.IntegracionesServicio import listar_leads, registrar_lead
        if listar_leads(1):
            return {"mensaje": "Lead ya registrado"}
        return registrar_lead("Clínica Demo GA07", "demo@diabcare.local", "Hospital Central", "bootstrap")

    paso("hubspot", lead)

    def pago():
        from servicios.integraciones.IntegracionesServicio import listar_pagos, crear_pago, confirmar_pago
        pagos = listar_pagos(20)
        pagados = [p for p in pagos if p.get("estado") == "pagado"]
        if pagados:
            return {"mensaje": "Pago ya confirmado"}
        r = crear_pago("profesional", 99.0)
        pid = r.get("pago", {}).get("id")
        if pid:
            confirmar_pago(pid)
        return r

    paso("stripe", pago)

    def cicd():
        from servicios.integraciones.IntegracionesServicio import ejecutar_pipeline_cicd
        return ejecutar_pipeline_cicd(usuario)

    paso("cicd", cicd)

    def alertas():
        from servicios.notificaciones.NotificacionesServicio import evaluar_todas
        return evaluar_todas()

    paso("alertas", alertas)

    return resultado
