# Changelog

## 2026-05-01

### Conversación de Sofía

- Se integró `whatsapp_interactions/messaging_selfimp.md` a la base documental del prompt.
- Se ajustó el prompt del sistema para que Sofía replique el estilo de `staff1` sin fingir capacidad de agendar manualmente.
- Se agregaron guardas para no pedir nombre cuando la conversación ya llega avanzada.
- Se redujo el follow-up genérico de booking cuando ya existe evidencia de cita o comprobante.
- Se agregó estado conversacional derivado para mejorar contexto y estabilidad.

### Seguridad y robustez

- Se reforzó la detección de prompt injection con más patrones y normalización de texto.
- Se bloquea prompt injection también después de transcribir audios.
- Las imágenes de comprobantes y capturas ya no se mandan al LLM general como contexto visual libre.
- El análisis estructurado de imágenes ahora incluye instrucciones explícitas para ignorar prompts embebidos.
- La intervención manual del equipo ya no inyecta su texto completo al historial del modelo; se usa un marcador seguro.
- El comando `sender/debug sender` quedó restringido a administración.
- El borrado administrativo `dipiridú` ya no elimina toda la base; ahora se limita al chat actual.
- Se dejó deduplicación persistente de webhooks mediante `WebhookEvent`.
- Se agregó una comprobación persistente para distinguir ecos recientes del bot frente a mensajes manuales salientes.
- Ya no se purga todo el historial de un cliente por datos cifrados ilegibles; solo se limpia lo necesario.

### Operación

- Se creó `docs/evolution_api_latency_guide.md` con recomendaciones para reducir latencia y ruido en Evolution API.
- `.gitignore` ahora excluye los chats de `whatsapp_interactions` pero conserva `whatsapp_interactions/messaging_selfimp.md`.

### Validación

- Suite focalizada: `54 passed` en `tests/test_business_rules.py`.
