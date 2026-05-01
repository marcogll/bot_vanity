# TASKS.md: Plan de Implementación - Proyecto Sofía

## Fase 1: Infraestructura y Dockerización 🐳
Configuración del entorno de ejecución en Omarchy.

- [x] Dockerfile: Crear imagen basada en `python:3.11-slim` (optimizada para producción).
- [x] Docker Compose: Configurar servicios `vanessa-app` y `vanessa-db` (PostgreSQL 15).
- [x] Evolution Stack: Agregar `evolution-api`, PostgreSQL dedicado y Redis al mismo `docker-compose.yml` para despliegue en VPS.
- [x] Network Isolation: Crear red interna `vanity-net` para que la DB no sea accesible desde el exterior.
- [x] Volume Mapping: Configurar el montaje de la carpeta `./docs` como volumen de solo lectura para la app.
- [x] Healthchecks: Configurar chequeos de salud para asegurar que la App reinicie si pierde conexión con la DB.

**Notas Fase 1:**
- `docker-compose.yml` expone `vanessa-app` en el host (`8001:8000`) y Evolution en `8080:8080`. Las bases de datos y Redis quedan dentro de `vanity-net`, salvo `vanessa-db`, que publica `127.0.0.1:5432` para desarrollo local.
- Para desarrollo local sin Docker de la app, se puede seguir usando `.venv` + `uvicorn --port 8001`.

## Fase 2: Backend y Core (FastAPI) 🐍
Desarrollo de la lógica del servidor y procesamiento de mensajes.

- [x] Validación de Webhooks: Implementar middleware para verificar el `WEBHOOK_SECRET` de Evolution API.
- [x] Deduplicación de Webhooks: Ignorar eventos repetidos con el mismo `key.id` de Evolution para evitar respuestas dobles.
- [x] Markdown Parser: Desarrollar el cargador dinámico de los archivos en `/docs` para alimentar el contexto de la IA.
- [x] Integración LLM: Configurar el cliente de OpenAI (GPT-4o) con el flujo de RAG básico.
- [x] Inyección de Fecha: Programar que cada mensaje enviado al LLM incluya la fecha y hora actual del servidor para validar `promos.md`.

**Notas Fase 2:**
- El cargador RAG soporta `docs/create_evolution_bot.md` y `docs/create_evolution_bot_instructions.md` para evitar romper si cambia el nombre del documento.
- El webhook espera el payload plano documentado por Evolution API y responde `{ "message": "..." }`.
- La deduplicación es en memoria por proceso y usa `instance + remote_jid + session_id`; si se escala a múltiples réplicas debe moverse a Redis o DB.

## Fase 3: Seguridad y "Hardening" 🛡️
Protección del sistema y de los datos del cliente.

- [x] Filtro Anti-Injection: Implementar capa de detección de frases que intenten ignorar instrucciones del sistema.
- [x] Cifrado AES-256: Configurar el módulo `cryptography.fernet` para cifrar los campos `content` y `pushName` antes de guardarlos.
- [x] Rate Limiting: Limitar el número de mensajes por usuario para evitar abusos o ataques de denegación de servicio.
- [x] Comando administrativo `dipiridú`: borrar globalmente memoria e historial tras confirmación explícita.
- [x] Restringir comandos administrativos al teléfono configurado en `ADMIN_PHONE_NUMBER`.

**Notas Fase 3:**
- El rate limit actual es en memoria por proceso. Para múltiples réplicas debe moverse a Redis.
- El filtro anti-injection cubre frases explícitas; debe ampliarse con telemetría real después de pruebas con usuarios.
- `dipiridú` no borra solo al usuario que lo escribe; tras confirmar con `sí`, elimina todas las filas de `interacciones` y `sesiones_memoria`.

## Fase 4: Persistencia y Memoria 💾
Gestión de la base de datos y la política de 30 días.

