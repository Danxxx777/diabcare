# -*- coding: utf-8 -*-
"""Smoke de los 3 niveles (operativo / táctico / estratégico AGG)."""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

ok = 0
fail = 0
empty = 0


def check(nombre: str, fn):
    global ok, fail, empty
    try:
        r = fn()
        if r is None:
            print(f"  VACIO  {nombre} → None")
            empty += 1
            return
        if isinstance(r, dict) and r.get("error"):
            print(f"  FAIL   {nombre} → {r.get('error')}")
            fail += 1
            return
        extra = ""
        if isinstance(r, dict):
            keys = ("total", "facturado_total", "facturas", "citas", "pacientes",
                    "ingresos_por_dia", "ok", "estado")
            bits = []
            for k in keys:
                if k in r:
                    v = r[k]
                    if isinstance(v, list):
                        bits.append(f"{k}={len(v)}")
                    else:
                        bits.append(f"{k}={v}")
            extra = " | " + ", ".join(bits[:6]) if bits else " | keys=" + ",".join(list(r)[:8])
        print(f"  OK     {nombre}{extra}")
        ok += 1
    except Exception as e:
        print(f"  FAIL   {nombre} → {type(e).__name__}: {e}")
        fail += 1
        traceback.print_exc()


def main():
    print("=== OPERATIVO ===")
    from paquetes.clinico.pacientes.PacientesServicio import resumen as pac_res, listar as pac_list
    from paquetes.clinico.admisiones.AdmisionesServicio import resumen as adm_res
    from paquetes.clinico.citas.CitasServicio import hoy, resumen_operativo, listar as cit_list
    from paquetes.laboratorio.LaboratorioServicio import resumen_operativo as lab_res
    from paquetes.urgencias.UrgenciasServicio import resumen_operativo as urg_res
    from paquetes.farmacia.FarmaciaServicio import resumen_operativo as farm_res
    from paquetes.facturacion.FacturacionServicio import resumen_caja as fac_res
    from paquetes.comorbilidades.ComorbilidadesServicio import resumen_operativo as com_res
    from paquetes.rrhh.RrhhServicio import resumen_operativo as rrhh_res
    from paquetes.notificaciones.NotificacionesServicio import listar as notif_list
    from paquetes.auditoria.AuditoriaServicio import listar as aud_list
    from paquetes.usuarios.UsuariosServicio import obtener_usuarios

    check("pacientes.resumen", pac_res)
    check("pacientes.listar", lambda: pac_list(0, 5))
    check("admisiones.resumen", adm_res)
    check("citas.hoy", hoy)
    check("citas.resumen", resumen_operativo)
    check("citas.listar", lambda: cit_list(0, 5))
    check("laboratorio.resumen", lab_res)
    check("urgencias.resumen", urg_res)
    check("farmacia.resumen", farm_res)
    check("facturacion.resumen", fac_res)
    check("comorbilidades.resumen", com_res)
    check("rrhh.resumen", rrhh_res)
    check("notificaciones.listar", lambda: notif_list(limit=5, rol="administrador"))
    check("auditoria.listar", lambda: aud_list(0, 5))
    check("usuarios.listar", obtener_usuarios)

    print("\n=== TACTICO / ESTRATEGICO AGG ===")
    from paquetes.dataset.DatasetKpisServicio import resumen_kpis, informes_complejos
    from paquetes.dataset.DatasetDwhServicio import resumen_dwh
    from paquetes.registros_clinicos.RegistrosClinicosServicio import estadisticas
    from paquetes.prediccion.PrediccionServicio import obtener_metricas
    from paquetes.pipeline_elt.PipelineEtlServicio import estado_publico as pipe_estado

    check("dataset.negocio.kpis (AGG)", resumen_kpis)
    check("dataset.informes.complejos", informes_complejos)
    check("dataset.dwh.resumen", resumen_dwh)
    check("registros.estadisticas (workpanel)", estadisticas)
    check("prediccion.metricas", obtener_metricas)
    check("pipeline.estado", pipe_estado)

    print("\n=== FRONTEND (archivos) ===")
    paginas = [
        "frontend/paginas/inicio/index.html",
        "frontend/paginas/clinico/pacientes/index.html",
        "frontend/paginas/clinico/agenda/index.html",
        "frontend/paginas/clinico/mis_citas/index.html",
        "frontend/paginas/clinico/analisis/informes/index.html",
        "frontend/paginas/clinico/analisis/estadisticas/index.html",
        "frontend/paginas/clinico/analisis/diabetes/index.html",
        "frontend/paginas/clinico/prediccion/index.html",
        "frontend/paginas/clinico/reportes/index.html",
        "frontend/paginas/datos/dataset/index.html",
        "frontend/paginas/datos/pipeline_elt/index.html",
        "frontend/paginas/datos/modelo_ml/index.html",
        "frontend/paginas/negocio/facturacion/index.html",
        "frontend/paginas/negocio/farmacia/index.html",
    ]
    for rel in paginas:
        p = ROOT / rel
        if p.is_file() and p.stat().st_size > 200:
            print(f"  OK     {rel}")
            global ok
            ok += 1
        else:
            print(f"  FAIL   falta {rel}")
            global fail
            fail += 1

    print(f"\nResumen: ok={ok} fail={fail} vacio={empty}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
