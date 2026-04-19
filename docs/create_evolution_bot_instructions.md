# Evolution Bot Instructions

Evolution API recibe mensajes de WhatsApp y los reenvía a Sofía mediante webhook.

Configuración esperada:
- Instancia de Evolution conectada a WhatsApp.
- Evento `MESSAGES_UPSERT` habilitado.
- Webhook apuntando a `/webhook` de Sofía.
- `apiKey` del webhook igual a `WEBHOOK_SECRET`.

Sofía responde por Evolution usando:
- URL interna de Evolution cuando corre en Docker: `http://evolution-api:8080`.
- Nombre de instancia recibido en el webhook.
- `EVOLUTION_API_KEY` para autenticar el envío.

El webhook debe ignorar mensajes enviados por la propia cuenta conectada para evitar loops.
