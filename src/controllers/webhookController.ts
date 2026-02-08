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

    // Log completo del payload del webhook para debugging
    console.log('📨 FULL WEBHOOK PAYLOAD:', JSON.stringify(webhookData, null, 2));

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
    const remoteJidAlt = key.remoteJidAlt;

    // Detectar si es mensaje de imagen
    const isImageMessage = !!message.imageMessage;

    if (isImageMessage) {
      console.log('📸 Image message detected - saving for later processing');

      // Guardar imagen temporalmente en memoria
      const imageData = {
        type: 'image',
        timestamp: new Date(),
        url: message.imageMessage?.url,
        caption: message.imageMessage?.caption
      };

      conversationMemory.addMessage(remoteJid, '[IMAGEN GUARDADA]', 'user');
      conversationMemory.addMessage(remoteJid, JSON.stringify(imageData), 'assistant');

      // Respuesta temporal (se mejorará cuando el usuario siga en la conversación)
      const tempResponse = '¡Hola! 🤍 Recibí tu foto. La voy a revisar para poder darte información precisa. En unos minutos te contacto con los detalles del servicio que te interesa. ✨';

      await sendMessage(extractPhoneNumber(remoteJid, remoteJidAlt), tempResponse);

      res.status(200).json({ message: 'Image message handled - saved for processing' });
      return;
    }

    console.log(`📨 Message from ${pushName} (${remoteJid}): ${userMessage}`);
    if (remoteJidAlt) {
      console.log(`📱 Alternative JID found: ${remoteJidAlt}`);
    }

    console.log(`📨 Message from ${pushName} (${remoteJid}): ${userMessage}`);
    if (remoteJidAlt) {
      console.log(`📱 Alternative JID found: ${remoteJidAlt}`);
    }

    // MANEJO DEL COMANDO DIPIRIDÚ (para testing)
    const lowerMessage = userMessage.toLowerCase().trim();
    if (lowerMessage === 'dipiridú' || lowerMessage === 'dipiridu') {
      console.log('🧹 Dipiridú command detected');
      const phoneNumber = extractPhoneNumber(remoteJid, remoteJidAlt);
      await sendMessage(phoneNumber, '⚠️ ¿Estás seguro de que quieres borrar TODA la base de datos de memoria? Esto eliminará todas las conversaciones guardadas. Responde "sí" para confirmar o "no" para cancelar.');
      conversationMemory.setConfirmationPending(remoteJid);
      res.status(200).json({ message: 'Dipiridú confirmation requested' });
      return;
    }

    if (conversationMemory.isConfirmationPending(remoteJid)) {
      if (lowerMessage === 'sí' || lowerMessage === 'si' || lowerMessage === 'yes' || lowerMessage === 'y') {
        console.log('✅ Memory clear confirmed');
        const result = conversationMemory.clearAll();
        const phoneNumber = extractPhoneNumber(remoteJid, remoteJidAlt);
        await sendMessage(phoneNumber, `🧹 ¡Hecho! He borrado ${result.cleared} conversaciones de la base de datos de memoria.`);
        conversationMemory.clearConfirmationPending(remoteJid);
        res.status(200).json({ message: 'Memory cleared', cleared: result.cleared });
        return;
      } else if (lowerMessage === 'no' || lowerMessage === 'cancelar' || lowerMessage === 'cancel') {
        console.log('❌ Memory clear cancelled');
        const phoneNumber = extractPhoneNumber(remoteJid, remoteJidAlt);
        await sendMessage(phoneNumber, '✅ Operación cancelada. La base de datos de memoria se mantiene intacta.');
        conversationMemory.clearConfirmationPending(remoteJid);
        res.status(200).json({ message: 'Memory clear cancelled' });
        return;
      } else {
        const phoneNumber = extractPhoneNumber(remoteJid, remoteJidAlt);
        await sendMessage(phoneNumber, '❓ No entendí tu respuesta. Por favor responde "sí" para borrar la memoria o "no" para cancelar.');
        res.status(200).json({ message: 'Waiting for confirmation' });
        return;
      }
    }

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
      { ...userInfo, isNewUser: history.length === 0 }
    );

    // 7. Enviar respuesta
    const phoneNumber = extractPhoneNumber(remoteJid, remoteJidAlt);
    console.log(`📱 Sending response to phone number: ${phoneNumber} (from JID: ${remoteJid}, Alt JID: ${remoteJidAlt || 'N/A'})`);
    await sendMessage(phoneNumber, aiResponse);

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
