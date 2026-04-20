# Debug Log: Sofía Bot Vanity

## Estado del Proyecto

- Bot activo como **Sofía** para copy visible y conversación con clientes.
- Instancia de Evolution controlada como `sofia` sin acento.
- Evolution fijado en `evoapicloud/evolution-api:v2.3.7` para corregir problemas de `@lid`.
- Webhook recomendado dentro de Docker: `http://vanessa-app:8000/webhook?apiKey=<WEBHOOK_SECRET>`.
- La app responde correctamente al número real cuando Evolution entrega el mapeo PN/LID.

## Cambios Recientes

- Se cambió la imagen de Evolution desde `atendai/evolution-api:v2.1.1` a `evoapicloud/evolution-api:v2.3.7`.
- Se agregó diagnóstico de payload para casos donde Evolution entrega solo `@lid`.
- Se agregó deduplicación en memoria por `instance + remote_jid + session_id` para evitar mensajes dobles cuando Evolution reenvía el mismo evento.
- Se agregó saludo inicial fijo: Sofía se presenta y pide el nombre del cliente al iniciar una conversación nueva.
- Se definió `dipiridú` como comando administrativo de borrado global de memoria e historial, con confirmación explícita antes de ejecutar.
- Se agregaron tablas `citas_pendientes` y `citas_completadas` para separar reservas en proceso y completadas con comprobante de pago.
- Se restringió `dipiridú` al teléfono configurado en `ADMIN_PHONE_NUMBER`.
- Se agregó transcripción de audios con `gpt-4o-mini-transcribe` cuando Evolution manda media en base64.
- Se actualizó documentación en `README.md`, `PRD.md` y `TASKS.md`.

## Resultado Observado

- Con Evolution `v2.1.1`, el webhook llegaba como `249391621378064@lid` sin teléfono real y `sendText` fallaba con `exists:false`.
- Con `latest` de `atendai/evolution-api`, Docker levantó `v2.2.3`, todavía sin los fixes necesarios.
- Con `evoapicloud/evolution-api:v2.3.7`, Evolution logró enviar a `5218441026472` y el log mostró `Evolution sendText succeeded`.
- Después del upgrade aparecieron múltiples POST del mismo evento, por lo que se agregó deduplicación en la app.
- En producción se detectó una `OPENAI_API_KEY` truncada (`sk-proj-`, longitud 8); al corregirla, la prueba desde el contenedor respondió `OK` con `gpt-4o`.

## Pruebas Ejecutadas

- `docker compose config --quiet`: OK.
- `.venv/bin/python -m pytest -q`: OK, 34 pruebas pasaron tras el ajuste de audio, admin phone, tracking de citas, fallback, formato WhatsApp y borrado global.

## Pendientes

- Verificar en producción que los duplicados ahora devuelvan `duplicate` y no generen segunda respuesta.
- Enviar un mensaje nuevo desde WhatsApp sin historial y confirmar que el primer texto de Sofía pida el nombre.
- Revisar si conviene desactivar webhook global o webhook de instancia para reducir POST duplicados desde Evolution.
- Migrar deduplicación a Redis o DB si se corre más de una réplica de `vanessa-app`.
