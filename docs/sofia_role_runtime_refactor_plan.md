# Plan de Refactor: Sofia Role Runtime

## Estado de este branch

Este documento conserva el plan maestro. El estado implementado, la guía de pruebas y la operación del branch actual viven en:

- `docs/refactor_status.md`
- `docs/testing_runtime_v2.md`
- `docs/operations_runtime_v2.md`
- `README.md`

## Objetivo

Convertir Sofia en un asistente operacional configurable y replicable para otros negocios, capaz de actuar como una combinacion controlada de:

- `staff_1`: experiencia acumulada desde el dia 1 para agendar citas por WhatsApp y llenar la agenda de forma eficiente.
- `staff_2_manager`: operacion diaria, resolucion de casos, priorizacion y escalamiento.
- `frontdesk_sofia`: atencion directa al cliente, captura de datos, cotizacion y guia a booking.

El objetivo no es crear un bot monolitico con un prompt mas grande. El objetivo es separar negocio, roles, politicas, herramientas, estado conversacional y canal WhatsApp.

Nota de diseno: `owner` puede existir como contexto estrategico para el equipo de desarrollo, pero no debe modelarse como agente operativo de Sofia. El rol operativo que se mezcla con Sofia es `staff_1`.

## Problema Actual

El proyecto actual esta muy centrado en Vanity y en Sofia:

- `app/main.py` concentra webhook, estado, reglas, memoria, LLM, booking, media, follow-ups y persistencia.
- `app/knowledge_engine.py` concatena documentos Markdown en un unico system prompt.
- La identidad de Sofia vive mezclada entre codigo, prompt y documentos operativos.
- La autoridad de staff humano esta expresada como instrucciones, no como capacidades controladas.
- Replicar el bot para otro negocio requeriria duplicar o editar codigo.

## Principio Arquitectonico

Sofia debe ser una instancia de un runtime conversacional multi-negocio. El negocio configura:

- identidad del bot
- catalogo
- politicas
- perfiles de staff
- herramientas disponibles
- limites de autoridad
- reglas de escalamiento

El codigo debe ejecutar esas reglas sin depender de nombres, servicios o politicas hardcodeadas de Vanity.

## Arquitectura Propuesta

```txt
app/
  bots/
    runtime.py
    registry.py
  tenants/
    models.py
    loader.py
  conversation/
    state.py
    classifier.py
    policy_engine.py
    response_planner.py
    memory.py
    prompt_builder.py
  roles/
    staff1.py
    manager.py
    frontdesk.py
    blender.py
  knowledge/
    engine.py
    catalog.py
  channels/
    whatsapp.py
  tools/
    booking.py
    payments.py
    handover.py
    notifications.py
```

## Fase 1: Diagnostico y Separacion de Responsabilidades

### Tarea 1: Mapear responsabilidades actuales

Actividades:

- Identificar funciones de `app/main.py` que pertenecen a canal WhatsApp.
- Identificar funciones de estado conversacional.
- Identificar funciones de memoria y persistencia.
- Identificar funciones de decision de negocio.
- Identificar funciones de generacion LLM.

Entregable:

- Matriz `responsabilidad -> modulo destino`.

### Tarea 2: Separar reglas duras, politicas y estilo

Actividades:

- Clasificar reglas actuales en:
  - reglas duras
  - politicas de negocio
  - estilo conversacional
  - restricciones de seguridad
  - capacidades reales del sistema

Ejemplos:

- Regla dura: no inventar precios.
- Politica: si hay queja fuerte, escalar.
- Estilo: mensajes cortos tipo recepcion humana.
- Capacidad: enviar liga de booking, pausar bot, validar comprobante.

### Tarea 3: Definir contrato interno de conversacion

Modelos iniciales:

- `ConversationContext`
- `CustomerProfile`
- `DetectedIntent`
- `ConversationState`
- `AssistantDecision`
- `ResponsePlan`
- `BusinessAction`

Objetivo:

- El LLM redacta, pero no decide libremente todo el flujo.

## Fase 2: Modelo Replicable de Negocio

### Tarea 4: Crear `BusinessProfile`

Ejemplo:

```yaml
business_id: vanity
display_name: Vanity Nail Salon
industry: beauty_salon
timezone: America/Monterrey
language: es-MX
booking:
  provider: fresha
  url: https://...
payments:
  provider: paypal
  deposit_required: true
brand_voice:
  tone: calido_breve_premium
```

