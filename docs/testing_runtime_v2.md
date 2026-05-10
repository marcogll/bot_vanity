# Guia de Pruebas del Runtime V2

## Preparacion local

Instala dependencias en el virtualenv del proyecto:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Para ejecutar tests sin depender de credenciales reales:

```bash
env OPENAI_API_KEY=test DATABASE_URL=postgresql+asyncpg://user:pass@localhost/test AES_ENCRYPTION_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= WEBHOOK_SECRET=test .venv/bin/python -m pytest
```

## Pruebas unitarias relevantes

- `tests/test_role_runtime.py`: tenant config y mezcla de roles.
- `tests/test_policy_engine.py`: silencio, escalación, prompt injection y fallback a LLM.
- `tests/test_bot_runtime_v2.py`: evaluación del Runtime V2.
- `tests/test_conversation_state.py`: derivación de estado sin importar `main.py`.
- `tests/test_conversation_memory.py`: buffer conversacional temporal.
- `tests/test_prompt_builder.py`: armado de mensajes para el LLM, media hints y sanitización de historial.
- `tests/test_whatsapp_channel.py`: parsing puro de payloads Evolution/WhatsApp.
- `tests/test_booking_flow.py`: flujo estructurado de retiro, diseño, app links y booking.
- `tests/test_business_rules.py`: regresión del flujo actual de `main.py`.

## Probar healthcheck local

Smoke test sin levantar DB ni startup completo:

```bash
env OPENAI_API_KEY=test DATABASE_URL=postgresql+asyncpg://user:pass@localhost/test AES_ENCRYPTION_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= WEBHOOK_SECRET=test .venv/bin/python -c "from fastapi.testclient import TestClient; from app.main import app; client = TestClient(app); response = client.get('/health'); print(response.status_code); print(response.json())"
```

Salida esperada:

```text
200
{'status': 'ok'}
```

Servidor local con startup completo:

```bash
env OPENAI_API_KEY=test DATABASE_URL=postgresql+asyncpg://user:pass@localhost/test AES_ENCRYPTION_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= WEBHOOK_SECRET=test .venv/bin/uvicorn app.main:app --reload --port 8001
```

Para este modo necesitas una base PostgreSQL accesible en `DATABASE_URL`, porque el startup inicializa tablas y sincroniza catálogo.

En otra terminal:

```bash
curl http://127.0.0.1:8001/health
```

Respuesta esperada:

```json
{"status":"ok"}
```

## Probar webhook local

El webhook responde `accepted` cuando el evento es valido. El procesamiento real se ejecuta en background y puede intentar usar Evolution/OpenAI si el flujo llega hasta esa parte.

```bash
curl -X POST "http://127.0.0.1:8001/webhook?apiKey=test" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "instance": "sofia_local",
    "data": {
      "key": {
        "remoteJid": "5218441026472@s.whatsapp.net",
        "fromMe": false,
        "id": "local-test-001"
      },
      "pushName": "Marco Test",
      "message": {
        "conversation": "Hola"
      }
    }
  }'
```

Respuesta esperada:

```json
{"message":"accepted"}
```

## Probar shadow mode

Configura:

```env
BOT_RUNTIME_V2_ENABLED=true
BOT_RUNTIME_V2_SHADOW_MODE=true
ROLE_BLEND_ENABLED=true
TENANT_CONFIG_PATH=tenants
DEFAULT_TENANT_ID=vanity
```

En logs debe aparecer una linea similar:

```text
Runtime V2 shadow: remote_jid=... tenant=vanity state=... intent=... decision=... plan=... dominant_role=...
```

## Probar flujo local de booking

Escenario esperado:

1. Cliente: `Hola`
2. Sofía: pide nombre.
3. Cliente: `Marco`
4. Sofía: pregunta servicio.
5. Cliente: `Uñas`
6. Sofía: pregunta subtipo.
7. Cliente: `Gelish`
8. Sofía: pregunta retiro.
9. Cliente: `No`
10. Sofía: pregunta tono liso, diseño o técnica.
11. Cliente: `tono liso`
12. Sofía: manda links de app, liga de booking y resumen `vas a agendar: Gelish - tono liso`.

Al mandar la liga, se agenda un follow-up después de `FOLLOW_UP_DELAY_SECONDS`, por defecto 900 segundos.

## Probar escalacion humana

Mensaje de ejemplo:

```text
Quiero hablar con una persona por una queja
```

Resultado esperado:

- respuesta de handover al cliente.
- persistencia de la interacción.
- notificación saliente a `ADMIN_PHONE_NUMBER` y `ADMIN_PHONE_NUMBERS` si Evolution está configurado.

## Limitaciones conocidas

- V2 todavía no toma control de respuestas productivas.
- El prompt builder ya está extraído. `main.py` conserva la orquestación de llamadas LLM generales, mientras el análisis visual estructurado vive en `app/tools/vision.py`.
- La capa de tools ya cubre notificaciones, follow-up de booking, persistencia de pagos/citas, helpers puros de capturas/comprobantes y análisis visual estructurado.
- Shadow mode registra comparación V1/V2 con `alignment=aligned|review` para auditar divergencias antes de activar control real.
- Multi-tenant ya persiste `tenant_id` en historial, memoria, citas y eventos webhook. Aún falta activar V2 fuera de shadow mode con allowlist.
