# Vanessa Bot Backend

Backend para "Vanessa", la asistente virtual de WhatsApp de Vanity Salon.

## 📁 Estructura del Proyecto

```
bot_vanity/
├── src/
│   ├── app.ts                          # Punto de entrada de la aplicación
│   ├── controllers/
│   │   └── webhookController.ts         # Maneja webhooks de Evolution API
│   ├── services/
│   │   ├── ragService.ts               # Servicio de RAG (carga y búsqueda de datos)
│   │   ├── openaiService.ts            # Servicio de OpenAI (generación de respuestas)
│   │   └── evolutionService.ts         # Servicio de Evolution API (envío de mensajes)
│   └── types/
│       └── index.ts                    # Interfaces de TypeScript
├── vanity_data/
│   ├── services.jsonl                  # Catálogo de servicios
│   └── locations.jsonl                 # Ubicaciones y políticas
├── .env                                # Variables de entorno
├── package.json
└── tsconfig.json
```

## 🚀 Instalación y Ejecución

### 1. Instalar dependencias
```bash
npm install
```

### 2. Configurar variables de entorno
Editar `.env` con tus credenciales:
```env
EVOLUTION_API_URL=https://api.evolution-api.com
EVOLUTION_API_KEY=your_evolution_api_key_here
EVOLUTION_INSTANCE=VanityBot

OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

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

## 🔧 Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Información de la API |
| GET | `/health` | Health check |
| POST | `/webhook` | Webhook de Evolution API |

## 📋 Funcionalidades

### RAG Service
- Carga automáticamente `services.jsonl` y `locations.jsonl` al iniciar
- Filtra servicios obsoletos (Navidad, Diciembre, 2023-2025)
- Prioriza promociones de "HELLO FEBRUARY" en búsquedas de promociones
- Búsqueda por coincidencia de palabras clave ponderada

### Webhook Controller
- Recibe webhooks de Evolution API
- Ignora mensajes propios (`fromMe: true`)
- Detecta mensajes de imagen y responde con mensaje predefinido
- Construye prompt del sistema + contexto recuperado + mensaje del usuario
- Envía respuesta a través de Evolution API

### OpenAI Service
- Usa modelo `gpt-4o-mini`
- Carga prompt del sistema desde `system_prompt.md`
- Inyecta contexto de servicios y ubicaciones relevantes

## 🔐 Seguridad

- Variables de entorno en `.env` (agregado a `.gitignore`)
- Validación de tipos con TypeScript
- Manejo de errores en todos los servicios

## 📊 Datos

### Formato de services.jsonl
```json
{
  "id": "feb_01",
  "category": "💘 HELLO FEBRUARY 💘",
  "service": "CLASSIC ELEGANCE",
  "price": "$1,250.00 MXN",
  "duration": "2h 45m",
  "description": "Paquete consentidor..."
}
```

### Formato de locations.jsonl
```json
{
  "id": "loc_norte",
  "category": "Ubicación y Sucursales",
  "name": "Sucursal Plaza O (Norte)",
  "zone": "Norte de Saltillo",
  "address": "Blvd. Venustiano Carranza 4535...",
  "maps_link": "https://maps.app.goo.gl/...",
  "booking_link": "https://www.fresha.com/...",
  "description": "Ubicada al Norte..."
}
```

## 🎯 Personalidad del Bot

Vanessa sigue la personalidad "Clean Girl Aesthetic":
- Tono cálido, femenino, eficiente
- Usa "tú", no "usted"
- Emojis moderados (✨, 🤍, 💅, 🌸)
- Respuestas concisas pero amables

## 📞 Integraciones

- **Evolution API**: Gateway de WhatsApp
- **OpenAI gpt-4o-mini**: Generación de respuestas
- **Fresha**: Sistema de reservas (enlaces estáticos)
- **Google Maps**: Ubicaciones de sucursales
# bot_vanity
