# Guía de Desarrollo de Bots WhatsApp - Esqueleto Modular

## 📖 Índice

1. [Introducción](#introducción)
2. [Arquitectura del Esqueleto](#arquitectura-del-esqueleto)
3. [Prerrequisitos](#prerrequisitos)
4. [Paso 1: Configuración Inicial](#paso-1-configuración-inicial)
5. [Paso 2: Activar Features (Feature Flags)](#paso-2-activar-features-feature-flags)
6. [Paso 3: Configurar Datos del Cliente](#paso-3-configurar-datos-del-cliente)
7. [Paso 4: Personalizar Personalidad](#paso-4-personalizar-personalidad)
8. [Paso 5: Integraciones](#paso-5-integraciones)
9. [Paso 6: Testing](#paso-6-testing)
10. [Paso 7: Docker y Despliegue](#paso-7-docker-y-despliegue)
11. [Paso 8: Producción](#paso-8-producción)
12. [Casos de Uso Específicos](#casos-de-uso-específicos)
13. [Troubleshooting](#troubleshooting)
14. [Referencias](#referencias)

---

## 📖 Introducción

### ¿Qué es el Esqueleto Modular?

El **Esqueleto Modular** es una base de código reutilizable y configurable para crear bots de WhatsApp con IA generativa. Está diseñado para adaptarse rápidamente a diferentes tipos de clientes (negocios locales, servicios profesionales, soporte técnico, educación) mediante un sistema de **features opcionales** y **templates predefinidos**.

### Casos de Uso Soportados

- **Negocios Locales**: Salones de belleza, tiendas, restaurantes, gimnasios
- **Servicios Profesionales**: Doctores, abogados, consultores, arquitectos
- **Soporte Técnico**: SaaS, telecomunicaciones, servicios digitales
- **Educación/Cursos**: Escuelas, academias, cursos online, talleres

### Características Clave

✅ **Modular**: Cada feature es opcional y activable
✅ **Flexible**: Adaptable a cualquier tipo de negocio
✅ **Documentado**: Guías completas y ejemplos
✅ **Production-Ready**: Docker, Coolify, monitoreo
✅ **Escalable**: Arquitectura limpia y mantenible
✅ **Tested**: Tests automatizados y endpoints de prueba

---

## 🏗️ Arquitectura del Esqueleto

### Estructura del Proyecto

```
bot_skeleton/
├── src/
│   ├── core/                      # CORE (siempre incluido)
│   │   ├── app.ts                 # Express server
│   │   ├── config/                # Feature flags + config
│   │   │   ├── features.ts        # Habilitar/deshabilitar features
│   │   │   └── env.ts            # Variables de entorno
│   │   ├── types/
│   │   │   └── index.ts           # Types base
│   │   └── controllers/
│   │       └── webhookController.ts
│   ├── features/                  # MÓDULOS OPCIONALES
│   │   ├── conversation-memory/
│   │   │   ├── index.ts
│   │   │   ├── service.ts
│   │   │   └── types.ts
│   │   ├── sentiment-analysis/
│   │   │   ├── index.ts
│   │   │   ├── analyzer.ts
│   │   │   └── types.ts
│   │   ├── upselling/
│   │   │   ├── index.ts
│   │   │   ├── service.ts
│   │   │   └── rules.ts
│   │   ├── rag-service/
│   │   │   ├── index.ts
│   │   │   ├── service.ts
│   │   │   └── search.ts
│   │   ├── personality-engine/
│   │   │   ├── index.ts
│   │   │   ├── loader.ts         # Carga guías
│   │   │   └── types.ts
│   │   ├── evolution-api/
│   │   │   ├── index.ts
│   │   │   ├── client.ts
│   │   │   └── webhook.ts
│   │   └── complaint-handling/
│   │       ├── index.ts
│   │       └── formbricks.ts
│   ├── utils/
│   │   └── logger.ts
│   └── templates/                # PLANTILLAS POR TIPO DE CLIENTE
│       ├── local-business/
│       │   ├── system_prompt.md
│       │   ├── conversation_guides/
│       │   └── personality_rules/
│       ├── professional-service/
│       │   ├── system_prompt.md
│       │   ├── conversation_guides/
│       │   └── personality_rules/
│       ├── tech-support/
│       │   ├── system_prompt.md
│       │   ├── conversation_guides/
│       │   └── personality_rules/
│       └── education/
│           ├── system_prompt.md
│           ├── conversation_guides/
│           └── personality_rules/
├── client_data/                  # DATOS DEL CLIENTE (se reemplaza)
│   ├── services.jsonl           # Catálogo de servicios/productos
│   ├── locations.jsonl          # Ubicaciones
│   └── config.json              # Config específica del cliente
├── docs/
│   ├── CLIENT_CUSTOMIZATION.md   # Cómo personalizar por cliente
│   ├── FEATURE_FLAGS.md          # Configuración de features
│   ├── CLIENT_TEMPLATES.md       # Descripción de templates
│   └── API_REFERENCE.md          # Referencia de API
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── package.json
├── tsconfig.json
└── README.md
```

### Flujo de Datos

```
WhatsApp
    ↓
Evolution API (Webhook)
    ↓
WebhookController
    ↓
Features (opcional):
    ├─→ Conversation Memory
    ├─→ Sentiment Analysis
    ├─→ RAG Service
    ├─→ Upselling Service
    └─→ Personality Engine
    ↓
OpenAI (Generación de respuesta)
    ↓
Evolution API (Enviar mensaje)
    ↓
WhatsApp (Usuario recibe respuesta)
```

---

## ✅ Prerrequisitos

### Sistema Operativo
- Linux, macOS o Windows (WSL2 recomendado para Windows)

### Software Requerido

1. **Node.js** (v18 o superior)
   ```bash
   node --version  # v18.0.0 o superior
   ```

2. **npm** o **yarn** (npm v9+ o yarn v1.22+)
   ```bash
   npm --version  # v9.0.0 o superior
   ```

3. **Git**
   ```bash
   git --version  # v2.0 o superior
   ```

4. **Docker** (opcional, para producción)
   ```bash
   docker --version
   docker-compose --version
   ```

### Cuentas y APIs Requeridas

1. **Evolution API** - Gateway de WhatsApp
   - [Evolution API GitHub](https://github.com/EvolutionAPI/evolution-api)
   - Instalación propia o servicio cloud
   - API Key y nombre de instancia

2. **OpenAI** - Generación de respuestas
   - [OpenAI Platform](https://platform.openai.com/)
   - API Key
   - Modelo recomendado: `gpt-4o-mini` (balance costo/velocidad)

3. **Coolify** (opcional, para despliegue)
   - [Coolify.io](https://coolify.io/)
   - Servidor o VPS con Coolify instalado
   - Acceso a repositorio Git

### Conocimientos Requeridos

- **Básico**: JavaScript/TypeScript, Node.js, npm
- **Intermedio**: Express.js, async/await, APIs REST
- **Avanzado**: OpenAI API, Docker, CI/CD (opcional)

---

## 🚀 Paso 1: Configuración Inicial

### 1.1 Clonar o Copiar el Esqueleto

**Opción A: Desde repositorio Git**
```bash
git clone https://github.com/usuario/bot-skeleton.git mi-bot-cliente
cd mi-bot-cliente
```

**Opción B: Copiar manualmente**
```bash
# Copiar la carpeta bot_skeleton a tu proyecto
cp -r bot_skeleton mi-bot-cliente
cd mi-bot-cliente
```

### 1.2 Instalar Dependencias

```bash
npm install
```

Esto instalará las siguientes dependencias:

**Producción:**
- `express` - Framework web
- `dotenv` - Manejo de variables de entorno
- `openai` - Cliente de OpenAI
- `cors` - Soporte CORS
- `axios` - Cliente HTTP

**Desarrollo:**
- `typescript` - Compilador TypeScript
- `@types/*` - Types para Node.js y Express
- `tsx` - Ejecución directa de TypeScript

### 1.3 Configurar Variables de Entorno

Crear el archivo `.env`:

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales:

```env
# Server Configuration
PORT=3000
NODE_ENV=development

# Evolution API Configuration
EVOLUTION_API_URL=https://tu-evolution-api.com
EVOLUTION_API_KEY=tu_api_key_aqui
EVOLUTION_INSTANCE=nombre_instancia

# OpenAI Configuration
OPENAI_API_KEY=sk-tu_openai_key_aqui
OPENAI_MODEL=gpt-4o-mini

# Optional: Complaint Handling
# FORMBRICKS_URL=https://tu-formbricks.com/form/quejas
```

### 1.4 Verificar Instalación

**Verificar versiones:**
```bash
node --version
npm --version
```

**Verificar dependencias:**
```bash
ls node_modules/
```

**Verificar configuración:**
```bash
cat .env
```

### 1.5 Compilar y Ejecutar en Desarrollo

```bash
# Compilar TypeScript
npm run build

# Ejecutar en modo desarrollo (con hot-reload)
npm run dev
```

El servidor debería iniciarse en `http://localhost:3000`

### 1.6 Verificar Endpoints

Abre tu navegador o usa curl:

```bash
# Health check
curl http://localhost:3000/health

# API info
curl http://localhost:3000/

# Stats
curl http://localhost:3000/stats
```

**Respuesta esperada (/health):**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-08T12:00:00.000Z"
}
```

**Respuesta esperada (/):**
```json
{
  "name": "Bot API",
  "version": "1.0.0",
  "status": "running",
  "features": {
    "conversationMemory": true,
    "sentimentAnalysis": true,
    "upselling": true,
    "personalityEngine": true
  },
  "endpoints": {
    "webhook": "http://localhost:3000/webhook",
    "health": "http://localhost:3000/health",
    "stats": "http://localhost:3000/stats",
    "test": "http://localhost:3000/test (POST)"
  }
}
```

---

## ⚙️ Paso 2: Activar Features (Feature Flags)

### 2.1 Entender el Sistema de Features

El esqueleto usa un sistema de **feature flags** para activar/desactivar módulos según las necesidades del cliente.

### 2.2 Archivo de Configuración de Features

Ubicación: `src/core/config/features.ts`

```typescript
export const FEATURE_FLAGS = {
  // Memoria de conversación (48h, 10 mensajes)
  CONVERSATION_MEMORY: true,

  // Análisis de sentimiento (positivo/neutral/negativo)
  SENTIMENT_ANALYSIS: true,

  // Upselling inteligente
  UPSELLING: true,

  // RAG para búsqueda de servicios/productos
  RAG_SERVICE: true,

  // Motor de personalidad (guías, reglas, tono)
  PERSONALITY_ENGINE: true,

  // Integración con Evolution API (WhatsApp)
  EVOLUTION_API: true,

  // Manejo de quejas (Formbricks u otro)
  COMPLAINT_HANDLING: false
} as const;
```

### 2.3 Activar/Desactivar Features

**Para activar un feature:**
```typescript
CONVERSATION_MEMORY: true,
```

**Para desactivar un feature:**
```typescript
UPSELLING: false,
```

### 2.4 Dependencias entre Features

Algunos features dependen de otros:

| Feature | Dependencias |
|---------|--------------|
| `UPSELLING` | `SENTIMENT_ANALYSIS` |
| `PERSONALITY_ENGINE` | `SENTIMENT_ANALYSIS` |
| `COMPLAINT_HANDLING` | `SENTIMENT_ANALYSIS` |
| `RAG_SERVICE` | Ninguna |

### 2.5 Combinaciones Recomendadas

#### **Negocio Local (Salón, Tienda, Restaurante)**
```typescript
CONVERSATION_MEMORY: true,
SENTIMENT_ANALYSIS: true,
UPSELLING: true,
RAG_SERVICE: true,
PERSONALITY_ENGINE: true,
EVOLUTION_API: true,
COMPLAINT_HANDLING: true
```

#### **Servicio Profesional (Doctor, Abogado)**
```typescript
CONVERSATION_MEMORY: true,
SENTIMENT_ANALYSIS: true,
UPSELLING: false,
RAG_SERVICE: true,
PERSONALITY_ENGINE: true,
EVOLUTION_API: true,
COMPLAINT_HANDLING: false
```

#### **Soporte Técnico**
```typescript
CONVERSATION_MEMORY: true,
SENTIMENT_ANALYSIS: true,
UPSELLING: false,
RAG_SERVICE: true,
PERSONALITY_ENGINE: false,
EVOLUTION_API: true,
COMPLAINT_HANDLING: true
```

#### **Educación/Cursos**
```typescript
CONVERSATION_MEMORY: true,
SENTIMENT_ANALYSIS: true,
UPSELLING: true,
RAG_SERVICE: true,
PERSONALITY_ENGINE: true,
EVOLUTION_API: true,
COMPLAINT_HANDLING: false
```

### 2.6 Impacto en Rendimiento

| Feature | Impacto en Tiempo de Respuesta | Uso de Memoria |
|---------|--------------------------------|----------------|
| CONVERSATION_MEMORY | +10ms | +5MB por usuario |
| SENTIMENT_ANALYSIS | +20ms | +1MB |
| UPSELLING | +15ms | +2MB |
| RAG_SERVICE | +50ms (search) | +10MB (data) |
| PERSONALITY_ENGINE | +30ms | +5MB |
| EVOLUTION_API | +100ms (network) | 0MB |
| COMPLAINT_HANDLING | +5ms | 0MB |

### 2.7 Probar Features Individualmente

Después de cambiar los flags, reinicia el servidor:

```bash
# Ctrl+C para detener
npm run dev
```

Verifica que los features estén activados en `/`:

```bash
curl http://localhost:3000/
```

---

## 📊 Paso 3: Configurar Datos del Cliente

### 3.1 Crear Carpeta de Datos del Cliente

```bash
mkdir -p client_data
```

### 3.2 Crear `services.jsonl` (Catálogo de Servicios/Productos)

Formato JSONL (un JSON por línea):

```json
{"id": "srv_001", "category": "Uñas", "service": "Manicure Gelish", "price": "$350 MXN", "duration": "1h", "description": "Manicure con esmalte semipermanente que dura hasta 21 días."}
{"id": "srv_002", "category": "Uñas", "service": "Uñas Acrílicas", "price": "$550 MXN", "duration": "2h", "description": "Extensiones de acrílico con diseño básico incluido."}
{"id": "srv_003", "category": "Cabello", "service": "Corte Dama", "price": "$300 MXN", "duration": "45min", "description": "Corte y styling básico para cabello de dama."}
{"id": "srv_004", "category": "Cabello", "service": "Hair Botox", "price": "$800 MXN", "duration": "2h", "description": "Tratamiento reestructurante que nutre y repara el cabello a profundidad."}
```

**Estructura de cada línea:**
- `id`: Identificador único del servicio
- `category`: Categoría del servicio
- `service`: Nombre del servicio
- `price`: Precio del servicio
- `duration`: Duración aproximada
- `description`: Descripción del servicio

### 3.3 Crear `locations.jsonl` (Ubicaciones)

```json
{"id": "loc_001", "category": "Ubicación", "name": "Sucursal Centro", "zone": "Centro", "address": "Av. Principal 123, Centro, CP 00000", "maps_link": "https://maps.google.com/?q=Av.+Principal+123", "booking_link": "https://booking.com/sucursal-centro", "description": "Ubicada en el corazón de la ciudad."}
{"id": "loc_002", "category": "Ubicación", "name": "Sucursal Norte", "zone": "Norte", "address": "Blvd. Norte 456, Zona Norte, CP 11111", "maps_link": "https://maps.google.com/?q=Blvd.+Norte+456", "booking_link": "https://booking.com/sucursal-norte", "description": "Con estacionamiento gratuito."}
```

**Estructura de cada línea:**
- `id`: Identificador único
- `category`: Categoría (generalmente "Ubicación")
- `name`: Nombre de la sucursal
- `zone`: Zona geográfica
- `address`: Dirección física
- `maps_link`: Enlace a Google Maps
- `booking_link`: Enlace a sistema de reservas
- `description`: Descripción de la ubicación

### 3.4 Crear `config.json` (Configuración Específica)

```json
{
  "clientName": "Mi Cliente",
  "clientType": "local-business",
  "language": "es",
  "currency": "MXN",
  "timezone": "America/Mexico_City",
  "businessHours": {
    "monday": "09:00-19:00",
    "tuesday": "09:00-19:00",
    "wednesday": "09:00-19:00",
    "thursday": "09:00-19:00",
    "friday": "09:00-19:00",
    "saturday": "09:00-18:00",
    "sunday": "cerrado"
  },
  "contact": {
    "phone": "+525512345678",
    "email": "contacto@micliente.com",
    "website": "https://micliente.com"
  },
  "features": {
    "enablePromos": true,
    "enableBooking": true,
    "enablePayments": false
  }
}
```

### 3.5 Validar los Archivos JSONL

**Validar formato:**
```bash
# Verificar que sea JSON válido
cat client_data/services.jsonl | jq .
cat client_data/locations.jsonl | jq .
```

**Contar registros:**
```bash
wc -l client_data/services.jsonl
wc -l client_data/locations.jsonl
```

### 3.6 Cargar Datos en la Aplicación

El sistema carga automáticamente los archivos al iniciar el servidor. Verifica en los logs:

```
✅ Loaded 4 services and 2 locations
```

### 3.7 Probar Búsqueda de Servicios

Usa el endpoint `/test` para probar:

```bash
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{
    "message": "¿Cuánto cuesta el gelish?",
    "phoneNumber": "test_user",
    "pushName": "Test User"
  }'
```

La respuesta debería incluir información del servicio de gelish.

---

## 🎨 Paso 4: Personalizar Personalidad

### 4.1 Seleccionar Template de Cliente

El esqueleto incluye 4 templates predefinidos:

| Template | Descripción | Ideal Para |
|----------|-------------|------------|
| `local-business` | Tono cálido, emojis, upselling activo | Salones, tiendas, restaurantes |
| `professional-service` | Tono profesional, emojis mínimos | Doctores, abogados, consultores |
| `tech-support` | Tono técnico, conciso, sin upselling | SaaS, telecomunicaciones |
| `education` | Tono educativo, pacientes, ejemplos | Escuelas, academias, cursos |

### 4.2 Copiar Template a Cliente

**Ejemplo: Negocio local**
```bash
cp -r src/templates/local-business/* client_data/
```

Esto copiará:
- `system_prompt.md`
- `conversation_guides/`
- `personality_rules/`

### 4.3 Modificar `system_prompt.md`

El system prompt define la personalidad del bot. Edita según el cliente:

```markdown
# System Prompt para [Nombre del Cliente]

## Identidad del Bot
- **Nombre**: [Nombre del bot]
- **Arquetipo**: [Arquetipo - ej: "Mejor amiga experta", "Asistente profesional"]
- **Objetivo**: [Objetivo principal]

## Tono y Estilo
- Usa "tú" siempre, nunca "usted"
- [Descripción del tono]
- Emojis: [cantidad y tipos]
- Longitud de respuestas: [corto/medio/largo]

## Guías de Interacción
[Guías específicas del cliente]

## Escenarios de Manejo
[Escenarios específicos]

## Restricciones
- [Restricción 1]
- [Restricción 2]
```

### 4.4 Personalizar `conversation_guides/`

Copia y edita las guías según el cliente:

**Guías principales:**
- `greetings.md` - Saludos (20+ variaciones)
- `closing_conversations.md` - Cierres naturales
- `complaints_handling.md` - Manejo de quejas
- `upselling_scenarios.md` - Escenarios de upselling
- `services_inquiry.md` - Consultas de servicios
- `location_routing.md` - Enrutamiento a sucursales
- `promotions.md` - Promociones y ofertas

**Ejemplo: greetings.md**
```markdown
# Guía de Saludos - [Nombre del Bot]

## Saludos Iniciales
1. "¡Hola! ✨ Bienvenida a [Nombre del Negocio]. ¿Qué estás buscando hoy?"
2. "¡Holis! 🤍 ¿En qué te puedo ayudar?"
3. "¡Qué bueno que te escribas! 💅 ¿Buscas algo especial?"
[... más variaciones ...]
```

### 4.5 Personalizar `personality_rules/`

Edita las reglas de personalidad:

**Archivos principales:**
- `tone_and_style.md` - Tono, estilo, vocabulario
- `dos_and_donts.md` - Lo que se debe y no se debe hacer
- `emoji_usage.md` - Uso de emojis
- `sentiment_handling.md` - Manejo de sentimiento

**Ejemplo: tone_and_style.md**
```markdown
# Reglas de Tono y Estilo

## Características del Tono
- [Característica 1]
- [Característica 2]

## Vocabulario Apropiado
- [Palabra 1]
- [Palabra 2]

## Frases Permitidas
1. "¡Hola! ¿En qué te puedo ayudar?"
2. "¿Te gustaría agendar?"

## Frases Prohibidas
❌ "En qué puedo servirle hoy?" (demasiado formal)
❌ "Gracias por contactarnos" (genérico)
```

### 4.6 Validar Guías

Verifica que los archivos estén bien formados:

```bash
# Verificar archivos
ls -la client_data/conversation_guides/
ls -la client_data/personality_rules/

# Contar variaciones
grep -c "^1\." client_data/conversation_guides/greetings.md
```

### 4.7 Probar Personalidad

Usa el endpoint `/test` con diferentes mensajes:

```bash
# Saludo
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola", "phoneNumber": "test_user", "pushName": "María"}'

# Consulta
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Qué servicios tienen?", "phoneNumber": "test_user", "pushName": "María"}'

# Queja
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "El servicio fue terrible", "phoneNumber": "test_user", "pushName": "María"}'
```

Verifica que las respuestas sigan el tono y estilo definido.

---

## 🔗 Paso 5: Integraciones

### 5.1 Configurar Evolution API (WhatsApp)

#### 5.1.1 Instalar Evolution API

**Opción A: Docker (Recomendada)**
```bash
docker run -d \
  --name evolution-api \
  -p 8080:8080 \
  -e TZ=America/Mexico_City \
  evolution/evolution-api
```

**Opción B: Desde Código**
```bash
git clone https://github.com/EvolutionAPI/evolution-api.git
cd evolution-api
npm install
npm run start
```

#### 5.1.2 Crear Instancia de WhatsApp

Accede a la UI de Evolution API (http://localhost:8080) y:
1. Crea una nueva instancia
2. Escanea el QR con tu WhatsApp
3. Genera API Key
4. Copia el nombre de la instancia

#### 5.1.3 Configurar Webhook en Evolution API

En Evolution API, configura:
- **Webhook URL**: `https://tu-dominio.com/webhook`
- **Method**: POST
- **Events**: `messages.upsert`

#### 5.1.4 Configurar en el Bot

Edita `.env`:
```env
EVOLUTION_API_URL=https://tu-evolution-api.com
EVOLUTION_API_KEY=tu_api_key_aqui
EVOLUTION_INSTANCE=nombre_instancia
```

### 5.2 Configurar OpenAI

#### 5.2.1 Obtener API Key

1. Ve a [OpenAI Platform](https://platform.openai.com/)
2. Regístrate o inicia sesión
3. Ve a API Keys
4. Crea una nueva API Key
5. Copia la key

#### 5.2.2 Configurar en el Bot

Edita `.env`:
```env
OPENAI_API_KEY=sk-tu_openai_key_aqui
OPENAI_MODEL=gpt-4o-mini
```

#### 5.2.3 Configurar Formbricks (Opcional - Quejas)

Si tienes una instancia de Formbricks para manejar quejas:

```env
FORMBRICKS_URL=https://tu-formbricks.com/form/quejas
```

### 5.3 Probar Integraciones

#### 5.3.1 Probar Evolution API

```bash
# Verificar conexión
curl -H "apikey: tu_api_key" \
  https://tu-evolution-api.com/instance/connectionState/nombre_instancia
```

**Respuesta esperada:**
```json
{
  "instance": "nombre_instancia",
  "state": "open"
}
```

#### 5.3.2 Probar OpenAI

Usa el endpoint `/test`:

```bash
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hola, ¿qué servicios tienen?",
    "phoneNumber": "test_user",
    "pushName": "Test User"
  }'
```

Deberías recibir una respuesta generada por OpenAI.

#### 5.3.3 Probar Flujo Completo con WhatsApp

1. Envía un mensaje al número de WhatsApp conectado a Evolution API
2. Verifica que el bot responda
3. Verifica los logs del servidor

**Logs esperados:**
```
📨 Message from Usuario (+525512345678): Hola
📊 Sentiment: neutral (confidence: 0.00)
🧠 History: 0 messages, User: New
🤖 Calling OpenAI with 0 history messages, sentiment: neutral, temp: 0.7
✅ OpenAI response generated (150 chars)
📱 Sending message to Evolution API:
   Phone: 525512345678
   Text: ¡Hola! ✨ Bienvenida a [Negocio]. ¿Qué estás buscando hoy?
✅ Evolution API response: { success: true }
✅ Message sent to +525512345678
```

---

## 🧪 Paso 6: Testing

### 6.1 Endpoint de Test

El bot incluye un endpoint `/test` para probar sin Evolution API:

```bash
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hola, ¿qué servicios tienen?",
    "phoneNumber": "test_user",
    "pushName": "María"
  }'
```

**Respuesta esperada:**
```json
{
  "message": "Hola, ¿qué servicios tienen?",
  "response": "¡Hola María! ✨ En [Negocio] tenemos varios servicios...",
  "metadata": {
    "sentiment": {
      "sentiment": "neutral",
      "confidence": 0.0,
      "keywords": []
    },
    "upsellOpportunity": null,
    "detectedServices": "1. Manicure Gelish - $350 MXN\n2. Uñas Acrílicas - $550 MXN",
    "conversationHistoryLength": 0
  }
}
```

### 6.2 Probar Features Individuales

#### 6.2.1 Probar Memoria de Conversación

```bash
# Primer mensaje
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola", "phoneNumber": "user123", "pushName": "María"}'

# Segundo mensaje (debería recordar contexto)
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Cuánto cuesta el gelish?", "phoneNumber": "user123", "pushName": "María"}'

# Verificar stats
curl http://localhost:3000/stats
```

**Stats esperados:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-08T12:00:00.000Z",
  "memory": {
    "totalUsers": 1,
    "activeConversations": 1,
    "averageMessagesPerUser": 2,
    "conversationsCleaned": 0
  }
}
```

#### 6.2.2 Probar Análisis de Sentimiento

```bash
# Mensaje positivo
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "¡Excelente! Me encanta el servicio", "phoneNumber": "test_pos", "pushName": "Ana"}'

# Mensaje negativo
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Pésimo servicio, no volveré", "phoneNumber": "test_neg", "pushName": "Carlos"}'
```

Verifica en los logs:
```
📊 Sentiment: positive (confidence: 0.85)
```

#### 6.2.3 Probar Upselling

```bash
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quiero uñas acrílicas",
    "phoneNumber": "test_upsell",
    "pushName": "Laura"
  }'
```

Verifica en los logs:
```
💰 Upsell opportunity: acrílico → polygel
```

### 6.3 Probar Flujos Completos

#### 6.3.1 Flujo 1: Nuevo Cliente (Indeciso)

```bash
# Mensaje 1
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola, no sé qué hacer", "phoneNumber": "flow1", "pushName": "Sofía"}'

# Mensaje 2
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Cuéntame qué promos tienen", "phoneNumber": "flow1", "pushName": "Sofía"}'

# Mensaje 3
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "La paquete de uñas", "phoneNumber": "flow1", "pushName": "Sofía"}'

# Mensaje 4
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "En la sucursal norte", "phoneNumber": "flow1", "pushName": "Sofía"}'
```

#### 6.3.2 Flujo 2: Cliente Recurrente (Específico)

```bash
# Mensaje 1
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola, quiero agendar gelish", "phoneNumber": "flow2", "pushName": "Ana"}'

# Mensaje 2
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "En centro", "phoneNumber": "flow2", "pushName": "Ana"}'
```

#### 6.3.3 Flujo 3: Queja

```bash
curl -X POST http://localhost:3000/test \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Pésimo servicio, me dejaron esperando 30 minutos",
    "phoneNumber": "flow3",
    "pushName": "Roberto"
  }'
```

Verifica que:
- El tono sea empático
- No haga upselling
- Redirija al formulario de quejas

### 6.4 Verificar Logs

Monitorea los logs en tiempo real:

```bash
# En otra terminal
npm run dev
```

Busca:
- `📊 Sentiment:`
- `💰 Upsell opportunity:`
- `🧠 History:`
- `✅ Response sent to`

### 6.5 Debugging Tips

#### Si el bot no responde:

1. **Verificar servidor:**
   ```bash
   curl http://localhost:3000/health
   ```

2. **Verificar logs:**
   Busca errores en `❌` o warnings en `⚠️`

3. **Verificar variables de entorno:**
   ```bash
   cat .env
   ```

4. **Verificar OpenAI:**
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer sk-tu_key"
   ```

5. **Verificar Evolution API:**
   ```bash
   curl -H "apikey: tu_api_key" \
     https://tu-evolution-api.com/instance/connectionState/nombre_instancia
   ```

#### Si la personalidad no funciona:

1. **Verificar que los archivos existan:**
   ```bash
   ls -la client_data/
   ls -la client_data/conversation_guides/
   ls -la client_data/personality_rules/
   ```

2. **Verificar feature flags:**
   ```bash
   cat src/core/config/features.ts
   ```

3. **Reiniciar servidor:**
   ```bash
   # Ctrl+C
   npm run dev
   ```

#### Si la memoria no funciona:

1. **Verificar que el feature esté activado:**
   ```bash
   grep "CONVERSATION_MEMORY" src/core/config/features.ts
   ```

2. **Verificar stats:**
   ```bash
   curl http://localhost:3000/stats
   ```

---

## 🐳 Paso 7: Docker y Despliegue

### 7.1 Dockerfile

El archivo `Dockerfile` está optimizado para producción:

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/client_data ./client_data
COPY --from=builder /app/system_prompt.md ./

USER node

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

CMD ["node", "dist/app.js"]
```

### 7.2 docker-compose.yml

Para desarrollo y testing local:

```yaml
version: '3.8'

services:
  bot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: bot-cliente
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - PORT=3000
      - EVOLUTION_API_URL=${EVOLUTION_API_URL}
      - EVOLUTION_API_KEY=${EVOLUTION_API_KEY}
      - EVOLUTION_INSTANCE=${EVOLUTION_INSTANCE}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=${OPENAI_MODEL:-gpt-4o-mini}
      - FORMBRICKS_URL=${FORMBRICKS_URL}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "node", "-e", "require('http').get('http://localhost:3000/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s
    networks:
      - bot-network

networks:
  bot-network:
    driver: bridge
```

### 7.3 Construir Imagen Docker

```bash
# Construir imagen
docker build -t bot-cliente:latest .

# Verificar imagen
docker images | grep bot-cliente
```

### 7.4 Ejecutar con Docker Compose

```bash
# Iniciar contenedor
docker-compose up -d

# Ver logs
docker-compose logs -f bot

# Verificar contenedor
docker ps | grep bot-cliente

# Probar health check
docker exec bot-cliente wget -qO- http://localhost:3000/health
```

**Health check esperado:**
```json
{"status":"healthy","timestamp":"2026-02-08T12:00:00.000Z"}
```

### 7.5 Detener Contenedor

```bash
# Detener contenedor
docker-compose down

# Detener y eliminar volúmenes
docker-compose down -v
```

### 7.6 Desplegar en Coolify

#### 7.6.1 Método 1: Git Repository (Recomendado)

**Paso 1:** Preparar repositorio

```bash
# Inicializar git (si aún no está)
git init
git add .
git commit -m "Initial commit"

# Subir a GitHub/GitLab
git remote add origin https://github.com/usuario/bot-cliente.git
git push -u origin main
```

**Paso 2:** Crear proyecto en Coolify

1. Ve a tu instancia de Coolify
2. Crea un nuevo proyecto
3. Selecciona "Git Repository"
4. Ingresa tu repo URL
5. Configura:
   - **Buildpack:** Node.js
   - **Build Command:** `npm run build`
   - **Start Command:** `npm start`
   - **Port:** 3000

**Paso 3:** Configurar variables de entorno en Coolify

En Coolify, agrega las siguientes variables:

```env
NODE_ENV=production
PORT=3000
EVOLUTION_API_URL=https://tu-evolution-api.com
EVOLUTION_API_KEY=tu_api_key_aqui
EVOLUTION_INSTANCE=nombre_instancia
OPENAI_API_KEY=sk-tu_openai_key_aqui
OPENAI_MODEL=gpt-4o-mini
FORMBRICKS_URL=https://tu-formbricks.com/form/quejas
```

**Paso 4:** Hacer deploy

1. Click en "Deploy"
2. Espera a que termine el build
3. Copia la URL de tu aplicación (ej: `https://bot-cliente.tu-dominio.com`)

**Paso 5:** Configurar webhook en Evolution API

En Evolution API, configura:
- **Webhook URL:** `https://bot-cliente.tu-dominio.com/webhook`
- **Method:** POST
- **Events:** `messages.upsert`

#### 7.6.2 Método 2: Docker Compose

**Paso 1:** Crear proyecto en Coolify

1. Crea un nuevo proyecto
2. Selecciona "Docker Compose"
3. Pega el contenido de `docker-compose.yml`

**Paso 2:** Configurar variables de entorno

Agrega las mismas variables que en el método 1.

**Paso 3:** Hacer deploy

Click en "Deploy" y espera.

### 7.7 Verificar Despliegue

**Probar health check:**
```bash
curl https://bot-cliente.tu-dominio.com/health
```

**Probar API info:**
```bash
curl https://bot-cliente.tu-dominio.com/
```

**Probar webhook con Evolution API:**

1. Envía un mensaje al número de WhatsApp
2. Verifica que el bot responda
3. Verifica logs en Coolify

### 7.8 Monitoreo

**Ver logs en Coolify:**
- Ve a tu proyecto
- Click en "Logs"
- Monitorea en tiempo real

**Monitorear con Docker (local):**
```bash
docker logs -f bot-cliente
```

**Ver recursos:**
```bash
docker stats bot-cliente
```

---

## 🚀 Paso 8: Producción

### 8.1 Optimizar para Producción

#### 8.1.1 Compilar TypeScript

```bash
npm run build
```

Esto crea la carpeta `dist/` con JavaScript compilado.

#### 8.1.2 Configurar Variables de Entorno

Crear `.env.production`:

```env
NODE_ENV=production
PORT=3000
EVOLUTION_API_URL=https://tu-evolution-api.com
EVOLUTION_API_KEY=tu_api_key_produccion
EVOLUTION_INSTANCE=nombre_instancia_produccion
OPENAI_API_KEY=sk-tu_openai_key_produccion
OPENAI_MODEL=gpt-4o-mini
FORMBRICKS_URL=https://tu-formbricks.com/form/quejas
```

#### 8.1.3 Configurar PM2 (Opcional)

PM2 es un process manager para producción:

```bash
# Instalar PM2 globalmente
npm install -g pm2

# Iniciar con PM2
pm2 start dist/app.js --name bot-cliente

# Guardar configuración
pm2 save

# Configurar para iniciar al boot
pm2 startup
```

**Monitorear con PM2:**
```bash
pm2 list
pm2 logs bot-cliente
pm2 monit
```

### 8.2 Configurar Nginx (Opcional)

Si usas Nginx como reverse proxy:

```nginx
server {
    listen 80;
    server_name bot-cliente.tu-dominio.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 8.3 Configurar SSL con Let's Encrypt (Opcional)

```bash
# Instalar certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d bot-cliente.tu-dominio.com

# Renovación automática
sudo certbot renew --dry-run
```

### 8.4 Monitoreo y Logs

#### 8.4.1 Logs del Servidor

```bash
# Ver logs en tiempo real
pm2 logs bot-cliente

# Ver logs de errores
pm2 logs bot-cliente --err

# Guardar logs
pm2 logs bot-cliente --lines 1000 > bot-logs.txt
```

#### 8.4.2 Métricas de Performance

```bash
# Uso de CPU y memoria
pm2 monit

# Con Docker
docker stats bot-cliente
```

### 8.5 Actualizaciones

#### 8.5.1 Actualizar Dependencias

```bash
# Ver dependencias desactualizadas
npm outdated

# Actualizar dependencias
npm update

# Actualizar todas las dependencias
npx npm-check-updates -u
npm install
```

#### 8.5.2 Hacer Deploy de Actualizaciones

**Con PM2:**
```bash
# Detener
pm2 stop bot-cliente

# Actualizar código
git pull
npm install
npm run build

# Iniciar
pm2 start dist/app.js --name bot-cliente
```

**Con Docker:**
```bash
# Reconstruir imagen
docker-compose build

# Reiniciar contenedor
docker-compose up -d
```

**Con Coolify:**
1. Actualiza el código en tu repo
2. Click en "Redeploy" en Coolify

### 8.6 Backup y Restore

#### 8.6.1 Backup de Datos del Cliente

```bash
# Crear backup
tar -czf client_data_backup_$(date +%Y%m%d).tar.gz client_data/

# Guardar backup en ubicación segura
mv client_data_backup_*.tar.gz /backups/
```

#### 8.6.2 Backup de Configuración

```bash
# Backup de .env
cp .env .env.backup

# Backup de configuración del cliente
cp client_data/config.json client_data/config.json.backup
```

#### 8.6.3 Restore

```bash
# Restore datos del cliente
tar -xzf /backups/client_data_backup_20260208.tar.gz

# Restore configuración
cp .env.backup .env
```

### 8.7 Troubleshooting en Producción

#### Problema: Bot no responde

**Diagnóstico:**
```bash
# Verificar que el proceso esté corriendo
pm2 list

# Ver logs de errores
pm2 logs bot-cliente --err

# Verificar health check
curl http://localhost:3000/health
```

**Solución:**
```bash
# Reiniciar PM2
pm2 restart bot-cliente

# O con Docker
docker-compose restart bot
```

#### Problema: Conexión con Evolution API

**Diagnóstico:**
```bash
# Verificar conexión
curl -H "apikey: tu_api_key" \
  https://tu-evolution-api.com/instance/connectionState/nombre_instancia
```

**Solución:**
- Verificar que Evolution API esté corriendo
- Verificar API Key e instancia
- Verificar webhook URL

#### Problema: Error de OpenAI

**Diagnóstico:**
```bash
# Verificar API Key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer sk-tu_key"
```

**Solución:**
- Verificar API Key
- Verificar cuota de OpenAI
- Verificar modelo configurado

### 8.8 Seguridad

#### 8.8.1 Proteger Variables de Entorno

Nunca commitear `.env`:
```bash
# Agregar a .gitignore
echo ".env" >> .gitignore
echo ".env.production" >> .gitignore
```

#### 8.8.2 Configurar CORS

En `src/app.ts`:
```typescript
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['*'],
  methods: ['GET', 'POST'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
```

#### 8.8.3 Rate Limiting

```bash
# Instalar express-rate-limit
npm install express-rate-limit

# Agregar en app.ts
import rateLimit from 'express-rate-limit';

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutos
  max: 100 // máximo 100 requests
});

app.use('/api/', limiter);
```

---

## 🎓 Casos de Uso Específicos

### Caso 1: Negocio Local (Salón de Belleza)

#### Configuración de Features
```typescript
const FEATURE_FLAGS = {
  CONVERSATION_MEMORY: true,
  SENTIMENT_ANALYSIS: true,
  UPSELLING: true,
  RAG_SERVICE: true,
  PERSONALITY_ENGINE: true,
  EVOLUTION_API: true,
  COMPLAINT_HANDLING: true
};
```

#### Personalidad
- **Tono:** Cálido, amigable, usa "tú"
- **Emojis:** 1-2 por mensaje (✨, 🤍, 💅)
- **Arquetipo:** Mejor amiga experta en belleza

#### Upselling Configurado
- Acrílico → Polygel
- Uñas → Base rubber/Vitamina
- Cejas → Vanity essence
- Cabello → Hair botox/Gloss elixir

#### Datos del Cliente
**services.jsonl:**
```json
{"id": "feb_01", "category": "💘 PROMO FEBRERO", "service": "Paquete Elegancia (Uñas + Pedi)", "price": "$1,250.00 MXN", "duration": "2h 30m", "description": "Paquete consentidor con uñas acrílicas y pedicure clásico."}
{"id": "nails_01", "category": "Uñas", "service": "Manicure Gelish", "price": "$350.00 MXN", "duration": "1h", "description": "Manicure con esmalte semipermanente que dura hasta 21 días."}
{"id": "nails_02", "category": "Uñas", "service": "Uñas Acrílicas", "price": "$550.00 MXN", "duration": "2h", "description": "Extensiones de acrílico con diseño básico incluido."}
```

**locations.jsonl:**
```json
{"id": "loc_001", "category": "Ubicación", "name": "Sucursal Centro", "zone": "Centro", "address": "Av. Principal 123, Centro", "maps_link": "https://maps.app.goo.gl/abc123", "booking_link": "https://booking.com/centro", "description": "Ubicada en el corazón de la ciudad."}
```

### Caso 2: Servicio Profesional (Doctor)

#### Configuración de Features
```typescript
const FEATURE_FLAGS = {
  CONVERSATION_MEMORY: true,
  SENTIMENT_ANALYSIS: true,
  UPSELLING: false, // No upselling
  RAG_SERVICE: true,
  PERSONALITY_ENGINE: true,
  EVOLUTION_API: true,
  COMPLAINT_HANDLING: false
};
```

#### Personalidad
- **Tono:** Profesional, empático, usa "tú"
- **Emojis:** 0-1 por mensaje (🤍)
- **Arquetipo:** Asistente médico empático

#### Datos del Cliente
**services.jsonl:**
```json
{"id": "cons_001", "category": "Consultas", "service": "Consulta General", "price": "$500.00 MXN", "duration": "30min", "description": "Consulta médica general para evaluación de síntomas."}
{"id": "exam_001", "category": "Exámenes", "service": "Análisis Clínico", "price": "$350.00 MXN", "duration": "15min", "description": "Análisis de sangre básico con resultados en 24h."}
```

### Caso 3: Soporte Técnico (SaaS)

#### Configuración de Features
```typescript
const FEATURE_FLAGS = {
  CONVERSATION_MEMORY: true,
  SENTIMENT_ANALYSIS: true,
  UPSELLING: false,
  RAG_SERVICE: true,
  PERSONALITY_ENGINE: false, // Tono técnico
  EVOLUTION_API: true,
  COMPLAINT_HANDLING: true
};
```

#### Personalidad
- **Tono:** Técnico, conciso, directo
- **Emojis:** Ninguno
- **Arquetipo:** Soporte técnico eficiente

#### Datos del Cliente
**services.jsonl:**
```json
{"id": "plan_001", "category": "Planes", "service": "Plan Básico", "price": "$299.00 MXN/mes", "duration": "Mensual", "description": "Incluye 5 usuarios, 10GB de almacenamiento y soporte por email."}
{"id": "feat_001", "category": "Características", "service": "Backup Automático", "price": "$50.00 MXN/mes", "duration": "Mensual", "description": "Backup diario de todos tus datos con retención de 30 días."}
```

### Caso 4: Educación (Academia de Cursos)

#### Configuración de Features
```typescript
const FEATURE_FLAGS = {
  CONVERSATION_MEMORY: true,
  SENTIMENT_ANALYSIS: true,
  UPSELLING: true,
  RAG_SERVICE: true,
  PERSONALITY_ENGINE: true,
  EVOLUTION_API: true,
  COMPLAINT_HANDLING: false
};
```

#### Personalidad
- **Tono:** Educativo, paciente, usa "tú"
- **Emojis:** 1-2 por mensaje (📚, ✨, 🎓)
- **Arquetipo:** Tutor amigable

#### Datos del Cliente
**services.jsonl:**
```json
{"id": "course_001", "category": "Cursos", "service": "Curso de Programación", "price": "$2,500.00 MXN", "duration": "8 semanas", "description": "Aprende programación desde cero con proyectos prácticos."}
{"id": "course_002", "category": "Cursos", "service": "Curso de Diseño Gráfico", "price": "$2,000.00 MXN", "duration": "6 semanas", "description": "Domina las herramientas de diseño gráfico profesional."}
```

---

## 🔧 Troubleshooting

### Problema: Servidor no inicia

**Síntomas:**
- `npm run dev` falla
- Error en logs: `EADDRINUSE: address already in use`

**Soluciones:**

1. **Cambiar puerto:**
   ```bash
   # En .env
   PORT=3001
   ```

2. **Matar proceso que usa el puerto:**
   ```bash
   # En Linux/Mac
   lsof -ti:3000 | xargs kill -9

   # En Windows
   netstat -ano | findstr :3000
   taskkill /PID <PID> /F
   ```

3. **Reiniciar servidor:**
   ```bash
   npm run dev
   ```

### Problema: Bot no responde en WhatsApp

**Síntomas:**
- Envías mensaje pero no recibes respuesta
- No hay logs en el servidor

**Soluciones:**

1. **Verificar webhook en Evolution API:**
   - Ve a la UI de Evolution API
   - Verifica que la URL del webhook sea correcta
   - Verifica que el evento `messages.upsert` esté activado

2. **Verificar que el servidor esté accesible:**
   ```bash
   # Si está en Coolify
   curl https://tu-dominio.com/health

   # Si está en local (necesita ngrok o similar)
   curl http://localhost:3000/health
   ```

3. **Verificar logs del servidor:**
   ```bash
   pm2 logs bot-cliente
   # o
   docker logs -f bot-cliente
   ```

4. **Probar con el endpoint /test:**
   ```bash
   curl -X POST http://localhost:3000/test \
     -H "Content-Type: application/json" \
     -d '{"message": "Hola", "phoneNumber": "test_user", "pushName": "Test"}'
   ```

### Problema: OpenAI error 401

**Síntomas:**
- Error: `Error: Incorrect API key provided`
- Logs: `❌ Error calling OpenAI`

**Soluciones:**

1. **Verificar API Key:**
   ```bash
   cat .env | grep OPENAI_API_KEY
   ```

2. **Verificar que la key sea válida:**
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer sk-tu_key"
   ```

3. **Regenerar API Key:**
   - Ve a [OpenAI Platform](https://platform.openai.com/)
   - Ve a API Keys
   - Crea una nueva key
   - Actualiza `.env`

### Problema: Evolution API error 401

**Síntomas:**
- Error: `Unauthorized`
- Logs: `❌ Error sending message to Evolution API`

**Soluciones:**

1. **Verificar API Key:**
   ```bash
   cat .env | grep EVOLUTION_API_KEY
   ```

2. **Verificar instancia:**
   ```bash
   curl -H "apikey: tu_api_key" \
     https://tu-evolution-api.com/instance/fetchInstances
   ```

3. **Regenerar API Key:**
   - Ve a la UI de Evolution API
   - Genera una nueva API Key
   - Actualiza `.env`

### Problema: La memoria no funciona

**Síntomas:**
- El bot no recuerda conversaciones previas
- `conversationHistoryLength` siempre es 0

**Soluciones:**

1. **Verificar feature flag:**
   ```bash
   cat src/core/config/features.ts | grep CONVERSATION_MEMORY
   ```
   Debe ser `true`.

2. **Verificar stats:**
   ```bash
   curl http://localhost:3000/stats
   ```
   Debería mostrar usuarios y mensajes.

3. **Reiniciar servidor:**
   ```bash
   pm2 restart bot-cliente
   ```

### Problema: El análisis de sentimiento no funciona

**Síntomas:**
- El tono no se ajusta según el sentimiento
- `sentiment` siempre es `neutral`

**Soluciones:**

1. **Verificar feature flag:**
   ```bash
   cat src/core/config/features.ts | grep SENTIMENT_ANALYSIS
   ```
   Debe ser `true`.

2. **Probar con mensajes específicos:**
   ```bash
   # Mensaje positivo
   curl -X POST http://localhost:3000/test \
     -H "Content-Type: application/json" \
     -d '{"message": "¡Excelente! Me encanta", "phoneNumber": "test_pos", "pushName": "Test"}'

   # Mensaje negativo
   curl -X POST http://localhost:3000/test \
     -H "Content-Type: application/json" \
     -d '{"message": "Pésimo servicio", "phoneNumber": "test_neg", "pushName": "Test"}'
   ```

3. **Verificar logs:**
   Busca `📊 Sentiment:` en los logs.

### Problema: El upselling no funciona

**Síntomas:**
- El bot nunca sugiere productos/servicios adicionales
- `upsellOpportunity` siempre es `null`

**Soluciones:**

1. **Verificar feature flags:**
   ```bash
   cat src/core/config/features.ts | grep UPSELLING
   cat src/core/config/features.ts | grep SENTIMENT_ANALYSIS
   ```
   Ambos deben ser `true`.

2. **Probar con triggers de upselling:**
   ```bash
   curl -X POST http://localhost:3000/test \
     -H "Content-Type: application/json" \
     -d '{"message": "Quiero uñas acrílicas", "phoneNumber": "test_upsell", "pushName": "Test"}'
   ```

3. **Verificar logs:**
   Busca `💰 Upsell opportunity:` en los logs.

### Problema: RAG no encuentra servicios

**Síntomas:**
- El bot no devuelve información de servicios
- `detectedServices` está vacío

**Soluciones:**

1. **Verificar que los archivos existan:**
   ```bash
   ls -la client_data/services.jsonl
   ls -la client_data/locations.jsonl
   ```

2. **Verificar formato JSONL:**
   ```bash
   cat client_data/services.jsonl | jq .
   ```
   Debe ser JSON válido.

3. **Verificar carga de datos:**
   Busca en los logs: `✅ Loaded X services and Y locations`

4. **Probar búsqueda:**
   ```bash
   curl -X POST http://localhost:3000/test \
     -H "Content-Type: application/json" \
     -d '{"message": "¿Qué servicios de uñas tienen?", "phoneNumber": "test_rag", "pushName": "Test"}'
   ```

### Problema: Docker build falla

**Síntomas:**
- `docker build` falla con error
- `docker-compose up` falla

**Soluciones:**

1. **Limpiar caché de Docker:**
   ```bash
   docker system prune -a
   ```

2. **Verificar Dockerfile:**
   ```bash
   cat Dockerfile
   ```
   Verifica que las rutas sean correctas.

3. **Construir sin caché:**
   ```bash
   docker build --no-cache -t bot-cliente:latest .
   ```

4. **Verificar logs de build:**
   ```bash
   docker build -t bot-cliente:latest . 2>&1 | tee build.log
   cat build.log
   ```

### Problema: Despliegue en Coolify falla

**Síntomas:**
- Build falla en Coolify
- Aplicación no inicia después del deploy

**Soluciones:**

1. **Verificar logs en Coolify:**
   - Ve a tu proyecto
   - Click en "Logs"
   - Busca errores

2. **Verificar variables de entorno:**
   - Ve a "Environment Variables"
   - Verifica que todas las variables estén configuradas

3. **Rehacer deploy:**
   - Click en "Redeploy"

4. **Verificar health check:**
   ```bash
   curl https://tu-dominio.com/health
   ```

---

## 📚 Referencias

### API Reference

#### Endpoints

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| GET | `/` | Información de la API y features habilitados | No |
| GET | `/health` | Health check | No |
| GET | `/stats` | Estadísticas de memoria | No |
| POST | `/webhook` | Webhook de Evolution API | No |
| POST | `/test` | Endpoint de prueba (sin Evolution API) | No |

#### `/test` Endpoint

**Request:**
```json
{
  "message": "Hola, ¿qué servicios tienen?",
  "phoneNumber": "test_user",
  "pushName": "María"
}
```

**Response:**
```json
{
  "message": "Hola, ¿qué servicios tienen?",
  "response": "¡Hola María! ✨ En [Negocio] tenemos varios servicios...",
  "metadata": {
    "sentiment": {
      "sentiment": "neutral",
      "confidence": 0.5,
      "keywords": []
    },
    "upsellOpportunity": null,
    "detectedServices": "1. Manicure Gelish - $350 MXN\n2. Uñas Acrílicas - $550 MXN",
    "conversationHistoryLength": 0
  }
}
```

### Configuración Avanzada

#### Feature Flags Detalladas

| Feature | Descripción | Dependencias | Impacto |
|---------|-------------|--------------|---------|
| `CONVERSATION_MEMORY` | Memoria de 48h, últimos 10 mensajes | Ninguna | +10ms, +5MB/user |
| `SENTIMENT_ANALYSIS` | Análisis de sentimiento (pos/neu/neg) | Ninguna | +20ms, +1MB |
| `UPSELLING` | Detección de oportunidades de venta | `SENTIMENT_ANALYSIS` | +15ms, +2MB |
| `RAG_SERVICE` | Búsqueda en catálogo de servicios | Ninguna | +50ms, +10MB |
| `PERSONALITY_ENGINE` | Motor de personalidad con guías | `SENTIMENT_ANALYSIS` | +30ms, +5MB |
| `EVOLUTION_API` | Integración con WhatsApp | Ninguna | +100ms, 0MB |
| `COMPLAINT_HANDLING` | Manejo de quejas (Formbricks) | `SENTIMENT_ANALYSIS` | +5ms, 0MB |

#### Variables de Entorno

| Variable | Requerido | Descripción | Ejemplo |
|----------|-----------|-------------|---------|
| `PORT` | No | Puerto del servidor | `3000` |
| `NODE_ENV` | No | Entorno (development/production) | `production` |
| `EVOLUTION_API_URL` | Sí | URL de Evolution API | `https://api.evolution-api.com` |
| `EVOLUTION_API_KEY` | Sí | API Key de Evolution API | `abc123...` |
| `EVOLUTION_INSTANCE` | Sí | Nombre de instancia de Evolution API | `MiBot` |
| `OPENAI_API_KEY` | Sí | API Key de OpenAI | `sk-abc123...` |
| `OPENAI_MODEL` | No | Modelo de OpenAI | `gpt-4o-mini` |
| `FORMBRICKS_URL` | No | URL de formulario de quejas | `https://.../form/quejas` |

### Extensiones y Plugins

El esqueleto está diseñado para ser extensible. Para agregar nuevas funcionalidades:

1. **Crear nuevo feature en `src/features/`:**
   ```bash
   mkdir src/features/my-new-feature
   touch src/features/my-new-feature/index.ts
   touch src/features/my-new-feature/types.ts
   ```

2. **Agregar feature flag:**
   ```typescript
   // src/core/config/features.ts
   export const FEATURE_FLAGS = {
     // ... otros flags
     MY_NEW_FEATURE: true
   } as const;
   ```

3. **Implementar lógica:**
   ```typescript
   // src/features/my-new-feature/index.ts
   export class MyNewFeature {
     // implementación
   }
   ```

4. **Integrar en el flujo principal:**
   ```typescript
   // src/controllers/webhookController.ts
   if (FEATURE_FLAGS.MY_NEW_FEATURE) {
     // usar el feature
   }
   ```

### Recursos Adicionales

- **Evolution API:** https://github.com/EvolutionAPI/evolution-api
- **OpenAI API:** https://platform.openai.com/docs/api-reference
- **OpenAI Models:** https://platform.openai.com/docs/models
- **TypeScript:** https://www.typescriptlang.org/docs/
- **Express.js:** https://expressjs.com/
- **Docker:** https://docs.docker.com/
- **Coolify:** https://coolify.io/docs

### Comunidad y Soporte

- **Issues:** GitHub Issues del proyecto
- **Discord:** Comunidad de usuarios (próximamente)
- **Email:** soporte@esqueleto-bot.com

---

## 📝 Checklist de Desarrollo

### Pre-desarrollo
- [ ] Clonar/esqueleto del proyecto
- [ ] Instalar dependencias
- [ ] Configurar variables de entorno
- [ ] Verificar instalación

### Configuración
- [ ] Activar features deseados
- [ ] Crear `client_data/` folder
- [ ] Crear `services.jsonl`
- [ ] Crear `locations.jsonl`
- [ ] Crear `config.json`

### Personalización
- [ ] Copiar template de cliente
- [ ] Editar `system_prompt.md`
- [ ] Personalizar `conversation_guides/`
- [ ] Personalizar `personality_rules/`

### Integraciones
- [ ] Configurar Evolution API
- [ ] Configurar OpenAI
- [ ] Configurar webhook
- [ ] Probar integraciones

### Testing
- [ ] Probar endpoint `/test`
- [ ] Probar memoria de conversación
- [ ] Probar análisis de sentimiento
- [ ] Probar upselling
- [ ] Probar RAG
- [ ] Probar flujos completos

### Despliegue
- [ ] Compilar TypeScript
- [ ] Crear Docker image
- [ ] Probar con docker-compose
- [ ] Desplegar en Coolify
- [ ] Configurar webhook en Evolution API
- [ ] Probar en producción

### Post-despliegue
- [ ] Configurar monitoreo
- [ ] Configurar backups
- [ ] Documentar configuración específica del cliente
- [ ] Entregar al cliente

---

## 🎉 Conclusión

¡Felicidades! Has completado el desarrollo de tu bot usando el esqueleto modular. Ahora tienes un bot de WhatsApp con IA generativa listo para producción.

### Próximos Pasos

1. **Monitorear el bot:** Observa las conversaciones y ajusta según feedback
2. **Optimizar prompts:** Mejora las respuestas basándote en datos reales
3. **Agregar features:** Considera agregar funcionalidades específicas del cliente
4. **Escalar:** Considera usar una base de datos real para la memoria si tienes muchos usuarios

### Feedback y Mejoras

Si encuentras bugs, tienes sugerencias o quieres contribuir, por favor:

- Abre un issue en GitHub
- Envía un pull request
- Contacta al equipo de desarrollo

---

**Versión:** 1.0.0
**Última actualización:** 8 de Febrero de 2026
**Autor:** Equipo de Desarrollo del Esqueleto Modular
**Licencia:** MIT
