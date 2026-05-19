# Matriz de Clasificación de Reglas - Sofia Role Runtime

Fecha: 2026-05-18
Fase: 1 - Tarea 2
Estado: ✅ Completada

## Metodología

Cada regla del sistema fue clasificada en una de estas categorías:

1. **Reglas duras**: Restricciones inquebrantables que el sistema NUNCA debe violar
2. **Políticas de negocio**: Decisiones operacionales configurables por tenant
3. **Estilo conversacional**: Patrones de tono, longitud y forma de comunicación
4. **Restricciones de seguridad**: Protección contra abusos, inyecciones y accesos no autorizados
5. **Capacidades reales del sistema**: Acciones que el sistema puede ejecutar efectivamente

---

## 1. REGLAS DURAS

### 1.1 No inventar precios
- **Ubicación**: `app/main.py`, `app/knowledge_engine.py`
- **Descripción**: Nunca generar precios que no estén en el catálogo oficial
- **Código**: System prompt incluye catálogo canónico de Fresha/service_catalog
- **Impacto**: Crítico - evita cobros incorrectos

### 1.2 No confirmar disponibilidad sin API
- **Ubicación**: `app/main.py:1192-1246` (`_contains_unsupported_availability_claim`)
- **Descripción**: No afirmar que hay disponibilidad real ni confirmar citas sin integración directa
- **Código**: Detección de frases como "verificar disponibilidad", "confirmo tu cita", "hay espacio disponible"
- **Impacto**: Crítico - evita promesas falsas al cliente

### 1.3 No contradecir intervención humana reciente
- **Ubicación**: `app/conversation/state.py`, `app/main.py`
- **Descripción**: Si una humana respondió recientemente, Sofía debe mantener silencio
- **Código**: `has_recent_manual_team_intervention()`, `MANUAL_TEAM_INTERVENTION_MARKER`
- **Impacto**: Crítico - evita duplicación y confusión

### 1.4 No pedir nombre si ya hay contexto avanzado
- **Ubicación**: `app/main.py:1253-1263` (`_should_send_initial_greeting`)
- **Descripción**: No ejecutar saludo inicial si existe historial o evidencia de contexto avanzado
- **Código**: `has_advanced_conversation_context()`, verificación de historial
- **Impacto**: Alto - evita reinicios de flujo molestos

### 1.5 No duplicar webhooks
- **Ubicación**: `app/main.py:371-383`, `app/main.py:392-410`
- **Descripción**: Ignorar eventos repetidos con el mismo `key.id` o contenido similar
- **Código**: `_remember_inbound_webhook_seen()`, `_claim_webhook_for_processing()`
- **Impacto**: Alto - evita respuestas dobles

---

## 2. POLÍTICAS DE NEGOCIO

### 2.1 Escalación por queja fuerte
- **Ubicación**: `app/business_rules.py:18-27`, `app/conversation/policy_engine.py:40-50`
- **Descripción**: Si hay queja fuerte, escalar a humano y pausar bot
- **Configurable**: Marcadores de escalación por tenant
- **Código**: `needs_human_handover()`, `PolicyEngine.decide()`
- **Impacto**: Alto - retención de clientes

### 2.2 Follow-up de booking
- **Ubicación**: `app/tools/booking.py`, `app/main.py:987-995`
- **Descripción**: Programar follow-up después de 15 minutos si no hay comprobante
- **Configurable**: `FOLLOW_UP_DELAY_SECONDS` (default 900)
- **Código**: `schedule_follow_up()`, `_should_schedule_booking_follow_up()`
- **Impacto**: Alto - conversión de citas

### 2.3 Flujo de booking estructurado
- **Ubicación**: `app/conversation/booking_flow.py`
- **Descripción**: Secuencia de preguntas para agendar: nombre → servicio → retiro → tono → Fresha → comprobante
- **Configurable**: URLs de booking, app stores por tenant
- **Código**: `booking_flow_reply()`, `BookingFlowSettings`
- **Impacto**: Alto - proceso core del negocio

### 2.4 Validación de comprobantes
- **Ubicación**: `app/tools/proofs.py`, `app/tools/payments.py`
- **Descripción**: Analizar imágenes de comprobantes de cita y pago con visión AI
- **Configurable**: Modelos de visión, umbrales de confianza
- **Código**: `analyze_booking_confirmation_image()`, `analyze_payment_proof_image()`
- **Impacto**: Alto - automatización de confirmación

### 2.5 Retención de datos (30 días)
- **Ubicación**: `app/janitor.py`
- **Descripción**: Purgar interacciones y sesiones con más de 30 días
- **Configurable**: Retención por tenant
- **Código**: `janitor_loop()`
- **Impacto**: Medio - privacidad y costos

### 2.6 No empujar Fresha en conversaciones manuales
- **Ubicación**: `app/main.py:1278-1283` (`_should_schedule_booking_follow_up`)
- **Descripción**: No insistir con booking link si ya hay contexto avanzado o intervención humana
- **Código**: `has_advanced_conversation_context()`
- **Impacto**: Alto - evita fricción

