<p align="center">
  <img src="https://raw.githubusercontent.com/marcogll/mg_data_storage/refs/heads/main/soul23/logo/soul23_logo.svg" width="110" alt="Soul23">
</p>

<h1 align="center">Bot Vanity</h1>

<p align="center">
  Bot automatizado para operaciones 🤖
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Docker-3a3a3a?style=flat-square&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/FastAPI-3a3a3a?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/OpenAI-3a3a3a?style=flat-square&logo=openai&logoColor=white" alt="OpenAI">
  <img src="https://img.shields.io/badge/PostgreSQL-3a3a3a?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Python-3a3a3a?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Telegram-3a3a3a?style=flat-square&logo=telegram&logoColor=white" alt="Telegram">
</p>

  Bot automatizado para operaciones 🤖
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Docker-3a3a3a?style=flat-square&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/FastAPI-3a3a3a?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/OpenAI-3a3a3a?style=flat-square&logo=openai&logoColor=white" alt="OpenAI">
  <img src="https://img.shields.io/badge/PostgreSQL-3a3a3a?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Python-3a3a3a?style=flat-square&logo=python&logoColor=white" alt="Python">
</p>

## Resumen

Sofía atiende mensajes de WhatsApp para Vanity Nail Salon. El sistema responde consultas, guía al agendamiento en Fresha, valida capturas y comprobantes, y prioriza la intervención humana cuando corresponde.

El comportamiento actual ya incorpora aprendizaje de chats reales en [whatsapp_interactions/messaging_selfimp.md](/home/marco/Work/code/bot_vanity/whatsapp_interactions/messaging_selfimp.md), con foco en:

- no reiniciar conversaciones avanzadas
- no pedir nombre ciegamente
- no responder encima de recepción humana
- no filtrar texto interno al usuario
- limitar la memoria conversacional a `24h`, o `48h` si existe booking/cita activa o reciente

## Estado actual

- Deduplicación de webhooks por `instance + remote_jid + session_id`
- Transcripción de audio antes del flujo principal
- Análisis estructurado de capturas de cita y comprobantes
- Cifrado at-rest de mensajes y nombres
- Protección básica contra prompt injection en texto y audio
- Sanitización final para impedir fuga de texto interno
- Modo test con allowlist, export JSON y purge automático por sesión
- Panel admin `/admin` con siembra inicial de `service_catalog` desde `docs/knowledge_base.md` y `docs/promos.md` cuando la tabla está vacía

## Estructura

```text
app/
  main.py                  webhook, orquestación, follow-ups, modo test
  knowledge_engine.py      system prompt + docs Markdown
  business_rules.py        reglas determinísticas
  models.py                interacciones, memoria, citas, webhook events
docs/
  system_prompt.md
  knowledge_base.md
  promos.md
  db.md
  evolution_api_latency_guide.md
whatsapp_interactions/
  messaging_selfimp.md
tests/
  test_business_rules.py
```

## Setup local

No instales dependencias con `pip` global. Usa `.venv`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Si no activas el virtualenv:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8001
```

## Variables de entorno

Parte de [`.env.example`](/home/marco/Work/code/bot_vanity/.env.example) y ajusta valores reales.

Variables críticas:

- `OPENAI_API_KEY`
- `AES_ENCRYPTION_KEY`
- `WEBHOOK_SECRET`
- `DATABASE_URL`
- `EVOLUTION_API_URL`
- `EVOLUTION_API_KEY`
- `EVOLUTION_INSTANCE_NAME`
- `BOOKING_URL`
- `PAYMENT_URL`

Variables del panel admin:

- `ADMIN_WEBUI_ENABLED=true`
- `ADMIN_BOOTSTRAP_USERNAME=admin`
- `ADMIN_BOOTSTRAP_PASSWORD=<password fuerte temporal>`
- `ADMIN_SESSION_SECRET=<secreto largo aleatorio>`
- `ADMIN_SESSION_MINUTES=120`
- `ADMIN_LOGIN_MAX_ATTEMPTS=5`
- `ADMIN_LOCKOUT_MINUTES=15`

Notas:

- `ADMIN_BOOTSTRAP_PASSWORD` solo se usa para sembrar el primer admin si no existe.
- `ADMIN_SESSION_SECRET` debe ser distinto a `WEBHOOK_SECRET`.
- el password se guarda hasheado en DB, no reversible
- en el primer login el panel obliga a rotar ese password temporal
- idealmente el panel debe ir detrás de `HTTPS` y una capa extra como VPN o allowlist de IP

Genera una llave Fernet válida:

```bash
.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Modo test

El modo test permite probar Sofía solo con ciertos teléfonos, mientras el resto queda para recepción humana.

