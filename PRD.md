# PRD: Vanessa - Asistente Virtual de Vanity Salon

| Metadato | Detalle |
| :--- | :--- |
| **Proyecto** | Chatbot WhatsApp "Vanessa" (RAG + Evolution API) |
| **Versión** | 1.0 |
| **Fecha** | 07 de Febrero, 2026 |
| **Estado** | Borrador Aprobado |
| **Dueño del Producto** | Vanity Salon |

---

## 1. Resumen Ejecutivo
Desarrollo de un agente de IA generativa para WhatsApp llamado **"Vanessa"**. El bot funcionará como una "recepcionista virtual premium", automatizando la atención al cliente de **Vanity Salon**. 

El sistema utilizará RAG (Retrieval-Augmented Generation) para consultar un catálogo de servicios limpio y actualizado, priorizando promociones vigentes ("Hello February"). Su objetivo principal es perfilar al cliente, resolver dudas y **redirigir tráfico cualificado al link de reserva** de la sucursal correcta.

## 2. Objetivos del Negocio
1.  **Reducir tiempos de respuesta:** Pasar de horas a segundos en respuestas de precios y disponibilidad.
2.  **Filtrado de Leads:** Evitar que el personal humano pierda tiempo en preguntas frecuentes (precios, ubicación, horarios).
3.  **Incremento de Reservas:** Aumentar la conversión guiando al usuario al enlace de Booking correcto según su ubicación.
4.  **Manejo de Crisis:** Canalizar quejas a un formulario externo para evitar malas experiencias públicas.

---

## 3. User Persona (La voz del Bot)

*   **Nombre:** Vanessa.
*   **Arquetipo:** *Clean Girl Aesthetic* / Mejor amiga experta en belleza.
*   **Tono:** Cálido, femenino, eficiente, usa "tú".
*   **Estilo de Escritura:**
    *   Uso moderado de emojis (✨, 🤍, 💅, 🌸).
    *   Respuestas concisas pero amables.
    *   Nunca suena robótica ni excesivamente formal ("Usted").

> **Ejemplo de Interacción:**
> *"¡Hola! 🤍 Claro que sí, para cabello maltratado el tratamiento 'Gloss Elixir' es una maravilla. ¿Te gustaría agendar en la sucursal Cima o Los Pinos? ✨"*

---

## 4. Alcance Funcional (Scope)

### ✅ 4.1. Consultoría de Servicios (Core)
*   **Motor de Recomendación:** El bot no solo lista precios; pregunta y recomienda.
    *   *Input:* "¿Qué me recomiendas para uñas?"
    *   *Output:* Sugiere opciones populares (ej: Rubber Shine) o promociones vigentes (ej: Classic Elegance - Febrero).
*   **Información Detallada:** Provee precio, duración y descripción basada estrictamente en la `knowledge_base`.

### ✅ 4.2. Gestión de Promociones (Lógica Temporal)
*   **Prioridad:** El bot debe priorizar la categoría **"💘 HELLO FEBRUARY 💘"** (contexto actual: Feb 2026).
*   **Filtrado Negativo:** Debe ignorar/ocultar activamente promociones de meses pasados (Navidad, Octubre, 2023, 2024, 2025) presentes en la data histórica.

### ✅ 4.3. Enrutamiento de Sucursales (Branch Routing)
*   Antes de entregar un enlace de reserva, el bot **debe** preguntar la preferencia de ubicación.
*   **Lógica:**
    *   Si Usuario elige "Sucursal A" $\rightarrow$ Enviar Link Booking A + Link Google Maps A.
    *   Si Usuario elige "Sucursal B" $\rightarrow$ Enviar Link Booking B + Link Google Maps B.
    *   Si Usuario pide "la más cercana" $\rightarrow$ Enviar ambas ubicaciones de Maps para que el usuario decida.

### ✅ 4.4. Información Operativa
*   **Métodos de Pago:** Informar (Efectivo, Tarjeta, Transferencia, Gift Cards).
*   **Estacionamiento:** Confirmar disponibilidad.
*   **Política de Cancelación:** Informar suavemente que se contactará para anticipos una vez agendada la cita.

### ✅ 4.5. Manejo de Excepciones (Hand-off)
*   **Quejas/Feedback Negativo:** Detectar sentimiento negativo y redirigir a **Formbricks** (u otro formulario) para gestión de crisis.
    *   *Script:* "Lamento mucho tu experiencia. Para darle seguimiento prioritario, por favor escríbenos aquí: [LINK]"
