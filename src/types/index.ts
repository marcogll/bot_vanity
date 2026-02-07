export interface Service {
  id: string;
  category: string;
  service: string;
  price: string;
  duration: string;
  description: string;
}

export interface Location {
  id: string;
  category: string;
  name: string;
  zone?: string;
  address?: string;
  maps_link?: string;
  booking_link?: string;
  description: string;
}

export interface EvolutionWebhookData {
  event: string;
  instance: string;
  data: {
    key: {
      remoteJid: string;
      fromMe: boolean;
      id: string;
    };
    pushName: string;
    message: {
      conversation?: string;
      extendedTextMessage?: {
        text: string;
      };
      imageMessage?: any;
    };
    messageType: string;
  };
}

export interface EvolutionSendMessage {
  number: string;
  text: string;
  delay?: number;
}

export interface SearchContext {
  services: Service[];
  locations: Location[];
}

// Conversation Memory Types
export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sentiment?: 'positive' | 'neutral' | 'negative';
}

export interface ConversationResult {
  booked: boolean;
  serviceBooked?: string;
  branch?: string;
  timestamp: Date;
}

export interface UserContext {
  remoteJid: string;
  pushName?: string;
  messages: ConversationMessage[]; // Últimos 10 mensajes
  lastActive: Date;
  firstContact: Date;
  preferences?: {
    preferredBranch?: string;
    mentionedServices: string[];
    lastServiceInquired?: string;
    lastUpsellAttempt?: Date;
  };
  result?: ConversationResult;
  sentimentHistory: ('positive' | 'neutral' | 'negative')[];
}

// Sentiment Analysis Types
export interface SentimentAnalysis {
  sentiment: 'positive' | 'neutral' | 'negative';
  confidence: number;
  keywords: string[];
}

// Upselling Types
export interface UpsellOpportunity {
  triggerService: string;
  suggestedService: string;
  reason: string;
  priority: 'high' | 'medium' | 'low';
}

// Memory Stats Types
export interface MemoryStats {
  totalUsers: number;
  activeConversations: number;
  averageMessagesPerUser: number;
  conversationsCleaned: number;
}