Ejemplo:

```env
TEST_MODE_ENABLED=true
TEST_MODE_ALLOWED_NUMBERS=528448087770,528445949068,528441565066
TEST_MODE_EXPORT_WEBHOOK_URL=https://tu-endpoint.example.com/sofia-test-export
TEST_MODE_EXPORT_WEBHOOK_AUTH_HEADER=token_sofia
TEST_MODE_EXPORT_WEBHOOK_AUTH_VALUE=change-me
TEST_MODE_SESSION_MINUTES=15
```

Comportamiento:

- Sofía solo responde a los números listados en `TEST_MODE_ALLOWED_NUMBERS`
- los demás chats se ignoran desde el bot
- tras `TEST_MODE_SESSION_MINUTES` sin actividad, se exporta la sesión como JSON
- si el webhook responde bien, se purga historial, memoria y citas de ese chat

Payload exportado:

- `mode`
- `exported_at` y `exported_at_local`
- `whatsapp_id` y `phone_number`
- `push_name`
- `profile_summary`
- `service_interest`
- `history[]` con `timestamp`, `timestamp_local`, `role`, `content`
- `pending_booking`
- `completed_booking`

## Reglas conversacionales

Sofía no debe copiar la autoridad operativa de recepción humana. Su rol es:

- orientar
- cotizar
- redirigir a booking cuando aplica
- validar confirmación o comprobantes
- escalar o quedarse callada si una humana ya resolvió

El estilo objetivo viene de chats reales documentados en:

- [messaging_selfimp.md](/home/marco/Work/code/bot_vanity/whatsapp_interactions/messaging_selfimp.md)
- [docs/system_prompt.md](/home/marco/Work/code/bot_vanity/docs/system_prompt.md)
- [docs/conversation_flow.md](/home/marco/Work/code/bot_vanity/docs/conversation_flow.md)

## Diagrama conversacional

La lógica conversacional ya no debe sentirse como script lineal. La referencia formal por estados y escenarios está en:

- [docs/conversation_flow.md](/home/marco/Work/code/bot_vanity/docs/conversation_flow.md)

Resumen corto:

1. conversación nueva:
   pedir nombre y mencionar una sola vez que también acepta audios
2. intención ya declarada:
   conservar servicio/fecha y no reiniciar
3. si es para un tercero:
   reconocerlo y seguir natural
4. si dice `uñas`:
   primero acotar subtipo
5. si responde subtipo:
   luego preguntar retiro como aclaración natural
6. ya con suficiente contexto:
   orientar o mandar booking
7. si llega captura/comprobante:
   validar, no volver a onboarding
8. si ya respondió humana:
   no duplicar ni reabrir flujo

Escenarios que deben sentirse naturales:

- `quiero cita para uñas el lunes`
- `Marco Gallegos es para mi esposa`
- `uñas y pedicure`
- `te mando la captura`
- `se me cayó una uña`
- `ya me atendió recepción`

## Contexto y memoria

La memoria ya no se usa abierta indefinidamente.

- conversación general: contexto útil de `24h`
- booking o cita activa/reciente: hasta `48h`
- si no hay contexto activo, Sofía trata el mensaje como conversación nueva

Esto evita que retome temas viejos sin relación con el request actual.

## Seguridad y robustez

- cifrado Fernet para contenido sensible
- filtro anti prompt injection en texto y audios transcritos
- instrucciones defensivas en análisis de imágenes
- dedupe persistente de webhooks
- saneamiento de mensajes internos antes de enviar a WhatsApp
- rate limiting por usuario

## Comando administrativo

El trigger administrativo se configura por env:

```env
ADMIN_PHONE_NUMBER=528441026472
MEMORY_DELETE_TRIGGER=dipiridú
```

Comportamiento actual:

- solo admins autorizados pueden dispararlo
- pide confirmación
- borra solo el chat actual, no toda la base

Si luego necesitas más de un admin, también existe:

```env
ADMIN_PHONE_NUMBERS=528441026472,528445047771
```

## Docker

Construcción local:

```bash
docker build -t marcogll/vanessa-bot-vanity:latest .
```

Stack completo:

```bash
docker compose up -d --build
```

Servicios:

- `vanessa-app`
- `vanessa-db`
- `evolution-api`
- `evolution-db`
- `evolution-redis`

Logs:

```bash
docker compose logs -f vanessa-app evolution-api
```

## Configuración de webhook en Evolution

El webhook de Evolution debe apuntar al dominio de `vanessa-app`, no al dominio de `evolution-api`.

Con una app publicada en Coolify, la forma correcta es:

```text
https://<dominio-vanessa-app>/webhook?apiKey=<WEBHOOK_SECRET_REAL>
```

