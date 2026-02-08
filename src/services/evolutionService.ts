import axios from 'axios';
import { EvolutionSendMessage } from '../types';

const EVOLUTION_API_URL = (process.env.EVOLUTION_API_URL || 'https://api.evolution-api.com').replace(/\/$/, '');
const EVOLUTION_API_KEY = process.env.EVOLUTION_API_KEY;
const EVOLUTION_INSTANCE = process.env.EVOLUTION_INSTANCE || 'VanityBot';
const EVOLUTION_API_ENDPOINT = process.env.EVOLUTION_API_ENDPOINT || '/message/sendText';

const api = axios.create({
  baseURL: `${EVOLUTION_API_URL}${EVOLUTION_API_ENDPOINT}/${EVOLUTION_INSTANCE}`,
  headers: {
    'Content-Type': 'application/json',
    'apikey': EVOLUTION_API_KEY
  }
});

export async function sendMessage(
  phoneNumber: string,
  text: string,
  delay: number = 1000
): Promise<void> {
  try {
    const payload: EvolutionSendMessage = {
      number: phoneNumber,
      text: text,
      delay: delay
    };

    console.log(`📤 Sending message to Evolution API:`);
    console.log(`   URL: ${EVOLUTION_API_URL}/message/sendText/${EVOLUTION_INSTANCE}`);
    console.log(`   Phone: ${phoneNumber}`);
    console.log(`   Text: ${text}`);
    console.log(`   Delay: ${delay}ms`);

    const response = await api.post('', payload);

    console.log(`✅ Evolution API response:`, response.data);
    console.log(`✅ Message sent to ${phoneNumber}`);
  } catch (error: any) {
    console.error('❌ Error sending message to Evolution API:');
    console.error('   Status:', error.response?.status);
    console.error('   StatusText:', error.response?.statusText);
    console.error('   Data:', error.response?.data);
    console.error('   Full error:', error.message);
    throw new Error('Failed to send message');
  }
}

/**
 * Extrae el número de teléfono del JID
 * Si remoteJidAlt está disponible, lo usa ya que contiene el formato correcto
 */
export function extractPhoneNumber(remoteJid: string, remoteJidAlt?: string): string {
  // Prioridad 1: remoteJidAlt si está disponible (ya tiene formato correcto)
  if (remoteJidAlt && remoteJidAlt.includes('@s.whatsapp.net')) {
    return remoteJidAlt.split('@')[0];
  }
  
  // Prioridad 2: remoteJid normal
  return remoteJid.split('@')[0];
}