### Tarea 5: Crear `ServiceCatalog`

Actividades:

- Usar `service_catalog` como fuente única de servicios, extras, precios, duraciones y vigencia.
- Definir una estructura normalizada para servicios, extras, precios, duraciones y vigencia.
- Evitar que precios dependan de parsing libre de prompt.

### Tarea 6: Crear `BusinessPolicyPack`

Debe definir:

- cuando cotizar
- cuando escalar
- cuando guardar silencio
- cuando enviar booking
- limites de autoridad del bot
- validacion de promociones
- reglas de deposito y comprobantes

## Fase 3: Sistema de Roles Staff

### Tarea 7: Definir `StaffRoleProfile`

Campos sugeridos:

```yaml
role_id: staff1
authority_level: high
focus:
  - conversion_a_cita_por_whatsapp
  - llenado_eficiente_de_agenda
  - criterio_de_recepcion_experta
  - continuidad_desde_el_primer_dia
can_execute:
  - choose_next_scheduling_question
  - prioritize_booking_path
cannot_execute:
  - confirmar_cita_manual_sin_tool
```

### Tarea 8: Modelar `staff_1`

Responsabilidades:

- aplicar experiencia real de recepcion desde el dia 1
- guiar la conversacion para llenar agenda con eficiencia
- elegir la siguiente pregunta que reduce friccion
- detectar cuando conviene llevar a booking, pedir dato faltante o escalar
- mantener continuidad como una persona que conoce el flujo operativo

No debe:

- responder como si estuviera atendiendo manualmente
- inventar disponibilidad
- saltarse reglas documentales

### Tarea 9: Modelar `staff_2_manager`

Responsabilidades:

- resolver operacion diaria
- clasificar urgencia
- detectar incidencias
- ordenar siguiente paso
- decidir si WhatsApp resuelve o si conviene booking

No debe:

- cambiar politicas globales
- prometer excepciones no configuradas

### Tarea 10: Crear `RoleBlender`

Ejemplo de pesos:

```yaml
new_lead:
  frontdesk: 0.70
  manager: 0.20
  staff1: 0.10

incident:
  frontdesk: 0.30
  manager: 0.50
  staff1: 0.20

complaint:
  frontdesk: 0.20
  manager: 0.40
  staff1: 0.40
```

## Fase 4: Motor de Decision Antes del LLM

### Tarea 11: Crear `ConversationClassifier`

Entrada:

- mensaje actual
- historial
- memoria
- metadata de media
- timestamps
- datos de citas o pagos

Salida:

- intencion
- estado
- urgencia
- riesgo de duplicacion
- intervencion humana reciente
- dato faltante

### Tarea 12: Crear `PolicyEngine`

Decisiones posibles:

```txt
RESPOND
SILENCE
ESCALATE_HUMAN
SEND_STRUCTURED_REPLY
ASK_LLM
```

Regla central:

- El sistema decide si debe intervenir antes de llamar al LLM.

### Tarea 13: Crear `ResponsePlanner`

Ejemplo de salida:

```json
{
  "action": "ask_missing_detail",
  "missing_field": "retiro",
  "tone": "frontdesk_staff1",
  "constraints": ["one_question", "no_booking_link_yet"]
}
```

## Fase 5: Prompt Modular

### Tarea 14: Dividir documentos

Estructura propuesta:

```txt
tenants/vanity/
  business.yaml
  roles/
    staff1.md
    manager.md
    frontdesk.md
  policies/
    booking.md
    escalation.md
    latency.md
```

### Tarea 15: Modificar `KnowledgeEngine`

Actividades:

- Cargar conocimiento por tenant.
- Cargar solo documentos relevantes para la decision actual.
- Mantener fallback a `docs/` durante la migracion.

### Tarea 16: Crear `PromptBuilder`

Contrato:

```txt
system = identidad negocio + politicas activas + mezcla de roles
user = contexto conversacional + ultimo mensaje + plan de respuesta
```

## Fase 6: Multi-Negocio

### Tarea 17: Introducir `tenant_id`

Fuentes posibles:

- instancia Evolution
- numero conectado
- path del webhook
- configuracion default

### Tarea 18: Ajustar modelos de base de datos

