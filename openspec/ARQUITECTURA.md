# Arquitectura de DiabCare

## Propósito

DiabCare es un sistema web hospitalario que integra atención clínica, operaciones administrativas, farmacia, laboratorio, analítica y modelos de predicción relacionados con diabetes. Este documento conserva las decisiones técnicas necesarias para que una IA pueda interpretar las especificaciones y ubicar su implementación.

## Componentes principales

### Frontend

- Aplicación multipágina construida con HTML, CSS y JavaScript.
- Páginas organizadas por dominio en `frontend/paginas/`.
- Cliente HTTP compartido en `frontend/estaticos/api.js`.
- Navegación, sesión y permisos visibles gestionados por utilidades compartidas de `frontend/estaticos/`.
- Los módulos reutilizan componentes CRUD y patrones de tarjetas e insignias existentes.

### Backend

- API REST construida con FastAPI.
- Punto de entrada en `backend/Principal.py`.
- Módulos funcionales en `backend/paquetes/`.
- Cada módulo separa rutas HTTP y lógica de servicio cuando el dominio lo requiere.
- Utilidades compartidas, persistencia, permisos y modelos se encuentran en `backend/nucleo/`.

### Persistencia

- Los datos operativos y analíticos se almacenan principalmente como tablas Parquet.
- MinIO proporciona almacenamiento de objetos para las tablas y archivos generados.
- `ParquetStore` encapsula operaciones de listado, consulta, creación, actualización, eliminación lógica y auditoría.
- Los cambios deben conservar identificadores, nombres de columnas y compatibilidad con los datos existentes, salvo que una especificación incluya una migración explícita.

### Seguridad

- La autenticación usa sesiones y JWT.
- Los accesos se validan por rol y módulo en el backend.
- Los roles principales son `administrador`, `medico` y `analista`.
- Las operaciones de modificación relevantes deben conservar la auditoría y la eliminación lógica.

### Analítica y datos

- El pipeline sigue el orden ELT: extracción, carga y transformación.
- Los DAG de Airflow coordinan procesos analíticos cuando corresponde.
- Los módulos de dataset, análisis, predicción, reportes y modelo ML consumen datos materializados sin acoplar la interfaz a la persistencia.

## Flujo de una solicitud

1. El usuario inicia sesión y recibe una sesión autorizada.
2. La interfaz solicita un recurso mediante el cliente HTTP compartido.
3. FastAPI valida sesión, rol y permiso del módulo.
4. La ruta delega la operación al servicio del dominio.
5. El servicio aplica reglas de negocio y consulta o modifica Parquet mediante las utilidades compartidas.
6. La API devuelve una respuesta JSON que la página representa con los componentes existentes.
7. Las modificaciones relevantes quedan auditadas.

## Convenciones de implementación

- Mantener la organización por dominios y reutilizar patrones existentes.
- Evitar cambios globales para funcionalidades locales.
- No introducir dependencias si la plataforma actual ya resuelve la necesidad.
- Añadir pruebas enfocadas para reglas de negocio y contratos de API.
- Validar en navegador los cambios visibles.
- Mantener `openspec/specs/` como fuente de verdad del comportamiento esperado.

## Arranque local

- Aplicación: `http://localhost:8000`.
- API: `http://localhost:8000/api/`.
- MinIO: puertos `9000` y `9001`.
- Lanzador principal: `servidor.py`.
- Arranque completo para exhibición: `arrancar.ps1`.