*   **Cotizaciones Personalizadas (Fotos):** Si el usuario envía una imagen (Media Message):
    *   *Acción:* Reconocer la imagen, indicar que la IA no cotiza diseños exactos y notificar que un humano revisará la foto para dar precio final.

---

## 5. Requisitos Técnicos

### 5.1. Stack Tecnológico
*   **Canal:** WhatsApp Business.
*   **Gateway:** Evolution API (Self-hosted o Cloud).
*   **Backend/Orquestador:** Node.js (Recomendado) o Python.
*   **IA / LLM:** OpenAI `gpt-4o-mini` (Balance costo/velocidad).
*   **Base de Datos Vectorial (RAG):** Pinecone, Supabase Vector, o In-Memory (si el JSON es < 2MB).

### 5.2. Ingesta de Datos (Data Pipeline)
El sistema debe procesar el archivo `services.json` con las siguientes reglas de limpieza antes de indexarlo:
1.  **Filtro de Estado:** Solo incluir items donde `status` == "Activo" (aunque el CSV tenga errores, esta es la primera barrera).
2.  **Filtro de Texto:** Excluir items cuyo `nombre` o `categoría` contenga palabras clave de fechas pasadas: "Navidad", "Diciembre", "Octubre", "2023", "2024", "2025".
3.  **Prioridad:** Taggear los items de "HELLO FEBRUARY" con metadata de alta prioridad para el retrieval.

### 5.3. Integraciones
*   **Google Maps:** Enlaces estáticos a las sucursales.
*   **Booking System:** Enlaces directos a la plataforma de agenda (ej: Booksy/Fresha) con parámetros de servicio si es posible (ej: `booksy.com/vanity?service=acrilico`).

---

## 6. Historias de Usuario (User Journeys)

### Flujo A: La Indecisa (Venta Consultiva)
1.  **Usuario:** "¿Qué promos tienen?"
2.  **Vanessa:** Detecta fecha (Feb 2026). Busca en categoría "HELLO FEBRUARY".
3.  **Vanessa:** "¡Hola! ✨ Por ser el mes del amor tenemos el paquete 'Classic Elegance' (Uñas + Pedi) en $1,250. ¿Te interesa ver algo de cabello también?"
4.  **Usuario:** "Solo uñas. ¿Dónde están?"
5.  **Vanessa:** "Tenemos sucursal en **Cima** y **Los Pinos**. ¿Cuál te queda mejor para pasarte la ubicación y agenda? 🤍"
6.  **Usuario:** "Cima".
7.  **Vanessa:** "Perfecto. Aquí está la ubicación de Cima: [MAPS_LINK]. Puedes agendar tu promo aquí: [BOOKING_LINK_CIMA] 💅"

### Flujo B: La Específica (Venta Directa)
1.  **Usuario:** "Precio de retiro de gelish".
2.  **Vanessa:** "El retiro de Gelish cuesta $100 y tardamos aprox 15 mins. ✨ ¿Te gustaría agendar?"
3.  **Usuario:** "Sí, en Los Pinos".
4.  **Vanessa:** "Súper. Aquí tienes la agenda directa de Los Pinos: [BOOKING_LINK_PINOS] 🌸".

### Flujo C: La Queja (Contención)
1.  **Usuario:** "Pésimo servicio, me dejaron esperando 30 minutos".
2.  **Vanessa:** "Lamento muchísimo escuchar eso 😔. Tu tiempo es muy valioso para nosotras. Por favor, ayúdanos llenando este formulario rápido para que la gerencia revise tu caso personalmente hoy mismo: [LINK_FORMBRICKS]. Gracias por darnos la oportunidad de mejorar."

---

## 7. Limitaciones (Out of Scope)
*   **No Agendamiento Directo:** El bot **no** tiene acceso de escritura al calendario ni disponibilidad en tiempo real. Solo provee el enlace.
*   **No Cobros:** No procesa pagos dentro de WhatsApp.
*   **No Reconocimiento de Imágenes:** No analiza la foto para decir "eso es un diseño francés", solo detecta que *es* una imagen.

## 8. Métricas de Éxito (KPIs)
*   **Tasa de Retención:** % de usuarios que completan el flujo hasta recibir el enlace.
*   **Hand-off Rate:** % de conversaciones que requieren intervención humana (objetivo < 20%).
*   **Satisfacción (Cualitativa):** Tono de las respuestas de los usuarios al final de la interacción.

---
**Aprobado por:** Marco Gallegos  
**Fecha:** 7 feb 2026
