-- Informe tradicional (SQL ANSI / SQLite 3 compatible).
-- Sin funciones propietarias: portable a PostgreSQL con cambios mínimos
-- (p. ej. CAST explícito si el motor lo exige).

-- KPI global
SELECT
  COUNT(*) AS total_registros,
  SUM(CASE WHEN diabetes = 1 THEN 1 ELSE 0 END) AS con_diabetes,
  SUM(CASE WHEN diabetes = 0 THEN 1 ELSE 0 END) AS sin_diabetes,
  ROUND(100.0 * SUM(CASE WHEN diabetes = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS prevalencia_pct,
  ROUND(AVG(age), 2) AS edad_promedio,
  ROUND(AVG(bmi), 2) AS bmi_promedio,
  ROUND(AVG(hbA1c_level), 2) AS hba1c_promedio,
  ROUND(AVG(blood_glucose_level), 2) AS glucosa_promedio
FROM diabetes;

-- Desglose por diagnóstico
SELECT
  diabetes,
  COUNT(*) AS n,
  ROUND(AVG(age), 2) AS edad_prom,
  ROUND(AVG(bmi), 2) AS bmi_prom,
  ROUND(AVG(hbA1c_level), 2) AS hba1c_prom,
  ROUND(AVG(blood_glucose_level), 2) AS glucosa_prom
FROM diabetes
GROUP BY diabetes
ORDER BY diabetes;

-- Top ubicaciones (filtro compuesto)
SELECT
  location,
  COUNT(*) AS n,
  SUM(CASE WHEN diabetes = 1 THEN 1 ELSE 0 END) AS con_diabetes,
  ROUND(100.0 * SUM(CASE WHEN diabetes = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS prevalencia_pct
FROM diabetes
GROUP BY location
ORDER BY n DESC
LIMIT 20;
