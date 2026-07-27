# P10 — Notificaciones y alertas (correo Brevo)

**Paquete**: `backend/paquetes/notificaciones/`  
**Frontend**: `/paginas/notificaciones/index.html`  
**Configuración correo**: `/paginas/gobierno/configuracion/index.html` (solo administrador)  
**Estado GA07**: **Parcial** (alertas clínicas + correo; churn CU-O16 pendiente)

---

## Casos de uso relacionados

| CU-O | Relación | Descripción |
|------|----------|-------------|
| **CU-O01** Login / recuperación | Parcial | Recuperar contraseña → código enviado por **correo** (Brevo SMTP) |
| **CU-O03** CRUD registros clínicos | Disparador | Al crear/editar registros con HbA1c o glucosa fuera de umbral → alerta + correo |
| **CU-O10** Dashboard / alertas TA06 §13 | **Principal** | Bandeja de notificaciones, evaluar umbrales, `hechos_alertas` en DWH |
| **CU-O16** Alerta churn (ML negocio) | Planificado | No implementado en demo; P10 cubre solo alertas **clínicas** |

---

## Requisitos implementados

- **RF-O-P10-002**: Notificaciones dirigidas por `destinatario_tipo` (`usuario|rol|paciente_email|todos`)
  y `canal` (`in_app|email|ambos`). Pacientes reciben solo correo (sin portal).
- Emisores: alertas clínicas → rol médico; reportes → rol analista/admin; facturas → email paciente + admin.
- Alertas clínicas: HbA1c > 7,5 % o glucosa > 180 mg/dL → notificación + correo a `email_destino_alertas`.
- Correo vía **Brevo SMTP** (`smtp-relay.brevo.com`) o API Brevo (`xkeysib-...`).
- Recuperación de contraseña envía código por correo si `email: true` en configuración.

---

## Configuración Brevo (administrador)

Ruta: **Gobierno → Configuración → Correo electrónico**

| Campo | Valor típico |
|-------|----------------|
| Habilitar envío | ON |
| Proveedor | SMTP genérico (clave `xsmtpsib-...`) o Brevo API (`xkeysib-...`) |
| Usuario SMTP | Email verificado en Brevo |
| Contraseña SMTP | Clave SMTP Brevo |
| Remitente | Mismo email verificado |
| Destino alertas | Email del médico/admin |

Botón **Enviar correo de prueba** valida la integración.

---

## API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/notificaciones/` | Lista notificaciones |
| GET | `/api/notificaciones/estadisticas` | Totales, no leídas, emails enviados |
| POST | `/api/notificaciones/evaluar` | Evalúa umbrales sobre registros clínicos |
| PATCH | `/api/notificaciones/{id}/leida` | Marcar leída |
| POST | `/api/configuracion/email/probar` | Prueba de correo |

---

## Fuera de alcance (iteración posterior)

- CU-O16 alertas churn comercial con ML de negocio.
- SMS / push móvil.
- Plantillas HTML avanzadas por tipo de alerta.
