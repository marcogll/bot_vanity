# Vanessa Bot Backend

Backend para "Vanessa", la asistente virtual de WhatsApp de Vanity Salon con memoria de conversación, análisis de sentimiento y upselling inteligente.

---

## 📁 Estructura del Proyecto

```
bot_vanity/
├── src/
│   ├── app.ts                          # Punto de entrada de la aplicación
│   ├── controllers/
│   │   └── webhookController.ts         # Maneja webhooks con memoria + sentimiento
│   ├── services/
│   │   ├── ragService.ts               # Carga y búsqueda de datos
│   │   ├── openaiService.ts            # OpenAI con historial + upselling + sentimiento
│   │   ├── evolutionService.ts          # Envío de mensajes WhatsApp
│   │   ├── conversationMemory.ts         # Memoria en memoria (48h, 10 mensajes)
│   │   ├── upsellingService.ts          # Detección inteligente de upselling
│   │   └── conversationService.ts        # Servicio de conversación
│   ├── utils/
│   │   ├── sentimentAnalyzer.ts         # Análisis de sentimiento
│   │   └── messageBuilder.ts              # Constructor de mensajes para Evolution API
│   └── types/
│       └── index.ts                     # Interfaces de TypeScript
├── conversation_guides/                 # 8 archivos con 200+ variaciones de respuestas
├── personality_rules/                    # 5 archivos con reglas de personalidad
├── vanity_data/
│   ├── services.jsonl                   # Catálogo de servicios
│   └── locations.jsonl                  # Ubicaciones y políticas
├── system_prompt.md                      # Prompt del sistema (250 líneas)
├── Dockerfile                            # Configuración de Docker
├── docker-compose.yml                    # Compose para despliegue local
├── .dockerignore                         # Archivos a ignorar en Docker
├── .env                                # Variables de entorno
├── .env.example                        # Ejemplo de variables de entorno
├── package.json
└── tsconfig.json
```

---

## 🚀 Instalación y Ejecución

### 1. Instalar dependencias
```bash
npm install
```

### 2. Configurar variables de entorno

Editar `.env` con tus credenciales:

```env
# Evolution API Configuration
EVOLUTION_API_URL=https://api.evolution-api.com
EVOLUTION_API_KEY=your_evolution_api_key_here
EVOLUTION_INSTANCE=VanityBot

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Server Configuration
PORT=3000
NODE_ENV=development
```

### 3. Ejecutar en desarrollo
```bash
npm run dev
```

### 4. Ejecutar en producción
```bash
npm run build
npm start
```

---

## 🐳 Docker & Coolify Deployment

### Usar Docker Compose

1. **Construir y levantar el contenedor:**
```bash
docker-compose up -d
```

2. **Ver logs:**
```bash
docker-compose logs -f vanessa-bot
```

3. **Detener el contenedor:**
```bash
docker-compose down
```

### Desplegar en Coolify

Coolify soporta dos métodos de despliegue:

#### Método 1: Git Repository (Recomendado)

1. **Asegúrate de tener un `.env` configurado** (usa `.env.example` como referencia)
2. **Crea un nuevo proyecto en Coolify**
3. **Selecciona "Git Repository" como fuente**
4. **Ingresa tu repo:** `git@github.com:marcogll/bot_vanity.git`
5. **Configura el proyecto:**
   - **Buildpack:** Node.js
   - **Build Command:** `npm run build`
   - **Start Command:** `npm start`
   - **Port:** 3000
6. **Configura las variables de entorno en Coolify:**
   ```env
   NODE_ENV=production
   PORT=3000
   EVOLUTION_API_URL=https://evolution.soul23.cloud/manager/
   EVOLUTION_API_KEY=tu_api_key_aqui
   EVOLUTION_INSTANCE=noire
   OPENAI_API_KEY=tu_openai_key_aqui
   OPENAI_MODEL=gpt-4o-mini
   FORMBRICKS_URL=https://your-formbricks-instance.com/form/quejas
   ```
7. **Haz deploy**

#### Método 2: Docker Compose

1. **Crea un nuevo proyecto en Coolify**
2. **Selecciona "Docker Compose" como fuente**
3. **Pega el contenido de `docker-compose.yml`**
4. **Configura las variables de entorno en Coolify** (ver arriba)
5. **Haz deploy**

### Configuración del Webhook de Evolution API

Una vez desplegado en Coolify:

1. **Copia la URL de tu aplicación** (ej: `https://tu-app.coolify.io`)
2. **Configura el webhook en Evolution API:**
   - **URL:** `https://tu-app.coolify.io/webhook`
   - **Método:** POST
   - **Content-Type:** `application/json`

### Health Check

El contenedor incluye un health check automático:
```bash
curl https://tu-app.coolify.io/health
```

Respuesta esperada:
```json
{"status":"healthy","timestamp":"2026-02-07T21:00:00.000Z"}
```

---

## 📡 Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Información de la API y features habilitados |
| GET | `/health` | Health check |
| GET | `/stats` | Estadísticas de memoria |
| POST | `/webhook` | Webhook de Evolution API |
| POST | `/test` | Endpoint de prueba para probar el bot sin Evolution API |