- [x] Migraciones: Ejecutar scripts iniciales de creación de tablas según `docs/db.md`.
- [x] Lógica de Resumen: Programar que, tras cada interacción, la IA genere/actualice el `resumen_perfil` en la tabla `sesiones_memoria`.
- [x] Janitor Task (Cron): Desarrollar la tarea programada que se ejecuta cada 24h para purgar registros con más de 30 días de antigüedad.
- [x] Tracking de citas: guardar citas pendientes al recibir comprobante de cita y mover a completadas al recibir comprobante de pago.

**Notas Fase 4:**
- Las tablas se crean con `SQLAlchemy metadata.create_all()` al iniciar. Pendiente futuro: migraciones formales con Alembic antes de producción.
- El resumen de memoria actual es determinístico y compacto; pendiente futuro: resumen generado por LLM cuando se estabilice el costo/latencia.
- El Janitor corre como background task dentro de FastAPI cada 24h y borra interacciones/sesiones fuera de retención.
- `citas_pendientes` se purga con la retención de la app. `citas_completadas` no se purga automáticamente.

## Fase 5: Lógica de Negocio y Seguimiento ⏱️
Funciones específicas de Vanity Nail Salon.

- [x] Calculadora de Precios: Asegurar que la IA sume correctamente (Base + Retiro + Nail Art) basándose en `knowledge_base.md`.
- [x] Saludo Inicial: Presentarse como Sofía y pedir el nombre del cliente en la primera interacción.
- [x] Background Task (Follow-up): Configurar el temporizador de 10 minutos para enviar el mensaje de seguimiento si no hay confirmación de cita.
- [x] Human Handover: Lógica para detectar palabras clave de frustración y pausar el bot.
- [x] Transcripción de audios: convertir audios de WhatsApp con base64 a texto antes de pasarlos al flujo de OpenAI.

**Notas Fase 5:**
- La calculadora cubre los servicios principales de `knowledge_base.md` y suma base + retiro + Nail Art cuando puede detectarlos en texto.
- El primer mensaje de una conversación nueva no llama al LLM; guarda el mensaje y responde con el saludo fijo para pedir nombre.
- El follow-up se dispara si Sofía envió la liga y no hay una respuesta nueva del usuario después del delay configurado.
- Pendiente futuro: guardar un estado formal de cita confirmada si Fresh o Evolution proveen esa señal.
- Los audios requieren que Evolution mande `base64`; el modelo por defecto de transcripción es `gpt-4o-mini-transcribe`.

## Fase 6: QA y Pruebas de Estrés 🧪

- [ ] Test de Flujo Completo: Simular flujo desde saludo hasta recepción de liga de Fresh.
- [ ] Test de Promociones: Validar que Sofía NO ofrezca promociones si la fecha del sistema está fuera de vigencia.
- [x] Test de Inyección: Intentar engañar al bot para que asuma una identidad distinta o revele el system prompt.
- [x] Test de Deduplicación: Validar que el identificador de mensaje de Evolution genere una llave estable.
- [x] Test de Saludo Inicial: Validar que una conversación sin historial use el saludo de Sofía y pida nombre.

**Notas Fase 6:**
- Ya existe prueba unitaria para anti-injection, handover, calculadora de precio, deduplicación y saludo inicial.
- Pendiente: tests de integración del webhook con DB temporal y mock de OpenAI.
- Pendiente: test específico de vigencia de promociones con fecha inyectada fuera de abril 2026.

## Fase 7: Estabilización Conversacional de Sofía 🧭
Implementación guiada por análisis de chats reales, en especial los incidentes del `23-24 abril 2026` y el estilo operativo de `staff1`.

