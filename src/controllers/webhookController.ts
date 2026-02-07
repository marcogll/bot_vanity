import { Request, Response } from 'express';
import { EvolutionWebhookData } from '../types';
import { ragService } from '../services/ragService';
import { generateResponse, formatContext } from '../services/openaiService';
import { sendMessage, extractPhoneNumber } from '../services/evolutionService';
import { conversationMemory } from '../services/conversationMemory';
import { upsellingService } from '../services/upsellingService';
import { analyzeSentiment, isComplaint } from '../utils/sentimentAnalyzer';

export async function handleWebhook(req: Request, res: Response): Promise<void> {
  try {
    const webhookData: EvolutionWebhookData = req.body;

    if (webhookData.event !== 'messages.upsert') {
      res.status(200).json({ message: 'Event ignored' });
      return;
    }

    const { key, message, pushName } = webhookData.data;

    if (key.fromMe) {
      console.log('🔇 Ignoring own message');
      res.status(200).json({ message: 'Own message ignored' });
      return;
    }

    const userMessage = message.conversation || message.extendedTextMessage?.text || '';
    const remoteJid = key.remoteJid;

    if (!userMessage.trim()) {
      console.log('📸 Non-text message received (likely media)');
      const mediaResponse = '¡Hola! 🤍 Recibí tu foto. Para darte un precio exacto de un diseño personalizado, necesito que una compañera la revise. ¿Te gustaría que te contactemos para agendar una valoración?';
      await sendMessage(extractPhoneNumber(remoteJid), mediaResponse);
      
      // Guardar en memoria
      conversationMemory.addMessage(remoteJid, '[IMAGEN]', 'user', 'neutral');
      
      res.status(200).json({ message: 'Media message handled' });
      return;
    }

    console.log(`📨 Message from ${pushName} (${remoteJid}): ${userMessage}`);

    // 1. Analizar sentimiento del mensaje
    const sentimentAnalysis = analyzeSentiment(userMessage);
    console.log(`😊 Sentiment: ${sentimentAnalysis.sentiment} (confidence: ${sentimentAnalysis.confidence})`);

    // 2. Obtener historial de conversación y contexto de usuario
    const history = conversationMemory.getHistory(remoteJid);
    const userContext = conversationMemory.getContext(remoteJid);
    const userInfo = conversationMemory.getContactInfo(remoteJid);
    console.log(`🧠 History: ${history.length} messages, User: ${userInfo.isRecurring ? 'Recurring' : 'New'}`);

    // 3. Detectar si es una queja
    const isUserComplaint = isComplaint(userMessage);
    if (isUserComplaint) {
      console.log('😔 Complaint detected - skipping upselling');
    }

    // 4. Buscar servicios relevantes
    const searchResults = ragService.search(userMessage);

    // 5. Detectar oportunidad de upselling
    let upsellOpportunity: any = undefined;
    if (!isUserComplaint && upsellingService.shouldUpsell(remoteJid, userMessage, sentimentAnalysis.sentiment, userContext?.preferences)) {
      upsellOpportunity = upsellingService.detectOpportunity(
        userMessage,
        searchResults.services,
        userContext?.preferences
      );
      if (upsellOpportunity) {
        console.log(`💰 Upselling opportunity: ${upsellOpportunity.triggerService} → ${upsellOpportunity.suggestedService}`);
      }
    }

    // 6. Generar respuesta con historial, upselling y sentimiento
    const context = formatContext(searchResults.services, searchResults.locations);
    const aiResponse = await generateResponse(
      userMessage,
      context,
      history,
      upsellOpportunity,
      sentimentAnalysis.sentiment,
      userInfo
    );

    // 7. Enviar respuesta
    await sendMessage(extractPhoneNumber(remoteJid), aiResponse);

    // 8. Guardar en memoria
    conversationMemory.addMessage(remoteJid, userMessage, 'user', sentimentAnalysis.sentiment);
    conversationMemory.addMessage(remoteJid, aiResponse, 'assistant');

    // 9. Actualizar preferencias si el usuario menciona sucursal
    const branchMentioned = detectBranchMention(userMessage, searchResults.locations);
    if (branchMentioned) {
      conversationMemory.updatePreferences(remoteJid, {
        preferredBranch: branchMentioned
      });
      console.log(`📍 Preferred branch updated: ${branchMentioned}`);
    }

    // 10. Detectar si se agendó algo (marcar resultado)
    if (detectBooking(userMessage) || userMessage.toLowerCase().includes('agendar')) {
      conversationMemory.markResult(remoteJid, {
        booked: true,
        branch: branchMentioned || userContext?.preferences?.preferredBranch,
        timestamp: new Date()
      });
      console.log('✅ Booking result marked');
    }

    console.log(`✅ Response sent to ${pushName} (sentiment: ${sentimentAnalysis.sentiment})`);
    res.status(200).json({ message: 'Webhook processed successfully' });
  } catch (error) {
    console.error('❌ Error processing webhook:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
}

/**
 * Detecta si el usuario menciona una sucursal específica
 */
function detectBranchMention(message: string, locations: any[]): string | undefined {
  const messageLower = message.toLowerCase();
  
  // Palabras clave para norte
  const norteKeywords = ['plaza o', 'virreyes', 'v. carranza', 'venustiano carranza', 'norte', 'zonanorte'];
  if (norteKeywords.some(keyword => messageLower.includes(keyword))) {
    const location = locations.find(l => l.zone?.toLowerCase().includes('norte') || l.name.toLowerCase().includes('plaza o'));
    if (location) return location.name;
  }
  
  // Palabras clave para sur
  const surKeywords = ['cima', 'valle dorado', 'periférico', 'sur', 'zonasur'];
  if (surKeywords.some(keyword => messageLower.includes(keyword))) {
    const location = locations.find(l => l.zone?.toLowerCase().includes('sur') || l.name.toLowerCase().includes('cima'));
    if (location) return location.name;
  }

  return undefined;
}

/**
 * Detecta si el usuario quiere agendar
 */
function detectBooking(message: string): boolean {
  const bookingKeywords = ['agendar', 'cita', 'reservar', 'programar', 'quiero', 'me gustaría', 'sí,'];
  return bookingKeywords.some(keyword => message.toLowerCase().includes(keyword));
}
