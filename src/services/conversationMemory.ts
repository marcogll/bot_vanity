import { UserContext, ConversationMessage, ConversationResult, MemoryStats } from '../types';

export class ConversationMemory {
  private users: Map<string, UserContext>;
  private readonly MAX_MESSAGES = 10;
  private readonly MEMORY_TTL_HOURS = 48; // 48 horas de retención

  constructor() {
    this.users = new Map();
    // Limpieza inicial
    this.cleanupOldConversations();
    
    // Limpieza automática cada hora
    setInterval(() => {
      this.cleanupOldConversations();
    }, 60 * 60 * 1000); // 1 hora
  }

  /**
   * Añadir mensaje al historial de un usuario
   */
  addMessage(
    remoteJid: string,
    message: string,
    role: 'user' | 'assistant',
    sentiment?: 'positive' | 'neutral' | 'negative'
  ): void {
    const context = this.getOrCreateContext(remoteJid);

    // Añadir nuevo mensaje
    const newMessage: ConversationMessage = {
      role,
      content: message,
      timestamp: new Date(),
      sentiment
    };

    context.messages.push(newMessage);

    // Mantener solo los últimos MAX_MESSAGES mensajes
    if (context.messages.length > this.MAX_MESSAGES) {
      context.messages = context.messages.slice(-this.MAX_MESSAGES);
    }

    // Actualizar último contacto
    context.lastActive = new Date();

    // Actualizar historial de sentimiento
    if (sentiment) {
      context.sentimentHistory.push(sentiment);
      // Mantener solo los últimos 20 sentimientos
      if (context.sentimentHistory.length > 20) {
        context.sentimentHistory = context.sentimentHistory.slice(-20);
      }
    }

    this.users.set(remoteJid, context);

    console.log(`✅ Message added for ${remoteJid}. Total messages: ${context.messages.length}`);
  }

  /**
   * Obtener historial de mensajes de un usuario
   */
  getHistory(remoteJid: string): ConversationMessage[] {
    const context = this.users.get(remoteJid);
    return context ? context.messages : [];
  }

  /**
   * Obtener contexto completo de un usuario
   */
  getContext(remoteJid: string): UserContext | undefined {
    return this.users.get(remoteJid);
  }

  /**
   * Obtener o crear contexto de usuario
   */
  private getOrCreateContext(remoteJid: string): UserContext {
    let context = this.users.get(remoteJid);
    
    if (!context) {
      context = {
        remoteJid,
        messages: [],
        lastActive: new Date(),
        firstContact: new Date(),
        sentimentHistory: []
      };
      this.users.set(remoteJid, context);
      console.log(`✅ New context created for ${remoteJid}`);
    }

    return context;
  }

  /**
   * Actualizar preferencias de un usuario
   */
  updatePreferences(
    remoteJid: string,
    preferences: Partial<UserContext['preferences']>
  ): void {
    const context = this.users.get(remoteJid);
    if (!context) {
      console.warn(`⚠️ Context not found for ${remoteJid}`);
      return;
    }

    const currentPreferences = context.preferences || {
      mentionedServices: [],
      lastServiceInquired: undefined,
      preferredBranch: undefined
    };

    context.preferences = {
      preferredBranch: preferences!.preferredBranch ?? currentPreferences.preferredBranch,
      mentionedServices: currentPreferences.mentionedServices,
      lastServiceInquired: preferences!.lastServiceInquired ?? currentPreferences.lastServiceInquired
    };

    // Actualizar historial de servicios mencionados
    if (preferences!.lastServiceInquired) {
      const services = context.preferences.mentionedServices;
      if (!services.includes(preferences!.lastServiceInquired)) {
        services.push(preferences!.lastServiceInquired);
      }
    }

    this.users.set(remoteJid, context);
    console.log(`✅ Preferences updated for ${remoteJid}:`, preferences);
  }