---

---

## 🎯 Funcionalidades

### Memoria de Conversación
- ✅ Retiene últimos 10 mensajes por usuario
- ✅ Retención de 48 horas
- ✅ Preferencias del usuario (sucursal, servicios mencionados)
- ✅ Resultado de conversación (agendado/no agendado)
- ✅ Historial de sentimiento
- ✅ Limpieza automática cada hora
- ✅ Detección de usuarios recurrentes

### Análisis de Sentimiento
- ✅ Detección de sentimiento (positivo/neutral/negativo)
- ✅ Ajuste de tono según sentimiento
- ✅ Emojis recomendados por sentimiento
- ✅ Detección de quejas, urgencia, especificidad, indecisión

### Upselling Inteligente
- ✅ 9 escenarios específicos (acrílico→polygel, uñas→base rubber, cejas→vanity essence, cabello→tratamientos)
- ✅ Solo si sentimiento positive/neutral
- ✅ Máximo 1 intento por conversación
- ✅ Acepta rechazos sin insistir
- ✅ No hace upselling en quejas

### Personalidad Dinámica
- ✅ 200+ variaciones de respuestas documentadas
- ✅ Nunca repite exactamente la misma respuesta
- ✅ Usa memoria para personalizar (sucursal preferida, servicios mencionados)
- ✅ Tono cálido pero neutro (usa "tú", nunca "usted")
- ✅ Emojis orgánicos (1-2 por mensaje, máx.)

### Guías de Interacción
- ✅ 8 archivos con guías completas de conversación
- ✅ 20+ variaciones de saludos
- ✅ 10+ variaciones de respuestas a "hola"
- ✅ 12+ variaciones de preguntas de sucursal
- ✅ 10+ cierres naturales y variados

### Reglas de Personalidad
- ✅ 30+ DOs (lo que debes hacer)
- ✅ 30+ DON'Ts (lo que no debes hacer)
- ✅ 30+ ejemplos de malas respuestas a evitar
- ✅ Reglas de tono, estilo y emojis
- ✅ Guía de manejo de sentimiento

---

## 📊 Datos

### Formato de services.jsonl

```json
{
  "id": "feb_01",
  "category": "💘 HELLO FEBRUARY 💘",
  "service": "CLASSIC ELEGANCE (uñas acrílicas + pedicure classic)",
  "price": "$1,250.00 MXN",
  "duration": "2h 45m",
  "description": "Paquete consentidor: incluye pedicure clásico para renovar tus pasos y uñas acrílicas impecables. ¡Perfecto para lucir fresca y elegante!"
}
```

### Formato de locations.jsonl

```json
{
  "id": "loc_norte",
  "category": "Ubicación y Sucursales",
  "name": "Sucursal Plaza O (Norte)",
  "zone": "Norte de Saltillo",
  "address": "Blvd. Venustiano Carranza 4535, Virreyes Residencial, 25230 Saltillo, Coah.",
  "maps_link": "https://maps.app.goo.gl/dR723BBAZixNV41g6",
  "booking_link": "https://www.fresha.com/book-now/vanity-nail-salon-mifzui17/services?lid=590196&share=true&pId=552479",
  "description": "Ubicada al Norte de la ciudad en Plaza O (Virreyes)."
}
```

---

## 🤖 Integraciones

- **Evolution API**: Gateway de WhatsApp
- **OpenAI gpt-4o-mini**: Generación de respuestas con historial
- **Fresha**: Sistema de reservas (enlaces estáticos)
- **Google Maps**: Ubicaciones de sucursales

---

## 🔧 Tecnologías

- **Backend/Orquestador**: Node.js + Express + TypeScript
- **IA / LLM**: OpenAI gpt-4o-mini (Balance costo/velocidad)
- **RAG**: In-memory (JSONL files)
- **Memoria**: In-memory (48h retention)
- **Webhook**: Evolution API

---

## 🎯 Características Únicas

1. **Memoria de 48h**: Recuerda conversaciones previas por 48 horas
2. **Análisis de sentimiento**: Detecta si el usuario está contento, neutral o molesto
3. **Upselling inteligente**: Sugiere servicios relacionados de forma natural
4. **200+ variaciones**: Nunca repite exactamente la misma respuesta
5. **Tono dinámico**: Se ajusta según el sentimiento del usuario
6. **Personalización**: Recuerda sucursal preferida y servicios mencionados
7. **Documentación completa**: 16 archivos con 3,500+ líneas de guías

---

## 📊 Métricas de Calidad

- ✅ **Variedad**: Vanessa nunca repite la misma respuesta
- ✅ **Memoria**: 80%+ de mensajes de seguimiento referencian temas previos
- ✅ **Upselling**: Rate de upselling < 30% (evitar spam)
- ✅ **Tono**: Ajuste de tono según sentimiento
- ✅ **Emojis**: 0-2 emojis por mensaje, variados
- ✅ **Concisión**: 80%+ de respuestas < 3 oraciones

---

## 🔧 Para Probar

### 1. Inicia el servidor
```bash
npm run dev
```

