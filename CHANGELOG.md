# Changelog

## 2026-05-18

### Refactor Sofia Role Runtime - Fases 5-10 Completadas

#### Fase 5: Prompt Modular
- Documentos de conocimiento divididos por tenant en `tenants/vanity/knowledge/`
  - `identity.md`, `policies.md`, `booking_flow.md`, `roles.md`, `escalation.md`
- `TenantKnowledgeEngine` en `app/knowledge/engine.py`
  - Carga conocimiento por tenant con placeholders dinámicos
  - Reemplaza URLs, nombres, políticas y configuración en tiempo de ejecución
- PromptBuilder con contrato system = identidad + políticas + roles

#### Fase 6: Multi-Negocio
- `BotRegistry` en `app/bots/registry.py`
  - Resuelve tenant por ID, instancia o número de teléfono
  - Cachea configuraciones para evitar recargas
  - Expone perfil de bot para uso en runtime
- `tenant_id` formalmente introducido en todo el sistema
- Canal WhatsApp completamente separado en `app/channels/whatsapp.py`

#### Fase 7: Capacidades y Herramientas
- Tool layer en `app/tools/layer.py`
  - `ToolAction` enum con 8 acciones permitidas
  - Tools implementados: SendBookingLink, RequestMissingDetail, QuoteService, PauseBot, NotifyHuman, ScheduleFollowup
  - Cada tool tiene precondiciones, ejecución, resultado estructurado y mensaje sugerido
- Límites de autoridad definidos en `BusinessPolicyPack.bot_authority_limits`

#### Fase 8: Refactor Incremental
- `app/main.py` reducido con módulos extraídos:
  - `app/admin/commands.py` - Comandos administrativos (memory/db delete, pause, shutdown)
  - `app/reply/formatter.py` - Formateo y sanitización de respuestas
  - `app/tools/test_export.py` - Exportación de sesiones de test
  - `app/tools/transcription.py` - Transcripción de audio
  - `app/conversation/history.py` - Helpers de historial y contexto
  - `app/channels/webhook_processor.py` - Procesamiento de webhooks

#### Fase 9: Testing
- 82 nuevos tests de integración y migración
- `tests/test_role_runtime_integration.py` - Tests de roles y runtime (20 tests)
- `tests/test_multi_tenant.py` - Tests de aislamiento multi-tenant (7 tests)
- `tests/test_authority_limits.py` - Tests de límites de autoridad (16 tests)
- `tests/test_real_chat_scenarios.py` - Escenarios de chat reales (21 tests)
- `tests/test_migration_validation.py` - Tests de validación de migración (15 tests)
- Suite completa: 343 tests passing

#### Fase 10: Migración Operativa
- Tenant vanity completamente configurado con políticas y conocimiento
- Sistema de flags implementado:
  - `BOT_RUNTIME_V2_ENABLED` - Control principal de V2
  - `BOT_RUNTIME_V2_SHADOW_MODE` - Shadow mode para evaluación sin responder
  - `BOT_RUNTIME_V2_ALLOWED_NUMBERS` - Allowlist para activación controlada
  - `ROLE_BLEND_ENABLED` - Control de mezcla de roles
- Comparación V1 vs V2 implementada con `compare_runtime_to_reply()`
- Script de validación en `scripts/validate_migration.py`
- Guía de migración operativa en `docs/migration_guide.md`

#### Documentación
- `docs/migration_guide.md` - Guía completa de migración operativa
- `docs/rule_classification_matrix.md` - Matriz de clasificación de reglas (33 reglas en 5 categorías)
- `docs/refactor_status.md` - Estado actualizado del refactor
- `docs/sofia_role_runtime_refactor_plan.md` - Plan maestro actualizado
- `README.md` - Estructura y estado actualizados
- `CHANGELOG.md` - Este archivo

### Validación

- Suite completa: `343 passed, 4 warnings`

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
- Se extrajo persistencia de pagos y finalización de citas a `app/tools/payments.py`.
- Se extrajeron modelos y mensajes de capturas/comprobantes a `app/tools/proofs.py`.
- Se extrajo el adaptador OpenAI de análisis visual a `app/tools/vision.py`.
- Se agregó `tenant_id` a historial, memoria, citas y eventos webhook, con migración idempotente en `init_db`.
- Se agregó comparación auditada entre respuesta V1 y decisión Runtime V2 en shadow mode.
- Se habilitó control limitado de Runtime V2 con allowlist para decisiones determinísticas.
- Se agregó comando admin `dipirdu -rf`/`dipiridú -rf` con confirmación exacta para borrar toda la base.
- Se bloqueó la lógica que podía inventar disponibilidad; Sofía ahora guía a Fresha y no pide día/hora ni confirma espacios.
- Se optimizó el webhook para responder rápido a Evolution y evitar reintentos por 504 cuando la DB o el procesamiento tardan.
- Se movió el parseo completo del webhook al background; el ACK ahora solo lee bytes, encola y responde.
- Se renombró y consolidó el generador principal como `generate_assistant_reply`.
- Se eliminaron wrappers temporales de `main.py` para helpers ya extraídos a tools.

### Booking y escalación

- El flujo estructurado pregunta servicio, subtipo, retiro y diseño/técnica antes de mandar booking.
- El cierre de booking incluye app/cuenta Fresha antes de mandar booking y usa copy natural tipo `vas a reservar: ...`.
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

- Suite completa: `153 passed, 4 warnings`.

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
