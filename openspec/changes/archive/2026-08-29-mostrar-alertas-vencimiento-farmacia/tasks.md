## 1. Clasificación en el backend

- [x] 1.1 Crear una función pura para clasificar fechas como `Vencido`, `Próximo a vencer`, `Vigente` o `Sin fecha`, y verificar con pruebas los límites de ayer, hoy, 30 días, 31 días, fecha ausente y fecha inválida.
- [x] 1.2 Enriquecer la respuesta de `GET /api/farmacia/inventario` con `estado_vencimiento` sin cambiar los campos existentes, y verificar mediante una prueba de la ruta que cada lote incluya el campo.

## 2. Visualización en Farmacia

- [x] 2.1 Añadir la columna `Estado de vencimiento` junto a `Vence` en la tabla de inventario y verificar en el navegador que los cuatro estados se muestren sin ocultar la fecha original.
- [x] 2.2 Renderizar el estado mediante las insignias visuales existentes y verificar que la tabla mantenga sus acciones de creación y edición.

## 3. Validación integral

- [x] 3.1 Ejecutar las pruebas enfocadas del módulo de Farmacia y verificar que todas finalicen correctamente.
- [x] 3.2 Ejecutar `openspec validate mostrar-alertas-vencimiento-farmacia --strict` y comprobar manualmente en DiabCare que el inventario muestre la clasificación esperada.
