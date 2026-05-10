# Operación del Branch Runtime V2

## Variables por ambiente

### Produccion conservadora

```env
BOT_RUNTIME_V2_ENABLED=false
BOT_RUNTIME_V2_SHADOW_MODE=false
BOT_RUNTIME_V2_ALLOWED_NUMBERS=
ROLE_BLEND_ENABLED=false
```

Con esta configuración, el bot opera con el flujo V1 más las reglas locales ya integradas en este branch.

### Shadow mode

```env
BOT_RUNTIME_V2_ENABLED=true
BOT_RUNTIME_V2_SHADOW_MODE=true
ROLE_BLEND_ENABLED=true
```

Usar para observar decisiones V2 sin cambiar respuestas al cliente.

### Control limitado con allowlist

```env
BOT_RUNTIME_V2_ENABLED=true
BOT_RUNTIME_V2_SHADOW_MODE=false
BOT_RUNTIME_V2_ALLOWED_NUMBERS=528448087770,528445949068
ROLE_BLEND_ENABLED=true
```

Con esta configuración V2 solo toma control en números permitidos, admins o teléfonos de test mode. El control está limitado a decisiones determinísticas: silencio, handover y respuestas estructuradas. Si V2 decide `ask_llm`, el flujo sigue usando V1.

### Test mode

```env
TEST_MODE_ENABLED=true
TEST_MODE_ALLOWED_NUMBERS=528448087770,528445949068
TEST_MODE_SESSION_MINUTES=15
```

Usar para limitar a qué teléfonos responde Sofía durante pruebas.

## Escalaciones

Configura admins:

```env
ADMIN_PHONE_NUMBER=528441026472
ADMIN_PHONE_NUMBERS=528441026472,528445047771
```

Cuando hay escalación, Sofía enviará una notificación por WhatsApp a esos números si `EVOLUTION_API_URL`, `EVOLUTION_API_KEY` y `EVOLUTION_INSTANCE_NAME` están configurados.

## Follow-up de booking

```env
FOLLOW_UP_DELAY_SECONDS=900
```

El follow-up pregunta si la clienta pudo elegir horario. No se envía si:

- ya existe cita completada.
- ya existe captura/comprobante pendiente.
- el contexto reciente indica que la clienta ya agendó.
- follow-ups están pausados desde el panel admin.

## Panel admin

El panel admin sigue disponible en `/admin` si:

```env
ADMIN_WEBUI_ENABLED=true
```

El primer usuario se siembra con:

```env
ADMIN_BOOTSTRAP_USERNAME=admin
ADMIN_BOOTSTRAP_PASSWORD=<password temporal fuerte>
ADMIN_SESSION_SECRET=<secreto largo>
```

## Docker compose

`docker compose` requiere variables obligatorias antes de interpolar el stack, especialmente:

- `OPENAI_API_KEY`
- `AES_ENCRYPTION_KEY`
- `WEBHOOK_SECRET`
- `DATABASE_URL`
- credenciales de Postgres declaradas en `.env.example`

Si no existe `.env` o `.env.production`, `docker compose ps` y `docker compose up` fallarán antes de crear servicios.

## Logs útiles

Buscar:

- `Runtime V2 shadow:`
- `Human handover requested`
- `Human handover notification failed`
- `Reply sent: remote_jid=... flow=local_booking_flow`
- `Follow-up sent`
- `Ignoring outbound webhook already matched to bot reply`

## Rollback operativo

Para volver al comportamiento más conservador:

```env
BOT_RUNTIME_V2_ENABLED=false
BOT_RUNTIME_V2_SHADOW_MODE=false
ROLE_BLEND_ENABLED=false
```

Si además se quiere evitar follow-ups, pausarlos desde `/admin`. No uses un valor artificial de `FOLLOW_UP_DELAY_SECONDS` como mecanismo de apagado.
