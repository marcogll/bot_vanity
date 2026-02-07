import { SentimentAnalysis } from '../types';

/**
 * Analiza el sentimiento de un mensaje de texto
 */
export function analyzeSentiment(message: string): SentimentAnalysis {
  const messageLower = message.toLowerCase();
  const keywords = {
    positive: [
      'gracias', 'perfecto', 'excelente', 'genial', 'super', 'quiero', 'sí',
      'me gusta', 'me encanta', 'está bien', 'me sirve', '¡', '❤️', '😊', '✨',
      'súper', 'perfecta', 'perfecto', 'excelente', 'genial', 'me encanta',
      'me gusta', 'bueno', 'buena', 'buenos', 'buenas'
    ],
    negative: [
      'terrible', 'pésimo', 'mal', 'malo', 'mala', 'queja', 'no me gustó',
      'lento', 'esperé', 'esperada', 'esperado', 'demoraron', 'demorada', 'demorado',
      'no volveré', 'nunca más', 'última vez', 'disgusto', 'enojado', 'frustrada',
      'frustrado', 'pésimo', 'terrible', '😠', '😡', '😔', '💔'
    ]
  };

  const detectedKeywords: string[] = [];

  // Buscar palabras clave positivas
  for (const keyword of keywords.positive) {
    if (messageLower.includes(keyword)) {
      detectedKeywords.push(keyword);
    }
  }

  // Buscar palabras clave negativas
  for (const keyword of keywords.negative) {
    if (messageLower.includes(keyword)) {
      detectedKeywords.push(keyword);
    }
  }

  const positiveCount = detectedKeywords.filter(kw => keywords.positive.includes(kw)).length;
  const negativeCount = detectedKeywords.filter(kw => keywords.negative.includes(kw)).length;
  const totalKeywords = detectedKeywords.length;

  // Determinar sentimiento
  let sentiment: 'positive' | 'neutral' | 'negative';
  let confidence: number;

  if (negativeCount > 0) {
    sentiment = 'negative';
    confidence = Math.min(negativeCount / totalKeywords, 1.0);
  } else if (positiveCount > 0) {
    sentiment = 'positive';
    confidence = Math.min(positiveCount / totalKeywords, 1.0);
  } else {
    sentiment = 'neutral';
    confidence = 0.0;
  }

  // Ajustar confianza basado en la longitud del mensaje
  if (sentiment === 'neutral' && message.length > 50) {
    // Si el mensaje es largo pero no tiene palabras clave, aumentar confianza de neutral
    confidence = 0.5;
  }

  return {
    sentiment,
    confidence,
    keywords: detectedKeywords
  };
}

/**
 * Verifica si se debe ajustar el tono según el sentimiento
 */
export function shouldAdjustTone(sentiment: string): boolean {
  return sentiment === 'negative';
}

/**
 * Retorna los emojis recomendados según el sentimiento
 */
export function getRecommendedEmojis(sentiment: string): string[] {
  if (sentiment === 'positive') {
    return ['✨', '🤍', '💅', '🌸'];
  } else if (sentiment === 'neutral') {
    return ['✨', '🤍'];
  } else if (sentiment === 'negative') {
    return ['😔', '💔'];
  }
  return ['✨', '🤍'];
}

/**
 * Verifica si el mensaje parece ser una queja
 */
export function isComplaint(message: string): boolean {
  const messageLower = message.toLowerCase();
  const complaintKeywords = [
    'pésimo', 'terrible', 'mal servicio', 'queja', 'no me gustó',
    'lento', 'esperé', 'demoraron', 'no volveré', 'nunca más',
    'disgusto', 'enojado', 'frustrada'
  ];

  return complaintKeywords.some(keyword => messageLower.includes(keyword));
}

/**
 * Verifica si el usuario parece estar apurado
 */
export function isUrgent(message: string): boolean {
  const messageLower = message.toLowerCase();
  const urgentKeywords = [
    'rápido', 'urgente', 'pronto', 'ahora', 'ya', 'esperando',
    'hace rato', 'tengo prisa', 'necesito ya'
  ];

  return urgentKeywords.some(keyword => messageLower.includes(keyword));
}

/**
 * Verifica si el usuario parece ser específico en lo que quiere
 */
export function isSpecific(message: string): boolean {
  const messageLower = message.toLowerCase();
  const specificKeywords = [
    'precio de', 'cuánto cuesta', 'dónde están', 'ubicación',
    'agendar', 'cita', 'reservar', 'horario'
  ];

  return specificKeywords.some(keyword => messageLower.includes(keyword));
}

/**
 * Verifica si el usuario parece estar indeciso
 */
export function isIndecisive(message: string): boolean {
  const messageLower = message.toLowerCase();
  const indecisiveKeywords = [
    'no sé', 'qué me recomiendas', 'qué hago', 'estoy indecisa',
    'no sé qué hacer', 'ayúdame a decidir', 'qué crees'
  ];

  return indecisiveKeywords.some(keyword => messageLower.includes(keyword));
}
