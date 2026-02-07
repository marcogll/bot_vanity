# Technical Specifications for AI Developer

## Goal
Build a WhatsApp Chatbot using Node.js (TypeScript) that acts as a RAG interface for Vanity Salon services.

## Tech Stack
- Runtime: Node.js (Latest LTS)
- Language: TypeScript
- Framework: Express.js (to receive Webhooks from Evolution API)
- AI: OpenAI Node SDK (Model: gpt-4o-mini)
- RAG Strategy: 
  - Load `vanity_data/*.jsonl` into memory on startup (Low data volume < 1MB).
  - Use cosine similarity for retrieval (no external Vector DB needed for MVP).
  - Library: `langchain` or simple vector math.

## Evolution API Integration
- The bot must expose a POST endpoint `/webhook/evolution`.
- It must filter messages to ignore `fromMe: true` (bot's own messages).
- It must send messages using the Evolution API HTTP endpoint `/message/sendText`.

## Project Structure
- /src
  - /config (env vars)
  - /services (OpenAI service, RAG service, Evolution Service)
  - /controllers (Webhook controller)
  - /utils (Text cleaning, RAG matching)
  - index.ts (Entry point)