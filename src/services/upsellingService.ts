import { Service, UpsellOpportunity } from '../types';

export class UpsellingService {
  /**
   * Detectar oportunidad de upselling basada en mensaje y servicios encontrados
   */
  detectOpportunity(
    userMessage: string,
    foundServices: Service[],
    userPreferences?: { mentionedServices?: string[]; preferredBranch?: string }
  ): UpsellOpportunity | undefined {
    const messageLower = userMessage.toLowerCase();
    const mentionedServices = userPreferences?.mentionedServices || [];

    // ACRÍLICO → POLYGEL
    if (messageLower.includes('acrílico') || messageLower.includes('acrilico')) {
      // Si el usuario ya rechazó upselling de polygel, no sugerir de nuevo
      if (mentionedServices.includes('polygel') && this.hasRejectedUpselling(userMessage, 'polygel')) {
        return undefined;
      }

      return {
        triggerService: 'acrílico',
        suggestedService: 'polygel',
        reason: 'más natural, sin olor, más flexible',
        priority: 'high' as const
      };
    }

    // CUALQUIER SERVICIO DE UÑAS → BASE RUBBER/VITAMINA
    const isNailsService = foundServices.some(s =>
      s.category === 'Nails' ||
      s.service.toLowerCase().includes('uñas') ||
      s.service.toLowerCase().includes('gelish') ||
      s.service.toLowerCase().includes('manicure') ||
      s.service.toLowerCase().includes('pedicure')
    );

    if (isNailsService && !messageLower.includes('vita') && !messageLower.includes('rubber')) {
      // Si el usuario ya rechazó upselling de base rubber, no sugerir de nuevo
      if (mentionedServices.includes('base rubber') && this.hasRejectedUpselling(userMessage, 'base rubber')) {
        return undefined;
      }

      return {
        triggerService: 'servicio de uñas',
        suggestedService: 'base rubber o vitamina',
        reason: 'fortalecer uñas y aumentar duración',
        priority: 'medium' as const
      };
    }

    // CEJAS → VANITY ESSENCE
    if (messageLower.includes('ceja') || messageLower.includes('cejas')) {
      // Si el usuario ya rechazó upselling de vanity essence, no sugerir de nuevo
      if (mentionedServices.includes('vanity essence') && this.hasRejectedUpselling(userMessage, 'vanity essence')) {
        return undefined;
      }

      return {
        triggerService: 'cejas',
        suggestedService: 'vanity essence (diseño básico)',
        reason: 'complementar el look con diseño desde $130',
        priority: 'medium' as const
      };
    }

    // CABELLO → TRATAMIENTOS
    const isHairService = foundServices.some(s =>
      s.category === 'Hair Services' ||
      s.service.toLowerCase().includes('cabello') ||
      s.service.toLowerCase().includes('pelo') ||
      s.service.toLowerCase().includes('corte') ||
      s.service.toLowerCase().includes('secado')
    );

    if (isHairService && !messageLower.includes('botox') && !messageLower.includes('tratamiento') && !messageLower.includes('gloss')) {
      // Si el usuario ya rechazó upselling de tratamiento, no sugerir de nuevo
      if ((mentionedServices.includes('hair botox') || mentionedServices.includes('gloss elixir')) &&
          this.hasRejectedUpselling(userMessage, 'tratamiento')) {
        return undefined;
      }

      return {
        triggerService: 'servicio de cabello',
        suggestedService: 'hair botox o gloss elixir',
        reason: 'nutrir y reparar a profundidad',
        priority: 'medium' as const
      };
    }

    return undefined;
  }

  /**
   * Generar hint para el prompt de OpenAI
   */
  generateUpsellHint(opportunity: UpsellOpportunity): string {
    return `
# UPSELLING OPPORTUNITY
Trigger: ${opportunity.triggerService}
Suggested: ${opportunity.suggestedService}
Reason: ${opportunity.reason}
Priority: ${opportunity.priority}

Si es natural y el usuario parece abierto, menciona: ${opportunity.suggestedService}.
Razón: ${opportunity.reason}
NO seas pushy. Si el usuario no parece interesado, no insistas.
`;
  }

  /**
   * Verificar si debe hacer upselling (evitar spam)
   */
  shouldUpsell(
    remoteJid: string,
    userMessage: string,
    sentiment: 'positive' | 'neutral' | 'negative',
    userPreferences?: { mentionedServices?: string[]; lastUpsellAttempt?: Date }
  ): boolean {
    const messageLower = userMessage.toLowerCase();

    // NO hacer upselling si:
    // 1. El sentimiento es negativo
    if (sentiment === 'negative') {
      return false;
    }

    // 2. El usuario dice "solo" + servicio
    if (messageLower.includes('solo ')) {
      return false;
    }

    // 3. El usuario parece apurado
    if (this.isUrgentMessage(userMessage)) {
      return false;
    }

    // 4. El usuario responde con monosílabos
    if (this.isMonosyllableResponse(userMessage)) {
      return false;
    }

    // 5. El usuario ya rechazó un upselling en esta conversación
    if (this.hasRejectedUpselling(userMessage, 'any')) {
      return false;
    }

    // 6. Ya se intentó upselling recientemente (menos de 24h)
    if (userPreferences?.lastUpsellAttempt) {
      const hoursSinceLastUpsell = (new Date().getTime() - userPreferences.lastUpsellAttempt.getTime()) / (1000 * 60 * 60);
      if (hoursSinceLastUpsell < 24) {
        return false;
      }
    }

    return true;
  }

  /**
   * Detectar si el usuario rechazó el upselling
   */
  private hasRejectedUpselling(userMessage: string, service: string): boolean {
    const messageLower = userMessage.toLowerCase();
    const rejectionKeywords = ['no gracias', 'no thanks', 'no', 'no quiero', 'no me interesa', 'no gracias'];

    // Si service es 'any', verificar cualquier rechazo
    if (service === 'any') {
      return rejectionKeywords.some(keyword => messageLower.includes(keyword));
    }

    // Si es un servicio específico, verificar rechazo específico o general
    return rejectionKeywords.some(keyword => messageLower.includes(keyword));
  }

  /**
   * Detectar si el mensaje parece urgente
   */
  private isUrgentMessage(message: string): boolean {
    const messageLower = message.toLowerCase();
    const urgentKeywords = ['rápido', 'urgente', 'pronto', 'ahora', 'ya', 'esperando', 'hace rato'];

    return urgentKeywords.some(keyword => messageLower.includes(keyword));
  }

  /**
   * Detectar si es una respuesta de monosílabo
   */
  private isMonosyllableResponse(message: string): boolean {
    const trimmed = message.trim();
    const monosyllables = ['sí', 'si', 'no', 'ok', 'okay', 'bien', 'claro', 'listo'];

    return monosyllables.some(ms => trimmed.toLowerCase() === ms);
  }
}

// Singleton instance
export const upsellingService = new UpsellingService();
