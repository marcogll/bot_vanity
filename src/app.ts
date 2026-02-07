import express, { Request, Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { handleWebhook } from './controllers/webhookController';
import { conversationMemory } from './services/conversationMemory';
import { generateResponse, formatContext } from './services/openaiService';
import { analyzeSentiment } from './utils/sentimentAnalyzer';
import { upsellingService } from './services/upsellingService';
import { ragService } from './services/ragService';

dotenv.config();

// Debug: Verificar carga de variables de entorno
console.log('🔍 Environment variables loaded:');
console.log('OPENAI_API_KEY:', process.env.OPENAI_API_KEY ? '✅ Set' : '❌ Missing');
console.log('EVOLUTION_API_KEY:', process.env.EVOLUTION_API_KEY ? '✅ Set' : '❌ Missing');
console.log('OPENAI_MODEL:', process.env.OPENAI_MODEL || 'gpt-4o-mini');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

app.get('/', (req: Request, res: Response) => {
  const baseUrl = process.env.COOLIFY_FQDN || process.env.COOLIFY_URL || `http://localhost:${PORT}`;
  res.json({
    name: 'Vanessa Bot API',
    version: '1.0.0',
    status: 'running',
    baseUrl,
    features: {
      conversationMemory: true,
      sentimentAnalysis: true,
      upselling: true,
      personalityGuides: true
    },
    endpoints: {
      webhook: `${baseUrl}/webhook`,
      health: `${baseUrl}/health`,
      stats: `${baseUrl}/stats`,
      test: `${baseUrl}/test (POST) - Test the bot without Evolution API`
    }
  });
});

app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

app.get('/stats', (req: Request, res: Response) => {
  const memoryStats = conversationMemory.getStats();
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    memory: memoryStats
  });
});

app.post('/test', async (req: Request, res: Response) => {
  try {
    const { message, phoneNumber = 'test_user', pushName = 'Test User' } = req.body;

    if (!message) {
      return res.status(400).json({ error: 'Message is required' });
    }

    console.log(`\n🧪 TEST MESSAGE from ${pushName} (${phoneNumber}): ${message}`);

    const context = conversationMemory.getContext(phoneNumber);
    const userPreferences = context?.preferences || { mentionedServices: [], lastServiceInquired: undefined, preferredBranch: undefined };

    const searchResult = ragService.search(message);
    const foundServices = searchResult.services;

    const sentimentAnalysis = analyzeSentiment(message);
    const sentiment = sentimentAnalysis.sentiment;
    console.log(`📊 Sentiment: ${sentiment} (confidence: ${sentimentAnalysis.confidence.toFixed(2)})`);

    const upsellOpportunity = upsellingService.shouldUpsell(phoneNumber, message, sentiment, userPreferences)
      ? upsellingService.detectOpportunity(message, foundServices, userPreferences)
      : undefined;

    if (upsellOpportunity) {
      console.log(`💰 Upsell opportunity: ${upsellOpportunity.triggerService} → ${upsellOpportunity.suggestedService}`);
    }

    const formattedContext = formatContext(foundServices, searchResult.locations);
    const conversationHistory = conversationMemory.getHistory(phoneNumber);

    const response = await generateResponse(
      message,
      formattedContext,
      conversationHistory,
      upsellOpportunity,
      sentiment,
      { pushName, isRecurring: conversationHistory.length > 0, preferredBranch: userPreferences?.preferredBranch }
    );

    conversationMemory.addMessage(phoneNumber, message, 'user', sentiment);
    conversationMemory.addMessage(phoneNumber, response, 'assistant', sentiment);

    if (upsellOpportunity) {
      userPreferences.lastUpsellAttempt = new Date();
      conversationMemory.updatePreferences(phoneNumber, userPreferences);
    }

    const detectedServices = foundServices.map((s, i) => `${i + 1}. ${s.service} - ${s.price}`).join('\n');

    res.json({
      message,
      response,
      metadata: {
        sentiment: sentimentAnalysis,
        upsellOpportunity: upsellOpportunity ? {
          trigger: upsellOpportunity.triggerService,
          suggested: upsellOpportunity.suggestedService,
          reason: upsellOpportunity.reason
        } : null,
        detectedServices,
        conversationHistoryLength: conversationHistory.length
      }
    });
  } catch (error) {
    console.error('❌ Test endpoint error:', error);
    res.status(500).json({ error: 'Failed to process test message' });
  }
});

app.post('/webhook', handleWebhook);

app.use((req: Request, res: Response) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

app.listen(PORT, () => {
  const memoryStats = conversationMemory.getStats();
  const baseUrl = process.env.COOLIFY_FQDN || process.env.COOLIFY_URL || `http://localhost:${PORT}`;
  console.log(`\n✨ Vanessa Bot Server running on port ${PORT}`);
  console.log(`🌐 Base URL: ${baseUrl}`);
  console.log(`📡 Webhook endpoint: ${baseUrl}/webhook`);
  console.log(`🏥 Health check: ${baseUrl}/health`);
  console.log(`📊 Stats endpoint: ${baseUrl}/stats`);
  console.log(`\n📊 Memory Stats:`);
  console.log(`   - Total users: ${memoryStats.totalUsers}`);
  console.log(`   - Active conversations: ${memoryStats.activeConversations}`);
  console.log(`   - Avg messages per user: ${memoryStats.averageMessagesPerUser}`);
  console.log(`\n🎯 Features enabled:`);
  console.log(`   ✅ Conversation Memory (48h retention)`);
  console.log(`   ✅ Sentiment Analysis`);
  console.log(`   ✅ Intelligent Upselling`);
  console.log(`   ✅ Personality Guides (200+ variations)\n`);
});

export default app;