---

## 3. ESTILO CONVERSACIONAL

### 3.1 Mensajes cortos tipo recepción humana
- **Ubicación**: `app/knowledge_engine.py`, `docs/system_prompt.md`
- **Descripción**: Respuestas breves, cálidas, sin párrafos largos
- **Código**: Inyectado en system prompt
- **Ejemplo**: "Perfecto 💗 Para uñas, ¿necesitas retiro de algún material previo?"

### 3.2 Tono cálido y premium
- **Ubicación**: `docs/system_prompt.md`, `app/knowledge_engine.py`
- **Descripción**: Uso de emojis discretos (💗), trato cercano pero profesional
- **Código**: Instrucciones en documentos de conocimiento
- **Ejemplo**: "¡Gracias, María! Encantada de atenderte. 💗"

### 3.3 Una pregunta a la vez
- **Ubicación**: `app/conversation/policy_engine.py:84-90`
- **Descripción**: No hacer múltiples preguntas en un solo mensaje
- **Código**: `ResponsePlan` con constraint `one_question`
- **Impacto**: Medio - mejor UX

### 3.4 No repetir información ya dada
- **Ubicación**: `app/conversation/memory.py`
- **Descripción**: Usar buffer conversacional para evitar redundancias
- **Código**: `ConversationBuffer`, `conversation_buffer_prompt_hint()`
- **Impacto**: Medio - fluidez conversacional

### 3.5 Copiar estilo de staff1 pero sin su autoridad
- **Ubicación**: `docs/sofia_role_runtime_refactor_plan.md`, `app/roles/blender.py`
- **Descripción**: Sofía replica tono de recepcionista experta pero no agendado manual
- **Código**: `RoleBlender`, pesos de roles por estado
- **Impacto**: Alto - autenticidad sin sobrepasar límites

---

## 4. RESTRICCIONES DE SEGURIDAD

### 4.1 Rate limiting
- **Ubicación**: `app/rate_limit.py`, `app/main.py:311-316`
- **Descripción**: Limitar mensajes por usuario en ventana de tiempo
- **Configurable**: `RATE_LIMIT_MAX_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`
- **Código**: `InMemoryRateLimiter`, `_is_rate_limited()`
- **Impacto**: Alto - prevención de abusos

### 4.2 Anti-inyección de prompt
- **Ubicación**: `app/security.py`, `app/main.py:871-890`
- **Descripción**: Detectar intentos de ignorar instrucciones del sistema
- **Código**: `looks_like_prompt_injection()`, respuesta segura hardcodeada
- **Impacto**: Crítico - integridad del sistema

### 4.3 Validación de webhook secret
- **Ubicación**: `app/security.py`
- **Descripción**: Verificar `WEBHOOK_SECRET` de Evolution API
- **Código**: `validate_webhook_api_key`
- **Impacto**: Crítico - autenticación de fuente

### 4.4 Cifrado AES-256 de datos sensibles
- **Ubicación**: `app/models.py`
- **Descripción**: Cifrar campos `content` y `push_name` en base de datos
- **Código**: Fernet encryption en modelo SQLAlchemy
- **Impacto**: Crítico - privacidad de datos

### 4.5 Comandos administrativos restringidos
- **Ubicación**: `app/main.py:768-842`
- **Descripción**: Solo `ADMIN_PHONE_NUMBER` puede ejecutar comandos como `dipiridú`, `serac`
- **Código**: `_is_authorized_admin()`, validación en cada comando
- **Impacto**: Crítico - control de acceso

### 4.6 Test mode allowlist
- **Ubicación**: `app/main.py:426-475`
- **Descripción**: En test mode, solo números autorizados reciben respuestas del bot
- **Configurable**: `TEST_MODE_ALLOWED_NUMBERS`
- **Código**: `_is_test_mode_allowed_number()`, `_should_handle_in_test_mode()`
- **Impacto**: Alto - aislamiento de pruebas

### 4.7 Deduplicación por firma de mensaje
- **Ubicación**: `app/main.py:2117-2137`
- **Descripción**: Evitar eco de mensajes outbound del bot
- **Código**: `_remember_recent_outbound_signature()`, `_consume_recent_outbound_signature()`
- **Impacto**: Medio - evita loops

---

## 5. CAPACIDADES REALES DEL SISTEMA

### 5.1 Enviar link de booking
- **Ubicación**: `app/config.py`, `app/main.py`
- **Descripción**: Redirigir a Fresha para agendado real
- **Código**: `settings.booking_url` inyectado en respuestas
- **Limitación**: No confirma disponibilidad, solo guía