Ejemplo:

```text
https://y1gwctkjhcv59yt3d7encn7z.soul23.cloud/webhook?apiKey=tu_secret_real
```

También se acepta:

```text
https://<dominio-vanessa-app>/webhook/messages-upsert?apiKey=<WEBHOOK_SECRET_REAL>
```

Notas:

- `<WEBHOOK_SECRET_REAL>` es el valor literal de `WEBHOOK_SECRET`, sin `< >`
- el dominio de `evolution-api` no va aquí
- `WEBHOOK_SECRET` y el `apiKey` configurado en Evolution deben coincidir exactamente

## Pruebas CLI

Hay dos pruebas distintas: envío directo por Evolution y prueba del webhook de Sofía.

### 1. Envío directo por Evolution

Esto manda un WhatsApp saliente y valida que la instancia de Evolution existe y puede enviar.

```bash
curl -X POST "https://<dominio-evolution>/message/sendText/<instance_name>" \
  -H "apikey: <EVOLUTION_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "528441026472",
    "text": "Prueba CLI desde Evolution"
  }'
```

Ejemplo real:

```bash
curl -X POST "https://ed3tlhtejal71x0be1zgjkkr.soul23.cloud/message/sendText/sofia_prod" \
  -H "apikey: qiY8h1TlRYxFoXzQ9rOoWd" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "528441026472",
    "text": "Prueba CLI desde Evolution"
  }'
```

Si responde:

```json
{"status":"PENDING", ...}
```

entonces la instancia existe y aceptó el envío.

Si responde:

```json
{"status":404,"error":"Not Found","response":{"message":["The \"sofia\" instance does not exist"]}}
```

entonces el nombre de instancia es incorrecto.

### 2. Prueba del webhook de Sofía

Esto simula un mensaje entrante como si Evolution lo enviara al backend.

```bash
curl -X POST "https://<dominio-vanessa-app>/webhook?apiKey=<WEBHOOK_SECRET_REAL>" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "instance": "<instance_name>",
    "data": {
      "key": {
        "remoteJid": "5218441026472@s.whatsapp.net",
        "fromMe": false,
        "id": "cli-test-001"
      },
      "pushName": "Marco Test",
      "message": {
        "conversation": "Hola, esta es una prueba del webhook"
      }
    }
  }'
```

Esperado:

- respuesta HTTP con `{"message":"accepted"}` o `{"message":"duplicate"}`
- Sofía intentará responder por WhatsApp a través de Evolution

### 3. End-to-end con `.env.production`

Si ya tienes `.env.production` correcto:

```bash
source .env.production

curl -X POST "${EVOLUTION_SERVER_URL}/message/sendText/${EVOLUTION_INSTANCE_NAME}" \
  -H "apikey: ${EVOLUTION_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "528441026472",
    "text": "Prueba CLI desde Evolution"
  }'
```

Y para probar el webhook:

```bash
source .env.production

curl -X POST "${SERVICE_URL_VANESSA_APP}/webhook?apiKey=${WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "instance": "sofia_prod",
    "data": {
      "key": {
        "remoteJid": "5218441026472@s.whatsapp.net",
        "fromMe": false,
        "id": "cli-test-002"
      },
      "pushName": "Marco Test",
      "message": {
        "conversation": "Hola, prueba end to end"
      }
    }
  }'
```

## Verificación de producción

Healthcheck:

```bash
curl http://127.0.0.1:8001/health
```

Validación rápida de OpenAI dentro del contenedor:

```bash
APP=$(docker ps --filter "ancestor=marcogll/vanessa-bot-vanity:latest" --format "{{.Names}}" | head -n1)
docker exec "$APP" python -c 'from app.config import get_settings; from openai import OpenAI; s=get_settings(); print("model:", s.llm_model); print("key_prefix:", s.openai_api_key[:7]); print("key_len:", len(s.openai_api_key)); r=OpenAI(api_key=s.openai_api_key).chat.completions.create(model=s.llm_model, messages=[{"role":"user","content":"Responde solo OK"}], max_tokens=5); print("reply:", r.choices[0].message.content)'
```

## Documentos clave

- [PRD.md](/home/marco/Work/code/bot_vanity/PRD.md)
- [TASKS.md](/home/marco/Work/code/bot_vanity/TASKS.md)
- [CHANGELOG.md](/home/marco/Work/code/bot_vanity/CHANGELOG.md)
- [docs/evolution_api_latency_guide.md](/home/marco/Work/code/bot_vanity/docs/evolution_api_latency_guide.md)

## Estado de pruebas

Suite focalizada actual:

```text
78 passed
```


