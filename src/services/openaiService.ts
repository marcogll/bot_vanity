import * as fs from 'fs';
import * as path from 'path';
import * as dotenv from 'dotenv';

// Cargar variables de entorno antes de importar OpenAI
dotenv.config();

import OpenAI from 'openai';
import { ConversationMessage, UpsellOpportunity } from '../types';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

const SYSTEM_PROMPT_PATH = path.join(__dirname, '../../system_prompt.md');

let cachedSystemPrompt: string | null = null;

function getSystemPrompt(): string {
  if (!cachedSystemPrompt) {
    try {
      cachedSystemPrompt = fs.readFileSync(SYSTEM_PROMPT_PATH, 'utf-8');
    } catch (error) {
      console.error('❌ Error loading system prompt:', error);
      return 'Eres Vanessa, la asistente virtual de Vanity Salon.';
    }
  }
  return cachedSystemPrompt;
}

/**
 * Genera respuesta con historial de conversación, upselling y sentimiento
 */
export async function generateResponse(
  userMessage: string,
  context: string,
  conversationHistory: ConversationMessage[] = [],
  upsellOpportunity?: UpsellOpportunity,
  sentiment?: 'positive' | 'neutral' | 'negative',
  userInfo?: { pushName?: string; isRecurring?: boolean; preferredBranch?: string; isNewUser?: boolean }
): Promise<string> {
  const systemPrompt = getSystemPrompt();
  
  // Construir prompt completo
  const fullPrompt = buildFullPrompt(
    systemPrompt, 
    context, 
    upsellOpportunity, 
    sentiment, 
    userInfo
  );

  // Construir array de mensajes para OpenAI
  const messages: OpenAI.Chat.Completions.ChatCompletionMessageParam[] = [
    {
      role: 'system',
      content: fullPrompt
    },
    // Incluir historial de conversación (últimos 10 mensajes)
    ...conversationHistory.map(msg => ({
      role: msg.role as 'user' | 'assistant',
      content: msg.content
    })),
    {
      role: 'user',
      content: userMessage
    }
  ];

  // Ajustar temperatura según sentimiento
  const temperature = getTemperatureBySentiment(sentiment);

  try {
    console.log(`🤖 Calling OpenAI with ${conversationHistory.length} history messages, sentiment: ${sentiment}, temp: ${temperature}`);
    
    const completion = await openai.chat.completions.create({
      model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
      messages,
      temperature,
      max_tokens: 500
    });

    const response = completion.choices[0].message.content || 'Lo siento, no pude generar una respuesta.';
    console.log(`✅ OpenAI response generated (${response.length} chars)`);
    
    return response;
  } catch (error) {
    console.error('❌ Error calling OpenAI:', error);
    throw new Error('Failed to generate response');
  }
}

/**
 * Construye el prompt completo del sistema
 */
function buildFullPrompt(
  systemPrompt: string,
  context: string,
  upsellOpportunity?: UpsellOpportunity,
  sentiment?: 'positive' | 'neutral' | 'negative',
  userInfo?: { pushName?: string; isRecurring?: boolean; preferredBranch?: string; isNewUser?: boolean }
): string {
  let prompt = systemPrompt;

  // Añadir información del usuario si está disponible
  if (userInfo) {
    prompt += `\n\n# INFORMACIÓN DEL USUARIO`;
    if (userInfo.pushName) prompt += `\nNombre: ${userInfo.pushName}`;
    if (userInfo.isNewUser) {
      prompt += `\nTIPO: NUEVO USUARIO (PRIMER MENSAJE)`;
      prompt += `\nINSTRUCCIÓN ESPECIAL: Preséntate y pregunta el nombre del usuario si aún no lo has recibido.`;
    } else if (userInfo.isRecurring) {
      prompt += `\nTIPO: Recurrente (ya ha interactuado antes)`;
      prompt += `\nINSTRUCCIÓN: NO vuelvas a presentarte. Ya te conocen.`;
    } else {
      prompt += `\nTIPO: Usuario reciente`;
    }
    if (userInfo.preferredBranch) prompt += `\nSucursal preferida: ${userInfo.preferredBranch}`;
  }

  // Añadir sentimiento al prompt
  if (sentiment) {
    prompt += `\n\n# SENTIMIENTO DEL USUARIO: ${sentiment.toUpperCase()}`;
    if (sentiment === 'negative') {
      prompt += '\nADJUST YOUR TONE: Be more empathetic, use fewer emojis (0-1), be direct, do NOT do upselling.';
    } else if (sentiment === 'positive') {
      prompt += '\nADJUST YOUR TONE: Be warm and enthusiastic, suggest upselling if natural.';
    } else {
      prompt += '\nADJUST YOUR TONE: Be direct and concise.';
    }
  }

  // Añadir hint de upselling
  if (upsellOpportunity) {
    prompt += `\n\n# UPSELLING OPPORTUNITY`;
    prompt += `\nTrigger: ${upsellOpportunity.triggerService}`;
    prompt += `\nSuggested: ${upsellOpportunity.suggestedService}`;
    prompt += `\nReason: ${upsellOpportunity.reason}`;
    prompt += `\nPriority: ${upsellOpportunity.priority}`;
    prompt += '\nINSTRUCTIONS: If natural, mention the suggested service. Be subtle, not pushy. If user says no, accept and change topic.';
  }

  // Añadir contexto de servicios y ubicaciones
  prompt += `\n\n# CONTEXTO DE SERVICIOS Y UBICACIONES\n${context}`;

  return prompt;
}

/**
 * Obtiene temperatura según el sentimiento
 */
function getTemperatureBySentiment(sentiment?: 'positive' | 'neutral' | 'negative'): number {
  if (sentiment === 'negative') {
    // Respuestas más predecibles en quejas
    return 0.3;
  } else if (sentiment === 'positive') {
    // Más creatividad para respuestas positivas
    return 0.8;
  } else {
    // Balanceado para respuestas neutrales
    return 0.7;
  }
}

/**
 * Formatea el contexto de servicios y ubicaciones
 */
export function formatContext(services: any[], locations: any[]): string {
  let context = '';

  if (services.length > 0) {
    context += 'SERVICIOS RELEVANTES:\n';
    services.forEach((s, i) => {
      context += `${i + 1}. ${s.service} - ${s.price} (${s.duration})\n   ${s.description}\n\n`;
    });
  }

  if (locations.length > 0) {
    context += 'UBICACIONES:\n';
    locations.forEach((l, i) => {
      context += `${i + 1}. ${l.name}\n   ${l.description}\n`;
      if (l.maps_link) context += `   Maps: ${l.maps_link}\n`;
      if (l.booking_link) context += `   Booking: ${l.booking_link}\n`;
      context += '\n';
    });
  }

  return context;
}