- [ ] Modelo de estado conversacional: Introducir un estado formal por conversación para distinguir al menos `new`, `collecting_service`, `booking_link_sent`, `awaiting_booking_proof`, `awaiting_deposit`, `confirmed`, `incident`, `handover_human`.
- [x] Señales de contexto alto: Detectar explícitamente comprobantes, capturas de cita, fotos de uñas, mensajes de tráfico, reacomodos y confirmaciones para evitar reinicios de flujo.
- [x] Guardas de saludo inicial: Dejar de pedir nombre automáticamente si ya existe historial útil, memoria previa o evidencia de contexto avanzado.
- [ ] Supresión de respuestas obsoletas: Cancelar o regenerar respuestas si el contexto cambió mientras el modelo tardó en responder.
- [x] Follow-up inteligente: Reemplazar el follow-up fijo `¿Pudiste elegir tu horario...?` por uno condicionado al estado real y cancelable si ya hubo respuesta humana o confirmación.
- [x] Detección de actividad humana reciente: Si una humana ya respondió útilmente en una ventana corta, Sofía no debe duplicar ni reabrir el flujo.
- [ ] Reglas de booking por contexto: No empujar Fresha cuando WhatsApp ya está resolviendo manualmente disponibilidad, reacomodo, incidencia o confirmación.
- [x] Separación estilo vs capacidad: Sofía debe heredar el tono de `staff1`, pero no asumir facultades de agendado manual que pertenecen a recepción humana.
- [x] Política de comprobantes: Si llega comprobante de anticipo o captura de cita, entrar a flujo de validación y confirmación, nunca a onboarding.
- [x] Estilo `staff1`: Traducir el patrón humano observado a reglas de longitud, tono y orden de preguntas para que Sofía replique una recepcionista real.
- [x] Guía Evolution API para latencia: Documentar la configuración recomendada de webhook, eventos y base64 para reducir ruido y retraso.
- [ ] Riesgo de contradicción: Antes de responder con precios, servicios u horarios, validar si ya existe una versión previa confirmada en la conversación o en estado persistido.
- [x] Telemetría conversacional: Registrar por qué se respondió, se silenció, se hizo handover o se canceló un follow-up para depuración posterior.

**Plan técnico sugerido por capa:**

- `app/models.py`
  Crear una tabla o ampliar `SesionMemoria`/`CitaPendiente` con estado conversacional, última intención detectada, último momento de intervención humana y banderas como `booking_proof_received`, `deposit_proof_received`, `human_active`.

- `app/main.py`
  Insertar un preprocesador determinístico antes del LLM que:
  1. clasifique el mensaje entrante
  2. actualice estado
  3. decida si aplica saludo inicial, flujo estructurado, LLM, redirección a booking, silencio o follow-up cancelado

- `app/main.py`
  Refactorizar `_should_send_initial_greeting()` para que dependa de contexto real y no solo de `no history`.

- `app/main.py`
  Reemplazar `_schedule_follow_up()` y `_send_follow_up_if_no_reply()` por una versión basada en estado, con cancelación si:
  1. hubo nuevo mensaje del usuario
  2. hubo respuesta humana
  3. la cita ya está confirmada
  4. se recibió captura/comprobante
  5. el tema cambió a incidencia o reacomodo

- `app/business_rules.py`
  Expandir reglas determinísticas para detectar:
  1. incidentes
  2. clienta en camino
  3. reacomodo
  4. comprobante/captura
  5. conversación ya resuelta por humana

- `app/knowledge_engine.py` y `docs/system_prompt.md`
  Mantener la guía conversacional como apoyo del modelo, dejando explícito que Sofía copia el estilo de `staff1` pero no su autoridad para agendar manualmente.

- `tests/test_business_rules.py`
  Agregar pruebas para los casos reales observados:
  1. no pedir nombre tras comprobante
  2. no mandar Fresha si ya hay cita en conversación
  3. no disparar follow-up obsoleto
  4. no contradecir precio previo confirmado
  5. silencio cuando ya respondió una humana
  6. tono corto estilo `staff1` en respuestas estructuradas

**Criterios de éxito:**

- Sofía no reinicia conversaciones activas.
- Sofía no manda ráfagas ni follow-ups obsoletos.
- Sofía no pide nombre después de una captura o comprobante.
- Sofía no insiste con Fresha cuando la recepción ya resolvió por chat.
- Sofía replica un estilo breve, cálido y contextual parecido al de `staff1`, pero conserva un flujo honesto de `redirigir a booking + validar confirmación`.
- Los incidentes del patrón `24/04/26` quedan cubiertos por pruebas automatizadas.
