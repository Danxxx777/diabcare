## Why

El personal de Farmacia puede consultar la fecha de vencimiento de cada lote, pero debe interpretarla manualmente. Un semáforo visible reduce el riesgo de dispensar productos vencidos y permite priorizar los lotes próximos a vencer.

## What Changes

- Calcular para cada lote su estado de vencimiento a partir de la fecha actual.
- Clasificar los lotes como `Vencido`, `Próximo a vencer`, `Vigente` o `Sin fecha`.
- Considerar próximo a vencer un lote cuya fecha esté entre hoy y los siguientes 30 días, inclusive.
- Mostrar el estado como una columna visible en el inventario de Farmacia.
- Mantener disponible la fecha de vencimiento original y no modificar las reglas actuales de dispensación ni el inventario.
- Incluir pruebas para los límites temporales y las fechas ausentes o inválidas.

## Capabilities

### New Capabilities

- `farmacia/alertas-vencimiento`: Clasificación y visualización del estado de vencimiento de los lotes del inventario de Farmacia.

### Modified Capabilities

Ninguna.

## Impact

- API de consulta de inventario de Farmacia.
- Servicio de Farmacia que prepara los datos de los lotes.
- Tabla de inventario en la interfaz web.
- Pruebas automatizadas del módulo de Farmacia.
- No requiere nuevas dependencias ni cambios de almacenamiento.