Agregar `tenant_id` a:

- `Interaccion`
- `SesionMemoria`
- `CitaPendiente`
- `CitaCompletada`
- `WebhookEvent`

### Tarea 19: Crear `BotRegistry`

Responsabilidad:

- resolver tenant
- cargar configuracion
- exponer perfil de bot
- aislar memoria por negocio

### Tarea 20: Separar canal de negocio

Evolution API debe quedar como adaptador WhatsApp. No debe contener conocimiento de Sofia ni Vanity.

## Fase 7: Capacidades y Herramientas

### Tarea 21: Definir acciones permitidas

Acciones iniciales:

- `send_booking_link`
- `request_missing_detail`
- `quote_service`
- `validate_booking_proof`
- `validate_payment_proof`
- `pause_bot`
- `notify_human`
- `schedule_followup`

### Tarea 22: Crear tool layer

Cada accion debe tener:

- precondiciones
- ejecucion
- resultado estructurado
- mensaje sugerido
- log operativo

### Tarea 23: Crear limites de autoridad

Sofia puede:

- orientar
- cotizar desde catalogo
- pedir captura
- validar comprobante cuando haya datos suficientes
- escalar

Sofia no puede:

- confirmar disponibilidad real sin API
- mover citas manualmente
- prometer excepciones
- contradecir recepcion humana

## Fase 8: Refactor Incremental

### Tarea 24: Extraer parsing de webhook

Destino:

- `app/channels/whatsapp.py`

### Tarea 25: Extraer buffer conversacional

Destino:

- `app/conversation/memory.py`

### Tarea 26: Extraer derivacion de estado

Destino:

- `app/conversation/state.py`

### Tarea 27: Extraer armado de prompt

Destino:

- `app/conversation/prompt_builder.py`

### Tarea 28: Reemplazar `_ask_vanessa`

Nuevo nombre:

- `generate_assistant_reply`

Objetivo:

- eliminar nombres hardcodeados como Vanessa, Sofia o Vanity del runtime generico.

### Tarea 29: Reducir `app/main.py`

Debe quedar como orquestador:

```txt
recibir webhook
normalizar mensaje
cargar tenant
cargar contexto
clasificar
decidir
ejecutar accion
persistir
responder
```

## Fase 9: Testing

### Tarea 30: Tests de roles

Casos:

- en queja sube peso manager/staff1
- en lead nuevo domina frontdesk
- si hay intervencion humana reciente, silencio
- si falta retiro, no manda booking

### Tarea 31: Tests multi-negocio

Casos:

- dos tenants no comparten memoria
- cada tenant carga catalogo distinto
- cada tenant tiene tono distinto
- misma intencion produce distinta politica segun negocio

### Tarea 32: Tests de autoridad

Casos:

- Sofia no confirma disponibilidad sin herramienta
- Sofia no promete mover cita
- Sofia si escala cuando hay queja
- Sofia no contradice humano reciente

### Tarea 33: Tests con chats reales

Usar `whatsapp_interactions/messaging_selfimp.md` como fuente de escenarios regresivos.

## Fase 10: Migracion Operativa

### Tarea 34: Mantener compatibilidad Vanity

Crear tenant `vanity` con la configuracion actual. El comportamiento no debe cambiar al inicio.

### Tarea 35: Activar por flags

Variables sugeridas:

```env
BOT_RUNTIME_V2_ENABLED=false
TENANT_CONFIG_PATH=tenants
ROLE_BLEND_ENABLED=false
```

### Tarea 36: Comparar V1 vs V2

En modo test:

- generar respuesta V1
- generar decision V2
- guardar diferencias
- enviar solo la respuesta activa configurada

### Tarea 37: Activar V2 solo para allowlist

Usar `TEST_MODE_ALLOWED_NUMBERS` para validar antes de produccion.

## Definicion de Exito

El refactor esta listo cuando:

- Sofia puede cambiar de negocio sin tocar codigo Python.
- Staff1, manager y frontdesk son perfiles configurables.
- El bot decide cuando callar antes de llamar al LLM.
- Las capacidades reales estan separadas de la personalidad.
- `app/main.py` deja de concentrar las decisiones.
- Los tests cubren estados, autoridad, escalamiento y multi-tenant.
- Vanity sigue funcionando igual o mejor durante la migracion.