  /**
   * Marcar resultado de conversación
   */
  markResult(
    remoteJid: string,
    result: Partial<ConversationResult>
  ): void {
    const context = this.users.get(remoteJid);
    if (!context) {
      console.warn(`⚠️ Context not found for ${remoteJid}`);
      return;
    }

    context.result = {
      booked: result.booked ?? false,
      serviceBooked: result.serviceBooked,
      branch: result.branch,
      timestamp: result.timestamp || new Date()
    };

    this.users.set(remoteJid, context);
    console.log(`✅ Result marked for ${remoteJid}:`, result);
  }

  /**
   * Limpiar conversaciones antiguas (>48 horas)
   */
  cleanupOldConversations(): { removed: number; total: number } {
    const now = new Date();
    let removed = 0;
    const total = this.users.size;

    for (const [remoteJid, context] of this.users.entries()) {
      const hoursInactive = (now.getTime() - context.lastActive.getTime()) / (1000 * 60 * 60);

      if (hoursInactive > this.MEMORY_TTL_HOURS) {
        console.log(`🧹 Cleaning up old conversation for ${remoteJid} (${hoursInactive.toFixed(2)}h inactive)`);
        this.users.delete(remoteJid);
        removed++;
      }
    }

    console.log(`🧹 Cleanup complete. Removed ${removed} conversations out of ${total}. Active: ${this.users.size}`);

    return {
      removed,
      total: this.users.size
    };
  }

  /**
   * Obtener estadísticas de memoria
   */
  getStats(): MemoryStats {
    const totalUsers = this.users.size;
    const activeConversations = Array.from(this.users.values()).filter(
      ctx => {
        const hoursInactive = (new Date().getTime() - ctx.lastActive.getTime()) / (1000 * 60 * 60);
        return hoursInactive <= 1; // Conversaciones activas en la última hora
      }
    ).length;

    const totalMessages = Array.from(this.users.values())
      .reduce((sum, ctx) => sum + ctx.messages.length, 0);
    
    const averageMessagesPerUser = totalUsers > 0 ? totalMessages / totalUsers : 0;

    return {
      totalUsers,
      activeConversations,
      averageMessagesPerUser: Math.round(averageMessagesPerUser * 100) / 100,
      conversationsCleaned: 0 // Se actualiza después de cada cleanup
    };
  }

  /**
   * Obtener promedio de sentimiento de un usuario
   */
  getAverageSentiment(remoteJid: string): 'positive' | 'neutral' | 'negative' | undefined {
    const context = this.users.get(remoteJid);
    if (!context || context.sentimentHistory.length === 0) {
      return undefined;
    }

    const sentiments = context.sentimentHistory;
    const positiveCount = sentiments.filter(s => s === 'positive').length;
    const negativeCount = sentiments.filter(s => s === 'negative').length;
    const totalCount = sentiments.length;

    if (negativeCount / totalCount > 0.5) {
      return 'negative';
    } else if (positiveCount / totalCount > 0.5) {
      return 'positive';
    } else {
      return 'neutral';
    }
  }

  /**
   * Detectar si un usuario es recurrente (tuvo conversación previa)
   */
  isRecurringUser(remoteJid: string): boolean {
    const context = this.users.get(remoteJid);
    if (!context) {
      return false;
    }

    const hoursSinceFirstContact = (new Date().getTime() - context.firstContact.getTime()) / (1000 * 60 * 60);
    return hoursSinceFirstContact > 24; // Recurrente si contactó hace más de 24h
  }

  /**
   * Obtener información de contacto para personalización
   */
  getContactInfo(remoteJid: string): {
    pushName?: string;
    isRecurring: boolean;
    preferredBranch?: string;
    lastServicesMentioned: string[];
  } {
    const context = this.users.get(remoteJid);

    return {
      pushName: context?.pushName,
      isRecurring: this.isRecurringUser(remoteJid),
      preferredBranch: context?.preferences?.preferredBranch,
      lastServicesMentioned: context?.preferences?.mentionedServices || []
    };
  }
}

// Singleton instance
export const conversationMemory = new ConversationMemory();
