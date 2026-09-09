## Purpose

Permitir que el personal de Farmacia identifique visualmente el estado de vencimiento de cada lote y priorice su revisión antes de dispensarlo.

## ADDED Requirements

### Requirement: Clasificación del vencimiento

El sistema SHALL clasificar cada lote del inventario de Farmacia según su fecha de vencimiento y la fecha actual del servidor.

#### Scenario: Lote vencido
- **WHEN** la fecha de vencimiento del lote sea anterior a la fecha actual
- **THEN** el sistema SHALL clasificar el lote como `Vencido`

#### Scenario: Lote que vence hoy
- **WHEN** la fecha de vencimiento del lote sea igual a la fecha actual
- **THEN** el sistema SHALL clasificar el lote como `Próximo a vencer`

#### Scenario: Lote que vence dentro de 30 días
- **WHEN** la fecha de vencimiento del lote esté entre la fecha actual y 30 días después, inclusive
- **THEN** el sistema SHALL clasificar el lote como `Próximo a vencer`

#### Scenario: Lote vigente
- **WHEN** la fecha de vencimiento del lote sea posterior al límite de 30 días
- **THEN** el sistema SHALL clasificar el lote como `Vigente`

#### Scenario: Lote sin fecha válida
- **WHEN** la fecha de vencimiento esté ausente o no tenga un formato válido
- **THEN** el sistema SHALL clasificar el lote como `Sin fecha`

### Requirement: Visualización en el inventario

El sistema SHALL incluir el estado calculado en la consulta del inventario y SHALL mostrarlo en una columna visible junto a la fecha de vencimiento original.

#### Scenario: Consulta del inventario
- **WHEN** un usuario autorizado consulte el inventario de Farmacia
- **THEN** cada lote devuelto SHALL incluir su estado de vencimiento
- **AND** la interfaz SHALL mostrar ese estado sin reemplazar la fecha original

### Requirement: Clasificación sin efectos secundarios

El sistema MUST calcular el estado únicamente como información derivada y MUST conservar los datos almacenados y las reglas actuales de dispensación.

#### Scenario: Cálculo del estado
- **WHEN** el sistema clasifique un lote
- **THEN** no SHALL modificar la fecha, la cantidad, el estado activo ni otro dato persistido del lote
