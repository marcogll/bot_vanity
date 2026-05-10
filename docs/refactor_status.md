# Estado del Refactor Sofia Role Runtime

Fecha de referencia: 2026-05-09

## Objetivo del branch

Este branch convierte el bot actual de Vanity en una base más modular para un runtime conversacional replicable. El cambio se está haciendo por cortes pequeños para conservar comportamiento productivo mientras se agregan modelos, políticas, roles, shadow mode y flujo estructurado.

## Estado actual

### Último avance

- `main.py` quedó más cerca de ser orquestador: estado, buffer, prompt, canal WhatsApp, policy engine y booking flow ya tienen módulos propios.
- La respuesta productiva sigue protegida: Runtime V2 corre en shadow mode y V1 sigue enviando el mensaje real.
- El sistema ya puede probarse con suite local, smoke test de `/health` y payloads webhook documentados en `docs/testing_runtime_v2.md`.

### Implementado

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

- Ampliar Runtime V2 para generación LLM completa si se decide que V2 tome control de conversaciones abiertas.
- Evaluar migración formal con Alembic si el esquema sigue creciendo.

### Último corte completado

1. ✅ Mover notificaciones de escalación a `app/tools/notifications.py`.
2. ✅ Mover scheduling/follow-up de booking a `app/tools/booking.py`.
3. ✅ Mover persistencia de pagos/finalización de citas a `app/tools/payments.py`.
4. ✅ Mover modelos/mensajes de capturas y pagos a `app/tools/proofs.py`.
5. ✅ Mover prompts/adaptador OpenAI de análisis visual a `app/tools/vision.py`.
6. ✅ Persistir `tenant_id` en modelos de base de datos y migración idempotente.
7. ✅ Comparar respuesta V1 vs decisión/plan V2 en shadow mode.
8. ✅ Activar Runtime V2 fuera de shadow mode con allowlist para decisiones determinísticas.
9. ✅ Eliminar wrappers temporales de `main.py` que ya no tenían dependencias internas.
10. ✅ Correr suite completa y smoke test `/health`.

### Siguiente corte recomendado

1. Ampliar control Runtime V2 para generación LLM cuando el plan V2 ya cubra prompts completos.
2. Evaluar migración formal con Alembic si el esquema empieza a crecer.
3. Migrar `startup/shutdown` de FastAPI a lifespan para eliminar warnings.

## Flags relevantes

```env
BOT_RUNTIME_V2_ENABLED=false
BOT_RUNTIME_V2_SHADOW_MODE=false
BOT_RUNTIME_V2_ALLOWED_NUMBERS=
ROLE_BLEND_ENABLED=false
TENANT_CONFIG_PATH=tenants
DEFAULT_TENANT_ID=vanity
FOLLOW_UP_DELAY_SECONDS=900
ADMIN_PHONE_NUMBER=528441026472
ADMIN_PHONE_NUMBERS=528441026472,528445047771
```

## Comportamiento de shadow mode

Con `BOT_RUNTIME_V2_ENABLED=true` y `BOT_RUNTIME_V2_SHADOW_MODE=true`:

- V1 sigue respondiendo al cliente.
- V2 evalúa contexto, intención, estado, política, plan y roles.
- V2 no envía mensajes.
- El resultado se registra en logs con el prefijo `Runtime V2 shadow:`.
- Si `BOT_RUNTIME_V2_SHADOW_MODE=false`, V2 solo toma control para números en `BOT_RUNTIME_V2_ALLOWED_NUMBERS`, admins o test mode, y únicamente en decisiones determinísticas.

## Flujo estructurado de booking

El flujo local antes del LLM cubre:

1. presentación inicial y solicitud de nombre.
2. detección de servicio.
3. para uñas/manicure/pedicure, pregunta por retiro.
4. después de retiro, pregunta por tono liso, diseño o técnica.
5. pregunta si ya tiene app/cuenta Fresha; si no, manda links de app y espera confirmación.
6. cuando ya tiene app/cuenta, envía liga de booking con resumen `vas a reservar: ...`.
7. programa follow-up después de 15 minutos si no hay captura/comprobante.
8. no consulta ni confirma disponibilidad; guía a Fresha para elegir horario real.

## Escalación humana

Si el usuario pide hablar con una persona o el mensaje contiene señales de queja fuerte:

- Sofía responde que pausará el flujo automático.
- Se persiste la interacción.
- Se agenda notificación WhatsApp a los admins configurados.
- La conversación evita reabrir el flujo si recepción humana intervino.

## Cobertura

La suite completa validada en este branch:

```text
153 passed, 4 warnings
```

Comando:

```bash
env OPENAI_API_KEY=test DATABASE_URL=postgresql+asyncpg://user:pass@localhost/test AES_ENCRYPTION_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= WEBHOOK_SECRET=test .venv/bin/python -m pytest
```
