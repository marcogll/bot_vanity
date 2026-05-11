# Evolution API Latency Guide

## Objetivo

Reducir latencia, evitar mensajes duplicados y bajar el ruido operativo entre Evolution API y Sofía para las pruebas del fin de semana.

Esta guía está enfocada en:

- entregar mensajes al webhook lo más rápido posible
- evitar auto-respuestas o flujos duplicados
- asegurar que capturas y comprobantes lleguen completos

## Configuración recomendada de webhook

Usar webhook por instancia, no webhook global.

Valores recomendados:

- `enabled: true`
- `url: http://vanessa-app:8000/webhook?apiKey=<WEBHOOK_SECRET>` si Evolution y Sofía corren en la misma red Docker
- `url: https://<dominio-vanessa-app>/webhook?apiKey=<WEBHOOK_SECRET>` si Evolution está fuera de la red Docker
- `webhook_by_events: false`
- `webhook_base64: true`
- `events: ["MESSAGES_UPSERT"]`

### Por qué así

- `MESSAGES_UPSERT` es el evento realmente necesario para conversaciones entrantes.
- `webhook_base64: true` ayuda a que Sofía pueda leer capturas, comprobantes y audios sin depender de fetches posteriores.
- `webhook_by_events: false` simplifica el enrutamiento actual de esta app.
- usar solo `MESSAGES_UPSERT` reduce tráfico innecesario y baja el riesgo de ruido.

## Qué no activar en Evolution para estas pruebas

En la misma instancia de WhatsApp, desactiva cualquier cosa que también responda mensajes:

- Typebot
- chatbot interno
- auto-respuestas configuradas desde Evolution
- flujos externos paralelos
- webhooks globales adicionales que generen side effects

Si más de un sistema responde, el problema ya no es solo latencia: se vuelve competencia de automatizaciones.

## Eventos recomendados

Para operación normal:

- `MESSAGES_UPSERT`: sí
- `CONNECTION_UPDATE`: opcional, solo para monitoreo fuera del webhook conversacional
- `SEND_MESSAGE`: no necesario
- `MESSAGES_UPDATE`: no necesario por ahora
- `MESSAGES_DELETE`: no necesario por ahora
- `CONTACTS_UPDATE`: no necesario
- `PRESENCE_UPDATE`: no necesario
- `CHATS_UPDATE`: no necesario

### Nota

Mientras menos eventos mandes al backend durante pruebas, mejor visibilidad tendrás sobre lo que realmente dispara Sofía.

## Base64

Para este proyecto conviene dejar `webhook_base64: true` porque Sofía analiza:

- capturas de cita
- comprobantes de pago
- imágenes de referencia
- audios transcritos

Si lo dejas en `false`, aumentas dependencia de fetches o pierdes contexto visual.

## Red y despliegue

Si corres todo en Docker, mantén Evolution y la app en la misma red interna.

Recomendado:

- Sofía responde a Evolution usando `http://evolution-api:8080`
- el webhook de Evolution apunta a `http://vanessa-app:8000/webhook?apiKey=<WEBHOOK_SECRET>` cuando ambos contenedores comparten red
- el webhook público apunta a la app FastAPI solo si Evolution está fuera de esa red
- evita túneles innecesarios entre Evolution y la app si ambos están en la misma máquina o VPS

## Recomendaciones operativas para bajar latencia

### 1. Una sola instancia activa por número

No conectes el mismo WhatsApp a múltiples automatizaciones al mismo tiempo.

### 2. Evita reenvíos extras

No encadenes:

- Evolution -> servicio A -> servicio B -> Sofía

Cada salto agrega retraso y puntos de falla.

### 3. Mantén el webhook simple

La URL de webhook debe apuntar directo a FastAPI:

- `POST /webhook?apiKey=<WEBHOOK_SECRET>`

En logs sanos debes ver:

- `delivery_lag_seconds=0` o bajo
- `Webhook processing completed ... elapsed_seconds` normalmente cerca de 1 a 3 segundos

Si `delivery_lag_seconds` llega alto, el retraso está antes de Sofía: Evolution, cola, proxy, dominio público o configuración persistida del webhook.

### 4. Revisa tiempos de respuesta de la app

Si la app tarda en responder al webhook, Evolution puede acumular eventos. Para pruebas:

- revisa logs de FastAPI
- revisa logs de Evolution
- confirma que OpenAI no esté causando cola excesiva

### 5. Desactiva respuestas automáticas redundantes

Si Evolution tiene mensajes de ausencia/fuera de horario configurados por su lado y Sofía también responde, verás duplicados.

Para estas pruebas, idealmente:

- o responde Evolution
- o responde Sofía

pero no ambos para la misma intención.

## Payload recomendado para configurar webhook por endpoint

Ejemplo de configuración:

```json
{
  "enabled": true,
  "url": "http://vanessa-app:8000/webhook?apiKey=<WEBHOOK_SECRET>",
  "webhook_by_events": false,
  "webhook_base64": true,
  "events": [
    "MESSAGES_UPSERT"
  ]
}
```

## Checklist para el fin de semana

- webhook activo por instancia
- `MESSAGES_UPSERT` como único evento conversacional
- `webhook_base64: true`
- sin Typebot ni otro bot paralelo
- sin auto-reply duplicado desde Evolution
- Sofía y Evolution en la misma red/localidad de despliegue
- revisar logs de ambos lados durante pruebas

## Sobre logs por cliente

La app ya guarda interacciones por `whatsapp_id` en la tabla `interacciones`.

Eso alcanza para:

- revisar conversaciones por cliente
- auditar qué respondió Sofía
- extraer muestras después de las pruebas

A futuro sí conviene:

- agrupar por ventana de 24h
- emitir resumen por webhook
- mandar sesiones cerradas a un analizador externo

Pero para este sprint no es bloqueante.

## Referencias oficiales

- Evolution webhook config: https://docs.evoapicloud.com/instances/events/webhook
- Evolution webhooks v2: https://doc.evolution-api.com/v2/en/configuration/webhooks