### 5.2 Validar comprobante de cita
- **Ubicación**: `app/tools/vision.py`, `app/tools/proofs.py`
- **Descripción**: Analizar captura de pantalla de confirmación de Fresha
- **Código**: `analyze_booking_confirmation_image()`, `BookingAnalysis`
- **Limitación**: Depende de calidad de imagen y modelo de visión

### 5.3 Validar comprobante de pago
- **Ubicación**: `app/tools/vision.py`, `app/tools/payments.py`
- **Descripción**: Analizar captura de pago de PayPal/transferencia
- **Código**: `analyze_payment_proof_image()`, `PaymentAnalysis`
- **Limitación**: No verifica transacción real, solo lee imagen

### 5.4 Pausar bot por conversación
- **Ubicación**: `app/main.py:2776-2800`
- **Descripción**: Marcar conversación específica como pausada
- **Código**: `_bot_is_paused()`, `_mark_bot_paused()`, `BOT_PAUSED_MARKER`
- **Limitación**: Solo afecta a ese whatsapp_id

### 5.5 Pausar bot global
- **Ubicación**: `app/main.py:2780-2782`, `app/main.py:2873-2898`
- **Descripción**: Comando `serac shutdown` para detener todas las respuestas
- **Código**: `app.state.admin_runtime["bot_paused"]`
- **Limitación**: Requiere reinicio manual con `serac start`

### 5.6 Notificar escalación a admins
- **Ubicación**: `app/tools/notifications.py`
- **Descripción**: Enviar WhatsApp a `ADMIN_PHONE_NUMBERS` cuando hay escalación
- **Código**: `schedule_human_handover_notification()`
- **Limitación**: Notificación asíncrona, no garantiza respuesta inmediata

### 5.7 Programar follow-up
- **Ubicación**: `app/tools/booking.py`
- **Descripción**: Agendar mensaje de seguimiento después de delay configurable
- **Código**: `schedule_follow_up()`, `app.state.followup_tasks`
- **Limitación**: En memoria por proceso, se pierde en restart

### 5.8 Transcribir audio
- **Ubicación**: `app/main.py:1628-1688`
- **Descripción**: Convertir audios de WhatsApp a texto con OpenAI
- **Código**: `_transcribe_audio_payload()`, `settings.audio_transcription_model`
- **Limitación**: Requiere base64 de Evolution API, costo por transcripción

### 5.9 Exportar sesión de test
- **Ubicación**: `app/main.py:538-609`
- **Descripción**: Exportar historial completo de conversación para análisis
- **Código**: `_export_test_session_if_idle()`, webhook de export
- **Limitación**: Solo en test mode, requiere webhook configurado

### 5.10 Cargar catálogo de servicios
- **Ubicación**: `app/catalog_sync.py`, `app/main.py:1128-1151`
- **Descripción**: Sincronizar servicios desde CSV de Fresha o docs
- **Código**: `sync_service_catalog_from_fresha_csv()`, `_service_catalog_prompt_hint()`
- **Limitación**: No actualiza precios en tiempo real

---

## Resumen por Categoría

| Categoría | Cantidad | Críticas | Configurables |
|-----------|----------|----------|---------------|
| Reglas duras | 5 | 2 | 0 |
| Políticas de negocio | 6 | 0 | 5 |
| Estilo conversacional | 5 | 0 | 3 |
| Restricciones de seguridad | 7 | 4 | 3 |
| Capacidades reales | 10 | 0 | 4 |
| **TOTAL** | **33** | **6** | **15** |

---

## Hallazgos y Recomendaciones

### 1. Reglas hardcodeadas que deben ser configurables
- `HUMAN_HANDOVER_REQUEST_MARKERS` en `app/business_rules.py` → mover a tenant config
- `INITIAL_GREETING_REPLY` en `app/main.py:120-123` → mover a tenant config
- `FOLLOW_UP_DELAY_SECONDS` → ya es configurable ✅
- Marcadores de nail subservices → mover a catálogo

### 2. Políticas que requieren validación cruzada
- Validación de comprobantes debe cruzar con datos de pending booking
- Follow-up debe verificar estado real antes de enviar
- Escalación debe verificar si ya hay humano asignado

### 3. Estilos que deben ser perfiles de role
- Tono cálido_breve_premium → definir en `BotProfile` o `StaffRoleProfile`
- Longitud máxima de mensajes → constraint en `ResponsePlan`
- Uso de emojis → configurable por tenant

### 4. Capacidades que requieren tool layer formal
- Cada capacidad debe tener: precondiciones, ejecución, resultado, mensaje sugerido, log
- Actual: lógica dispersa en `main.py`, `tools/`, `business_rules.py`
- Objetivo: `app/tools/` con interfaz uniforme

---

## Siguientes Pasos (Fase 1 - Tarea 3)

1. Formalizar contrato interno con todos los modelos definidos
2. Crear `ConversationClassifier` para clasificación determinística antes del LLM
3. Definir interfaz de tool layer para capacidades reales
4. Migrar reglas hardcodeadas a configuración de tenant