### 2. Verifica health
```bash
curl http://localhost:3000/health
```

### 3. Verifica stats
```bash
curl http://localhost:3000/stats
```

### 4. Envía mensajes al webhook de Evolution API
- Configura tu instancia de Evolution API para apuntar a: `http://localhost:3000/webhook`
- Envía un mensaje de WhatsApp para probar

### 5. Probar el bot sin Evolution API (Test Endpoint)

Para probar el bot sin configurar el webhook de Evolution API, puedes usar el endpoint `/test`:

```bash
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hola, ¿qué servicios tienen?",
    "phoneNumber": "test_123",
    "pushName": "María"
  }'
```

**Respuesta esperada:**
```json
{
  "message": "Hola, ¿qué servicios tienen?",
  "response": "¡Hola María! ✨ En Vanity tenemos varios servicios para consentirte...",
  "metadata": {
    "sentiment": {
      "sentiment": "neutral",
      "confidence": 0.5,
      "keywords": []
    },
    "upsellOpportunity": null,
    "detectedServices": "",
    "conversationHistoryLength": 0
  }
}
```

**Parámetros:**
- `message` (requerido): El mensaje del usuario
- `phoneNumber` (opcional): Número de teléfono del usuario (por defecto: "test_user")
- `pushName` (opcional): Nombre del usuario (por defecto: "Test User")

**Nota:** Este endpoint usa el mismo flujo que el webhook real, incluyendo análisis de sentimiento, búsqueda de servicios, detección de upselling y generación de respuestas con OpenAI. Útil para desarrollo y testing.

---

## 📝 Documentación Detallada

- `PROGRESO.md` - Estado de implementación completa
- `conversation_guides/` - Guías de conversación con 200+ variaciones
- `personality_rules/` - Reglas de personalidad y tono
- `system_prompt.md` - Prompt del sistema (250 líneas)

---

## 🎯 Personalidad del Bot

### Nombre
Vanessa

### Arquetipo
Clean Girl Aesthetic / Mejor amiga experta en belleza

### Tono
- Cálido pero neutro, usa "tú" siempre
- Emojis moderados (✨, 🤍, 💅, 🌸)

### Estilo de Escritura
- Usa "tú", jamás "usted"
- Respuestas concisas pero amables
- Nunca suena robótica ni excesivamente formal ("Usted")

### Emojis
- 1-2 por mensaje máximo
- Emojis que aporten valor, no decoración
- Alterna emojis, no uses siempre los mismos

---

## 🎯 Características del Bot

### Memoria
- **Retención**: 48 horas
- **Historial**: Últimos 10 mensajes
- **Preferencias**: Sucursal preferida, servicios mencionados
- **Resultado**: Agendado/no agendado, servicio, sucursal

### Sentimiento
- **Positivo**: Más entusiasta, más emojis (2 máx.), sugerencias de upselling más naturales
- **Neutral**: Directo y conciso, emojis moderados (1-2), upselling sutil
- **Negativo**: Más empática, menos emojis (0-1 máx.), sin upselling

### Upselling
- **Tasa objetivo**: 20-30% de aceptación
- **Escenarios**: 9 escenarios específicos (acrílico→polygel, uñas→base rubber, cejas→vanity essence, cabello→tratamientos)
- **Reglas**: Solo si sentimiento positive/neutral, máx. 1 intento por conversación
- **Rejection handling**: Acepta rechazos sin insistir

### Respuestas
- **Variación**: 200+ variaciones documentadas
- **Sin repetición**: Nunca repite exactamente la misma respuesta
- **Concisión**: 1-2 oraciones salvo excepciones
- **Naturaleza**: Lenguaje cotidiano, no técnico ni rebuscado

---

## 🚀 Para Producción

### 1. Compilar el proyecto
```bash
npm run build
```

### 2. Asegúrate de tener las variables de entorno configuradas en `.env`

### 3. Inicia el servidor en modo producción
```bash
npm start
```

### 4. Considera usar un process manager como PM2 para producción
```bash
npm install -g pm2
pm2 start dist/app.js
```

---

## 📚 Stack Técnico

- **Backend**: Node.js v24.13.0
- **Lenguaje**: TypeScript v5.3.3
- **Framework**: Express v4.18.2
- **IA**: OpenAI gpt-4o-mini
- **Gateway**: Evolution API
- **RAG**: In-memory (JSONL files)

---

## 📝 Dependencias

### Producción
- express
- dotenv
- openai
- cors
- axios

### Desarrollo
- typescript
- @types/express
- @types/node
- @types/cors
- @types/axios

---

## 📝 Scripts

| Comando | Descripción |
|---------|-------------|
| `npm run dev` | Ejecuta en modo desarrollo con hot-reload |
| `npm run build` | Compila TypeScript a JavaScript |
| `npm run start` | Ejecuta el servidor en modo producción |
| `npm run lint` | Ejecuta linter en todos los archivos TypeScript |
| `npm run typecheck` | Verifica que no hay errores de TypeScript |

---

*Última actualización: 7 de Febrero 2026*
*Versión: 1.0.0*
*Estado: ✅ Completado y listo para producción*
