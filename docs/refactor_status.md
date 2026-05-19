# Estado del Refactor Sofia Role Runtime

Fecha de referencia: 2026-05-18

## Objetivo del branch

Este branch convierte el bot actual de Vanity en una base más modular para un runtime conversacional replicable. El cambio se está haciendo por cortes pequeños para conservar comportamiento productivo mientras se agregan modelos, políticas, roles, shadow mode y flujo estructurado.

## Estado actual

### Último avance

- Fases 1-10 del plan de refactor completadas.
- `ConversationClassifier` creado como motor de clasificación determinística antes del LLM.
- `ResponsePlanner` creado para generar planes de respuesta basados en contexto y decisión.
- `BusinessPolicyPack` agregado a la configuración de tenant con políticas de booking, escalación y estilo.
- `TenantKnowledgeEngine` creado para cargar conocimiento por tenant con placeholders dinámicos.
- `BotRegistry` implementado para resolver y cachear configuraciones de tenant.
- Tool layer creado con 6 tools implementados y precondiciones.
- `app/main.py` reducido extrayendo: admin commands, reply formatter, test export, transcription, history helpers, webhook processor.
- Validación de migración creada con script y tests de compatibilidad.
- Guía de migración operativa documentada en `docs/migration_guide.md`.
- Suite completa: 343 tests passing (82 nuevos tests de integración y migración).

### Fases Completadas

#### Fase 1: Diagnóstico y Separación de Responsabilidades ✅

- Tarea 1: Mapear responsabilidades actuales → Matriz en `docs/rule_classification_matrix.md`
- Tarea 2: Separar reglas duras, políticas y estilo → 33 reglas clasificadas en 5 categorías
- Tarea 3: Definir contrato interno de conversación → Modelos en `app/conversation/models.py`

#### Fase 2: Modelo Replicable de Negocio ✅

- Tarea 4: `BusinessProfile` con configuración completa en `app/tenants/models.py`
- Tarea 5: `ServiceCatalog` como fuente única (ya existía en DB, sincronizado desde Fresha)
- Tarea 6: `BusinessPolicyPack` con BookingPolicy, EscalationPolicy, StylePolicy

#### Fase 3: Sistema de Roles Staff ✅

- Tarea 7: `StaffRoleProfile` definido en `app/tenants/models.py`
- Tarea 8: `staff_1` modelado en `tenants/vanity/business.json`
- Tarea 9: `staff_2_manager` modelado en `tenants/vanity/business.json`
- Tarea 10: `RoleBlender` implementado en `app/roles/blender.py`

#### Fase 4: Motor de Decisión Antes del LLM ✅

- Tarea 11: `ConversationClassifier` en `app/conversation/classifier.py`
  - Clasifica intención, estado, urgencia, risk flags y missing fields
  - 28 tests cubriendo todos los casos
- Tarea 12: `PolicyEngine` en `app/conversation/policy_engine.py` (ya existía, mejorado)
- Tarea 13: `ResponsePlanner` en `app/conversation/response_planner.py`
  - Genera planes de respuesta basados en estado e intención
  - 16 tests cubriendo todos los estados

#### Fase 5: Prompt Modular ✅

- Tarea 14: Documentos divididos por tenant en `tenants/vanity/knowledge/`
  - `identity.md` - Identidad del bot, límites, estilo
  - `policies.md` - Políticas de booking, escalación, autoridad
  - `booking_flow.md` - Flujo estructurado de booking
  - `roles.md` - Perfiles de staff y mezcla de roles
  - `escalation.md` - Políticas de escalación humana
- Tarea 15: `TenantKnowledgeEngine` en `app/knowledge/engine.py`
  - Carga conocimiento por tenant
  - Reemplaza placeholders con configuración real
  - 14 tests cubriendo carga y generación de prompt
- Tarea 16: PromptBuilder con contrato system = identidad + políticas + roles

#### Fase 6: Multi-Negocio ✅

- Tarea 17: `tenant_id` introducido formalmente
- Tarea 18: Modelos de base de datos ya tienen `tenant_id` (implementado anteriormente)
- Tarea 19: `BotRegistry` en `app/bots/registry.py`
  - Resuelve tenant por ID, instancia o número
  - Cachea configuraciones
  - Expone perfil de bot
  - 6 tests cubriendo resolución y cache
- Tarea 20: Canal WhatsApp separado en `app/channels/whatsapp.py` (ya implementado)

#### Fase 7: Capacidades y Herramientas ✅

