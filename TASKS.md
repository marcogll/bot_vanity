# TASKS.md: Plan de Implementación - Proyecto Vanessa

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
- [x] Markdown Parser: Desarrollar el cargador dinámico de los archivos en `/docs` para alimentar el contexto de la IA.
- [x] Integración LLM: Configurar el cliente de OpenAI (GPT-4o) con el flujo de RAG básico.
- [x] Inyección de Fecha: Programar que cada mensaje enviado al LLM incluya la fecha y hora actual del servidor para validar `promos.md`.

**Notas Fase 2:**
- El cargador RAG soporta `docs/create_evolution_bot.md` y `docs/create_evolution_bot_instructions.md` para evitar romper si cambia el nombre del documento.
- El webhook espera el payload plano documentado por Evolution API y responde `{ "message": "..." }`.

## Fase 3: Seguridad y "Hardening" 🛡️
Protección del sistema y de los datos del cliente.

- [x] Filtro Anti-Injection: Implementar capa de detección de frases que intenten ignorar instrucciones del sistema.
- [x] Cifrado AES-256: Configurar el módulo `cryptography.fernet` para cifrar los campos `content` y `pushName` antes de guardarlos.
- [x] Rate Limiting: Limitar el número de mensajes por usuario para evitar abusos o ataques de denegación de servicio.

**Notas Fase 3:**
- El rate limit actual es en memoria por proceso. Para múltiples réplicas debe moverse a Redis.
- El filtro anti-injection cubre frases explícitas; debe ampliarse con telemetría real después de pruebas con usuarios.

## Fase 4: Persistencia y Memoria 💾
Gestión de la base de datos y la política de 30 días.

- [x] Migraciones: Ejecutar scripts iniciales de creación de tablas según `docs/db.md`.
- [x] Lógica de Resumen: Programar que, tras cada interacción, la IA genere/actualice el `resumen_perfil` en la tabla `sesiones_memoria`.
- [x] Janitor Task (Cron): Desarrollar la tarea programada que se ejecuta cada 24h para purgar registros con más de 30 días de antigüedad.

**Notas Fase 4:**
- Las tablas se crean con `SQLAlchemy metadata.create_all()` al iniciar. Pendiente futuro: migraciones formales con Alembic antes de producción.
- El resumen de memoria actual es determinístico y compacto; pendiente futuro: resumen generado por LLM cuando se estabilice el costo/latencia.
- El Janitor corre como background task dentro de FastAPI cada 24h y borra interacciones/sesiones fuera de retención.

## Fase 5: Lógica de Negocio y Seguimiento ⏱️
Funciones específicas de Vanity Nail Salon.

- [x] Calculadora de Precios: Asegurar que la IA sume correctamente (Base + Retiro + Nail Art) basándose en `knowledge_base.md`.
- [x] Background Task (Follow-up): Configurar el temporizador de 10 minutos para enviar el mensaje de seguimiento si no hay confirmación de cita.
- [x] Human Handover: Lógica para detectar palabras clave de frustración y pausar el bot.

**Notas Fase 5:**
- La calculadora cubre los servicios principales de `knowledge_base.md` y suma base + retiro + Nail Art cuando puede detectarlos en texto.
- El follow-up se dispara si Vanessa envió la liga y no hay una respuesta nueva del usuario después del delay configurado.
- Pendiente futuro: guardar un estado formal de cita confirmada si Fresh o Evolution proveen esa señal.

## Fase 6: QA y Pruebas de Estrés 🧪

- [ ] Test de Flujo Completo: Simular flujo desde saludo hasta recepción de liga de Fresh.
- [ ] Test de Promociones: Validar que Vanessa NO ofrezca promociones si la fecha del sistema está fuera de vigencia.
- [x] Test de Inyección: Intentar engañar al bot para que asuma una identidad distinta o revele el system prompt.

**Notas Fase 6:**
- Ya existe prueba unitaria para anti-injection, handover y calculadora de precio.
- Pendiente: tests de integración del webhook con DB temporal y mock de OpenAI.
- Pendiente: test específico de vigencia de promociones con fecha inyectada fuera de abril 2026.
