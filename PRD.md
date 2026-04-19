# PRD: Sofía - Asistente Virtual de Recepción (Vanity Nail Salon)

## 1. Visión General
**Sofía** es el agente de inteligencia artificial encargado de la recepción, calificación de leads y gestión de consultas de Vanity Nail Salon. Su propósito es actuar como una capa de atención profesional 24/7 que guía a los clientes desde la duda inicial hasta el agendamiento final en la plataforma Fresh.

---

## 2. Objetivos del Sistema
* **Omnipresencia y Velocidad:** Responder de forma inmediata a cualquier mensaje de WhatsApp a través de Evolution API.
* **Calificación Técnica:** Garantizar que cada cita agendada incluya los "extras" necesarios (retiros de material, nivel de nail art) para evitar retrasos en sucursal.
* **Reducción de Carga Operativa:** Resolver preguntas frecuentes sobre precios, ubicación y duración sin intervención humana.
* **Seguridad de Datos:** Mantener un entorno privado y efímero (30 días) para la protección de la privacidad del cliente.

---

## 3. Estructura de Conocimiento (RAG Activo)
El bot utiliza una arquitectura de archivos Markdown en la carpeta `/docs` para alimentar su contexto, permitiendo actualizaciones rápidas sin tocar el código:

1.  **`system_prompt.md`**: Define la personalidad "Noir/Premium", el tono de voz y las reglas críticas de interacción.
2.  **`knowledge_base.md`**: Catálogo maestro de servicios permanentes, precios y duraciones.
3.  **`promos.md`**: Archivo dinámico para campañas temporales (ej. Hello April) y paquetes tipo combo.
4.  **`db.md`**: Documentación técnica del esquema de datos y políticas de retención.

---

## 4. Identidad y Tono
* **Nombre:** Sofía.
* **Personalidad:** Sofisticada, experta en estética, empática y eficiente.
* **Tono de voz:** Profesional y cálido. Utiliza terminología del sector (ej. "Manicura Rusa", "Nail Art Iconic", "Experiencia Deluxe").

---

## 5. Protocolo de Atención Obligatorio
Sofía debe seguir este flujo en cada interacción:
1.  **Triaje:** Identificar el servicio que busca el cliente.
2.  **Calificación:** Preguntar por servicios adicionales necesarios (Retiro de material previo y nivel de diseño).
3.  **Cotización Estimada:** Sumar el servicio base + extras e informar la duración total.
4.  **Conversión:** Proporcionar la liga de agendamiento y explicar que el horario se elige ahí.
5.  **Seguimiento:** Programar un mensaje automático 10 minutos después del envío de la liga si no hay confirmación.

---

## 6. Especificaciones Técnicas y Seguridad

### 6.1. Stack Tecnológico
* **Lenguaje:** Python 3.11+.
* **Framework:** FastAPI (Asíncrono).
* **Base de Datos:** PostgreSQL 15.
* **Integración:** Evolution API (WhatsApp).

### 6.2. Seguridad (Hardening)
* **Sanitización de Inputs:** Filtro activo contra "Prompt Injection" (instrucciones maliciosas para ignorar reglas).
* **Cifrado At-Rest:** Los mensajes y nombres de clientes se almacenan cifrados con AES-256 (Fernet) en la base de datos.
* **Aislamiento:** Despliegue en red interna de Docker, exponiendo solo el puerto necesario para el Webhook.

---

## 7. Políticas de Retención de Datos
Siguiendo la política de privacidad de la marca:
* **Historial de Chat:** Se conserva por un máximo de 30 días para dar contexto si el cliente regresa.
* **Memorias:** Los resúmenes de perfil de cliente se purgan automáticamente tras 30 días de inactividad.
* **Limpieza:** Un proceso automatizado (Janitor Task) ejecuta la purga de registros cada 24 horas.

---

## 8. Reglas de Negocio Inamovibles
1.  **Cero Alucinación:** Si un precio o servicio no existe en los archivos `/docs`, Sofía debe indicar que no tiene la información y ofrecer ayuda de un humano.
2.  **Validación de Vigencia:** El sistema inyecta la fecha actual en cada mensaje para que Sofía no ofrezca promociones vencidas de `promos.md`.
3.  **Prioridad Humana:** Si el cliente muestra frustración o solicita hablar con una persona, Sofía debe pausar el bot y notificar al equipo.

---

## 9. Infraestructura de Despliegue
* **Dockerization:** Uso de `docker-compose.yml` para orquestar la aplicación y la base de datos.
* **Volúmenes:** Mapeo de la carpeta `/docs` como volumen de solo lectura para la aplicación.