- Tarea 21: Acciones permitidas definidas en `ToolAction` enum
- Tarea 22: Tool layer en `app/tools/layer.py`
  - Cada acción tiene: precondiciones, ejecución, resultado, mensaje sugerido
  - Tools implementados: SendBookingLink, RequestMissingDetail, QuoteService, PauseBot, NotifyHuman, ScheduleFollowup
  - 17 tests cubriendo todos los tools
- Tarea 23: Límites de autoridad definidos en `BusinessPolicyPack.bot_authority_limits`

#### Fase 10: Migración Operativa ✅

- Tarea 34: Compatibilidad Vanity mantenida
  - Tenant vanity configurado en `tenants/vanity/business.json`
  - Documentos de conocimiento en `tenants/vanity/knowledge/`
  - 5 tests de compatibilidad en `tests/test_migration_validation.py`
- Tarea 35: Sistema de flags implementado
  - `BOT_RUNTIME_V2_ENABLED` - Control principal de V2
  - `BOT_RUNTIME_V2_SHADOW_MODE` - Shadow mode para evaluación sin responder
  - `BOT_RUNTIME_V2_ALLOWED_NUMBERS` - Allowlist para activación controlada
  - `ROLE_BLEND_ENABLED` - Control de mezcla de roles
  - `TENANT_CONFIG_PATH` y `DEFAULT_TENANT_ID` - Configuración de tenant
  - 3 tests de sistema de flags
- Tarea 36: Comparación V1 vs V2 implementada
  - `compare_runtime_to_reply()` en `app/bots/runtime.py`
  - Script de validación en `scripts/validate_migration.py`
  - 5 tests de comparación en `tests/test_migration_validation.py`
  - 12 escenarios de validación cubiertos
- Tarea 37: Activación por allowlist implementada
  - `_runtime_v2_is_allowed_number()` en `app/main.py`
  - `_should_runtime_v2_take_control()` en `app/main.py`
  - Documentación en `docs/migration_guide.md`

### Implementado (anterior)

- Modelos de tenant y roles en `app/tenants/models.py`.
- Loader de configuración por tenant en `app/tenants/loader.py`.
- Configuración versionada de Vanity en `tenants/vanity/business.json`.
- `RoleBlender` en `app/roles/blender.py`.
- Contratos de conversación en `app/conversation/models.py`.
- `PolicyEngine` mínimo en `app/conversation/policy_engine.py`.
- Runtime V2 en `app/bots/runtime.py`.
- Shadow mode V2 desde `app/main.py`, sin alterar la respuesta que se envía al cliente.
- Derivación de estado extraída a `app/conversation/state.py`.
- Buffer conversacional extraído a `app/conversation/memory.py`.
- Flujo local de booking extraído a `app/conversation/booking_flow.py`.
- Armado de prompt extraído a `app/conversation/prompt_builder.py`.
- Parsing puro de canal WhatsApp extraído a `app/channels/whatsapp.py`.
- `EvolutionWebhookPayload` movido a `app/channels/whatsapp.py`.
- Notificaciones de escalación extraídas a `app/tools/notifications.py`.
- Follow-up y reglas operativas de booking extraídas a `app/tools/booking.py`.
- Persistencia de pagos y finalización de citas extraída a `app/tools/payments.py`.
- Modelos y mensajes de capturas/comprobantes extraídos a `app/tools/proofs.py`.
- Adaptador OpenAI de análisis visual extraído a `app/tools/vision.py`.
- `tenant_id` persistido en historial, memoria, citas y eventos webhook.
- Comparación V1/V2 registrada en shadow mode con estado, intención, acción y alineación.
- Runtime V2 puede tomar control limitado con allowlist para decisiones determinísticas.
- Comando admin `dipirdu -rf`/`dipiridú -rf` agregado con confirmación exacta para borrar toda la base.
- Generador principal consolidado como `generate_assistant_reply`.
- Follow-up de booking configurado a 15 minutos por defecto.
- Notificación de escalación humana a `ADMIN_PHONE_NUMBER` y `ADMIN_PHONE_NUMBERS`.
- README y `.env.example` actualizados para este branch.

### Aún pendiente

- Ninguna - todas las fases del plan de refactor están completadas.

### Cobertura

La suite completa validada en este branch:

```text
343 passed, 4 warnings
```

Comando:

```bash
env OPENAI_API_KEY=test DATABASE_URL=postgresql+asyncpg://user:pass@localhost/test AES_ENCRYPTION_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= WEBHOOK_SECRET=test .venv/bin/python -m pytest
```
