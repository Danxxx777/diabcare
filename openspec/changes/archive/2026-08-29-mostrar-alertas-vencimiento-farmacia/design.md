## Context

La ruta `GET /api/farmacia/inventario` devuelve directamente el resultado de `ParquetStore.listar`. La tabla del inventario consume la colección `lotes` y ya admite columnas con funciones de renderizado. Consulte `proposal.md` para la motivación y `specs/farmacia/alertas-vencimiento/spec.md` para el comportamiento requerido.

## Goals / Non-Goals

**Goals:**

- Centralizar la clasificación temporal en el backend para que todos los consumidores reciban el mismo estado.
- Mantener el contrato actual de la respuesta y agregar solamente un campo derivado por lote.
- Probar la clasificación de forma determinista mediante una fecha de referencia controlable.

**Non-Goals:**

- Impedir automáticamente la dispensación de lotes vencidos.
- Crear notificaciones persistentes o modificar datos Parquet.
- Permitir configurar el umbral de 30 días desde la interfaz.

## Decisions

### Clasificar en el servicio de Farmacia

Se agregará una función pura que reciba la fecha de vencimiento y una fecha de referencia opcional. La consulta de inventario enriquecerá cada lote con `estado_vencimiento` antes de devolverlo.

Alternativa considerada: calcular el estado únicamente en JavaScript. Se descarta porque otros consumidores de la API podrían obtener una clasificación diferente y porque las pruebas de límites serían menos directas.

### Mantener la respuesta actual

La ruta conservará la colección `lotes`, la paginación y los campos existentes. Solo añadirá `estado_vencimiento` a cada elemento, por lo que el cambio es compatible con consumidores actuales.

Alternativa considerada: crear una ruta exclusiva para alertas. Se descarta porque duplicaría la consulta y complicaría la demostración sin aportar una necesidad funcional.

### Usar fechas calendario

La clasificación comparará valores de tipo `date`, sin considerar hora ni zona horaria. Se aceptará el formato ISO `YYYY-MM-DD`; valores ausentes o inválidos producirán `Sin fecha`.

Alternativa considerada: comparar cadenas ISO. Se descarta para evitar resultados incorrectos ante entradas inválidas y para expresar claramente los límites de 0 y 30 días.

### Mostrar el estado como insignia

La tabla añadirá una columna `Estado de vencimiento` junto a `Vence` y aprovechará el renderizado de insignias existente. La fecha original permanecerá visible para permitir verificación manual.

## Risks / Trade-offs

- [La fecha del servidor puede diferir de la fecha local del usuario] - La regla usa explícitamente la fecha del servidor como referencia única y comprobable.
- [Los registros históricos pueden contener fechas inválidas] - Se clasifican como `Sin fecha` sin interrumpir la consulta completa.
- [El umbral fijo puede cambiar en el futuro] - La función aislará el valor de 30 días para facilitar una configuración posterior sin ampliar este cambio.

## Migration Plan

No se requiere migración de datos. El despliegue consiste en actualizar backend e interfaz. El rollback elimina el campo derivado y la columna sin alterar registros persistidos.
