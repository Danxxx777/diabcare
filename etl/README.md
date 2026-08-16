# Proceso ELT DiabCare (exhibicion academica)

Orden real: **Extract → Load → Transform (E→L→T)**.

| Paso | Modulo | Destino |
|------|--------|---------|
| E | extract.py | work temporal |
| L | load.py | diabetes-data/landing/ (crudo) |
| T | transform.py | diabetes-data/stage/ + DWH |

No es ETL: no se transforma antes de cargar al almacen.

## Estrategia

- Incremental (@hourly): solo novedades PB; no borra landing/stage.
- Historico (domingo): relee PB completo; anade Parquet y rematerializa DWH.

## DAGs

- diabcare_elt: E → L → T (@hourly)
- diabcare_elt_historico: E→L→T completo
- diabcare_benchmark_sql: SQL vs Parquet
