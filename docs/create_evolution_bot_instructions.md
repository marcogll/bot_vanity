# Evolution Bot Instructions

Evolution API recibe mensajes de WhatsApp y los reenvía a Sofía mediante webhook.

Configuración esperada:
- Instancia de Evolution conectada a WhatsApp.
- Evento `MESSAGES_UPSERT` habilitado como único evento conversacional.
- Webhook apuntando a `/webhook` de Sofía.
- `apiKey` del webhook igual a `WEBHOOK_SECRET`.
- Si corre en Docker con Sofía, usar webhook interno: `http://vanessa-app:8000/webhook?apiKey=<WEBHOOK_SECRET>`.

Sofía responde por Evolution usando:
- URL interna de Evolution cuando corre en Docker: `http://evolution-api:8080`.
- Nombre de instancia recibido en el webhook.
- `EVOLUTION_API_KEY` para autenticar el envío.

El webhook debe ignorar mensajes enviados por la propia cuenta conectada para evitar loops.

Eventos como `contacts.update`, `messages.update`, `presence.update`, `chats.update` y `send.message` no son necesarios para conversación y generan ruido operativo. Sofía los ignora, pero conviene desactivarlos desde Evolution.

Para configuración enfocada en latencia, eventos mínimos y reducción de ruido operativo, ver también:

- `docs/evolution_api_latency_guide.md`
