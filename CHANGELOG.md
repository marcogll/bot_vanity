# Changelog

## 2026-05-09

### Refactor Sofia Role Runtime

- Se agregaron modelos de tenant, negocio, bot y roles.
- Se creó configuración versionada para `vanity` en `tenants/vanity/business.json`.
- Se agregó `RoleBlender` con pesos por estado conversacional.
- Se agregaron contratos puros de conversación, decisiones, acciones y planes.
- Se agregó `PolicyEngine` mínimo para silencio, handover, prompt injection, dato faltante y fallback a LLM.
- Se agregó `BotRuntimeV2` con shadow mode detrás de flags.
- Se extrajo derivación de estado a `app/conversation/state.py`.
- Se extrajo buffer conversacional temporal a `app/conversation/memory.py`.
- Se agregó flujo local de booking en `app/conversation/booking_flow.py`.
- Se extrajo parsing puro de canal WhatsApp a `app/channels/whatsapp.py`.
- Se movió `EvolutionWebhookPayload` al adaptador `app/channels/whatsapp.py`.
- Se extrajeron notificaciones de escalación a `app/tools/notifications.py`.
- Se extrajeron follow-ups y reglas operativas de booking a `app/tools/booking.py`.
- Se extrajeron modelos y mensajes de capturas/comprobantes a `app/tools/proofs.py`.
- Se extrajo el adaptador OpenAI de análisis visual a `app/tools/vision.py`.
- Se renombró el generador principal a `generate_assistant_reply`; `_ask_vanessa` queda como wrapper temporal.

### Booking y escalación

- El flujo estructurado pregunta servicio, subtipo, retiro y diseño/técnica antes de mandar booking.
- El cierre de booking incluye links de app iOS/Android, liga de booking y resumen `vas a agendar: ...`.
- El follow-up de booking queda en 15 minutos por defecto (`FOLLOW_UP_DELAY_SECONDS=900`).
- Las escalaciones humanas notifican por WhatsApp a `ADMIN_PHONE_NUMBER` y `ADMIN_PHONE_NUMBERS`.

### Documentación

- Se actualizó `README.md` para el estado del branch.
- Se actualizó `.env.example` con flags V2, admins múltiples y follow-up de 15 minutos.
- Se agregó `docs/refactor_status.md`.
- Se agregó `docs/testing_runtime_v2.md`.
- Se agregó `docs/operations_runtime_v2.md`.
- Se actualizó `docs/conversation_flow.md`.

### Validación

- Suite completa: `137 passed, 4 warnings`.

## 2026-05-01

### Conversación de Sofía

- Se integró `whatsapp_interactions/messaging_selfimp.md` a la base documental del prompt.
- Se ajustó el prompt del sistema para que Sofía replique el estilo de `staff1` sin fingir capacidad de agendar manualmente.
- Se agregaron guardas para no pedir nombre cuando la conversación ya llega avanzada.
- Se redujo el follow-up genérico de booking cuando ya existe evidencia de cita o comprobante.
- Se agregó estado conversacional derivado para mejorar contexto y estabilidad.

### Seguridad y robustez

- Se reforzó la detección de prompt injection con más patrones y normalización de texto.
- Se bloquea prompt injection también después de transcribir audios.
- Las imágenes de comprobantes y capturas ya no se mandan al LLM general como contexto visual libre.
- El análisis estructurado de imágenes ahora incluye instrucciones explícitas para ignorar prompts embebidos.
- La intervención manual del equipo ya no inyecta su texto completo al historial del modelo; se usa un marcador seguro.
- El comando `sender/debug sender` quedó restringido a administración.
- El borrado administrativo `dipiridú` ya no elimina toda la base; ahora se limita al chat actual.
- Se dejó deduplicación persistente de webhooks mediante `WebhookEvent`.
- Se agregó una comprobación persistente para distinguir ecos recientes del bot frente a mensajes manuales salientes.
- Ya no se purga todo el historial de un cliente por datos cifrados ilegibles; solo se limpia lo necesario.

### Operación

- Se creó `docs/evolution_api_latency_guide.md` con recomendaciones para reducir latencia y ruido en Evolution API.
- `.gitignore` ahora excluye los chats de `whatsapp_interactions` pero conserva `whatsapp_interactions/messaging_selfimp.md`.

### Validación

- Suite focalizada: `54 passed` en `tests/test_business_rules.py`.
