import axios from 'axios';
import { EvolutionSendMessage } from '../types';

const EVOLUTION_API_URL = (process.env.EVOLUTION_API_URL || 'https://api.evolution-api.com').replace(/\/$/, '');
const EVOLUTION_API_KEY = process.env.EVOLUTION_API_KEY;
const EVOLUTION_INSTANCE = process.env.EVOLUTION_INSTANCE || 'VanityBot';

const api = axios.create({
  baseURL: `${EVOLUTION_API_URL}/message/sendText/${EVOLUTION_INSTANCE}`,
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

    await api.post('', payload);
    console.log(`✅ Message sent to ${phoneNumber}`);
  } catch (error) {
    console.error('❌ Error sending message:', error);
    throw new Error('Failed to send message');
  }
}

export function extractPhoneNumber(remoteJid: string): string {
  return remoteJid.split('@')[0];
}
