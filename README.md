# Sofía Bot Vanity

Backend FastAPI para procesar webhooks de Evolution API y responder como Sofía,
asistente virtual de Vanity Nail Salon.

## Estado actual

- Sofía se presenta en la primera interacción y pide el nombre del cliente antes de continuar.
- El webhook deduplica eventos repetidos de Evolution usando el ID del mensaje para evitar respuestas dobles.
- Evolution corre con `evoapicloud/evolution-api:v2.3.7` para soporte actualizado de `@lid` y mapeo PN/LID.

## Setup local en Arch/Omarchy

No instales dependencias con `pip` global. Arch marca Python como entorno
administrado externamente, por lo que debes usar un virtualenv del proyecto:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Si no activas el virtualenv, ejecuta los binarios directamente:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

## Variables de entorno

Crea un `.env` basado en `.env.example`.

Modelo recomendado:

```env
LLM_MODEL=gpt-4o
AUDIO_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
```

`OPENAI_API_KEY` debe ser la llave completa de OpenAI. Si queda truncada, por ejemplo
`sk-proj-`, Sofía no podrá usar la knowledge base ni promociones y caerá al fallback
técnico.

Genera una clave válida para cifrado:

```bash
.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Coloca el resultado en `AES_ENCRYPTION_KEY`.

## Ejecutar

Levanta PostgreSQL local:

```bash
docker compose up -d vanessa-db
```

Con el `.env` configurado:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8001
```

Healthcheck:

```bash
curl http://127.0.0.1:8001/health
```

## Docker

Para construir la imagen de Sofía:

```bash
docker build -t <docker-user>/vanessa-bot-vanity:latest .
```

Para publicarla en Docker Hub:

```bash
docker push <docker-user>/vanessa-bot-vanity:latest
```

Para levantar el stack completo en el VPS:

```bash
docker compose up -d --build
```

El stack levanta:

- `vanessa-app`: backend FastAPI.
- `vanessa-db`: PostgreSQL de Sofía.
- `evolution-api`: instancia de Evolution API v2.3.7.
- `evolution-db`: PostgreSQL de Evolution.
- `evolution-redis`: cache de Evolution.

La app queda publicada en:

```text
http://127.0.0.1:8001
```

Evolution queda disponible dentro de la red Docker en:

```text
http://evolution-api:8080
```

En producción configura `EVOLUTION_SERVER_URL` con el dominio público de Evolution,
por ejemplo `https://evo.tu-dominio.com`, y usa el mismo `EVOLUTION_API_KEY` para
autenticar llamadas desde Sofía hacia Evolution.

Para ver logs:

```bash
docker compose logs -f vanessa-app evolution-api
```

En Coolify los contenedores tienen nombres generados. Para ubicar la app:

```bash
APP=$(docker ps --filter "ancestor=marcogll/vanessa-bot-vanity:latest" --format "{{.Names}}" | head -n1)
echo "$APP"
docker logs -f "$APP"
```

## Verificación OpenAI En Producción

Después de crear o actualizar variables en Coolify, valida que el contenedor tenga
la llave completa y pueda llamar a OpenAI:

```bash
APP=$(docker ps --filter "ancestor=marcogll/vanessa-bot-vanity:latest" --format "{{.Names}}" | head -n1)

docker exec "$APP" python -c 'from app.config import get_settings; from openai import OpenAI; s=get_settings(); print("model:", s.llm_model); print("key_prefix:", s.openai_api_key[:7]); print("key_len:", len(s.openai_api_key)); r=OpenAI(api_key=s.openai_api_key).chat.completions.create(model=s.llm_model, messages=[{"role":"user","content":"Responde solo OK"}], max_tokens=5); print("reply:", r.choices[0].message.content)'
```

Resultado esperado:

```text
model: gpt-4o
key_prefix: sk-proj
key_len: <mucho mayor que 8>
reply: OK
```

Si `key_len` es `8` y el error dice `Incorrect API key provided: sk-proj-`,
la variable `OPENAI_API_KEY` está incompleta en Coolify. Corrige la variable,
redeploya y repite la prueba.

Para confirmar que la imagen tiene el código reciente:

```bash
docker exec "$APP" python -c 'import inspect, app.main as m; print("has_local_recovery:", hasattr(m, "_local_recovery_reply")); print("image_high:", "\"detail\": \"high\"" in inspect.getsource(m._build_user_content)); print("greeting:", m.INITIAL_GREETING_REPLY)'
```

## Comando De Borrado Global

`dipiridú` es un comando administrativo raro a propósito. Cuando Sofía recibe
exactamente esa palabra, pide confirmación. Si se responde `sí`, borra toda la
base de memoria e historial:

- todas las filas de `interacciones`;
- todas las filas de `sesiones_memoria`.

No borra solo la conversación del usuario que lo envió. La confirmación existe
para evitar borrados accidentales.

Solo el número configurado en `ADMIN_PHONE_NUMBER` puede iniciar o confirmar este
comando. Usa el número en formato dígitos, sin `+`, espacios ni guiones.

```env
ADMIN_PHONE_NUMBER=5218440000000
```

## Audios De WhatsApp

Si Evolution envía audio con `base64`, Sofía lo transcribe antes de procesarlo.
La transcripción se convierte en el mensaje del usuario y sigue el mismo flujo de
knowledge base, promociones, precios y agendamiento.

Modelo por defecto:

```env
AUDIO_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
```

Evolution debe mantener habilitado `WEBHOOK_GLOBAL_WEBHOOK_BASE64=true` para que
los audios lleguen con contenido transcribible.

## Tracking De Citas

Sofía mantiene dos tablas operativas para seguimiento de reservas:

- `citas_pendientes`: se crea cuando la clienta envía una captura/comprobante de cita después de recibir la liga de agendamiento.
- `citas_completadas`: se crea cuando, existiendo una pendiente, la clienta envía después el comprobante de pago/anticipo.

Cuando una cita pasa a completada, se elimina de `citas_pendientes`. La tabla
`citas_pendientes` se purga con `MEMORY_RETENTION_DAYS`; `citas_completadas`
no se borra automáticamente por tiempo.

## Webhook de Evolution

Cuando Evolution corre en el mismo `docker-compose.yml`, usa la URL interna:

```text
http://vanessa-app:8000/webhook?apiKey=<WEBHOOK_SECRET>
```

El backend acepta tanto `/webhook` como `/webhook/messages-upsert`, y responde `duplicate` si Evolution reenvía el mismo `key.id`.
