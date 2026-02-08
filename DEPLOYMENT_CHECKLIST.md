# Deployment Checklist for Coolify

## ✅ Codebase Status

### Repository
- **Branch:** main
- **Status:** Clean (no uncommitted changes)
- **Sync:** Up to date with origin/main
- **Latest Commit:** `4d81f95` - fix: remove /manager/ from Evolution API base URL

### Files Updated
- ✅ `src/services/evolutionService.ts` - Fixed trailing slash issue
- ✅ `.env.example` - Updated with correct Evolution API URL
- ✅ `src/app.ts` - Uses Coolify FQDN in logs
- ✅ `Dockerfile` - Copies necessary files (system_prompt.md, vanity_data/)
- ✅ `.dockerignore` - Keeps system_prompt.md, excludes docs

---

## 🔧 Configuration for Coolify

### Environment Variables (MUST UPDATE)

```env
# ⚠️ CRITICAL: Update this URL - remove /manager/ at the end
EVOLUTION_API_URL=https://evolution.soul23.cloud

# Other variables (keep current values)
EVOLUTION_API_KEY=RaHNDk8eBZ9myHaDhHW5shtuNlS67A85
EVOLUTION_INSTANCE=noire
OPENAI_API_KEY=sk-proj-LDv6lHdcYszEwr-8I_ElwsM5LR4T8X8F9878ch0_H3W6gj6pK........
OPENAI_MODEL=gpt-4o-mini
PORT=3000
NODE_ENV=production
FORMBRICKS_URL=https://your-formbricks-instance.com/form/quejas
```

### ⚠️ IMPORTANT: Remove /manager/ from EVOLUTION_API_URL

**Current (WRONG):**
```
EVOLUTION_API_URL=https://evolution.soul23.cloud/manager/
```

**Correct:**
```
EVOLUTION_API_URL=https://evolution.soul23.cloud
```

---

## 📋 Deployment Steps in Coolify

### Step 1: Update Environment Variable
1. Go to your Coolify project
2. Go to "Environment" section
3. Find `EVOLUTION_API_URL`
4. Edit and change:
   - From: `https://evolution.soul23.cloud/manager/`
   - To: `https://evolution.soul23.cloud`
5. Save changes

### Step 2: Redeploy Application
1. Click "Deploy" button in Coolify
2. Wait for deployment to complete
3. Check that deployment shows "Running"

### Step 3: Test the Bot
1. Send a WhatsApp message to: `528441026472`
2. Wait for Vanessa's response
3. Check Coolify logs

### Step 4: Verify Logs

**SUCCESSFUL Response (Expected):**
```
✅ Loaded 65 services and 3 locations
✨ Vanessa Bot Server running on port 3000
🌐 Base URL: pw4400k8ws0s0ogc88ssko8s.soul23.cloud
📡 Webhook endpoint: pw4400k8ws0s0ogc88ssko8s.soul23.cloud/webhook

📨 Message from Test User (528441026472@lid): Hola
😊 Sentiment: neutral (confidence: 0)
🧠 History: 0 messages, User: New
🤖 Calling OpenAI with 0 history messages, sentiment: neutral, temp: 0.7
✅ OpenAI response generated (150 chars)

📤 Sending message to Evolution API:
   URL: https://evolution.soul23.cloud/message/sendText/noire
   Phone: 528441026472
   Text: ¡Hola! ✨ ¿En qué te puedo ayudar hoy?
   Delay: 1000ms
✅ Evolution API response: {"status":"PENDING",...}
✅ Message sent to 528441026472
```

**If still 404 Error:**
```
❌ Error sending message to Evolution API:
   Status: 404
   StatusText: Not Found
```
This means the URL is still wrong. Check `EVOLUTION_API_URL` in Coolify.

---

## 🎯 Summary

### What Was Fixed

1. **Docker Build Issues:**
   - ✅ Fixed .dockerignore to include system_prompt.md
   - ✅ Fixed Dockerfile to copy necessary files only

2. **Coolify FQDN:**
   - ✅ App now uses `COOLIFY_FQDN` for URLs in logs
   - ✅ Logs show production URLs instead of localhost

3. **Evolution API Endpoint:**
   - ✅ Found correct endpoint: `/message/sendText/{instance}`
   - ✅ Fixed base URL (removed `/manager/` suffix)
   - ✅ Tested and confirmed working with curl
   - ✅ Test message successfully delivered

4. **Debug Logs:**
   - ✅ Added detailed logs for Evolution API requests
   - ✅ Shows full URL, phone number, text, delay
   - ✅ Shows Evolution API response data

### Files in Repository

**Source Code (9 files):**
- src/app.ts
- src/controllers/webhookController.ts
- src/services/conversationMemory.ts
- src/services/evolutionService.ts
- src/services/openaiService.ts
- src/services/ragService.ts
- src/services/upsellingService.ts
- src/types/index.ts
- src/utils/sentimentAnalyzer.ts

**Configuration (5 files):**
- package.json
- package-lock.json
- tsconfig.json
- .env.example (UPDATED)
- .dockerignore (UPDATED)

**Docker (3 files):**
- Dockerfile (UPDATED)
- docker-compose.yml
- .dockerignore (UPDATED)

**Documentation (5 files):**
- README.md (UPDATED)
- COOLIFY.md (UPDATED)
- DEBUG_EVOLUTION.md
- EVOLUTION_API_ENDPOINTS.md
- DEPLOYMENT_CHECKLIST.md (this file)

**Data (2 files):**
- vanity_data/services.jsonl
- vanity_data/locations.jsonl

**Scripts (1 file):**
- test-evolution-endpoints.sh

---

## ✅ Ready for Deployment

**Repository Status:**
- ✅ All changes committed
- ✅ All changes pushed to GitHub
- ✅ Working tree clean
- ✅ Up to date with origin/main

**GitHub URL:** https://github.com/marcogll/bot_vanity.git

**Latest Commit:** `4d81f95` - fix: remove /manager/ from Evolution API base URL

---

## 🚀 Next Steps

1. Update `EVOLUTION_API_URL` in Coolify (remove /manager/)
2. Redeploy in Coolify
3. Send test WhatsApp message
4. Verify logs show successful message delivery
5. Vanessa is live! 🎉

---

## 📊 Key Reminders

### Do NOT:
- ❌ Keep `/manager/` at the end of EVOLUTION_API_URL
- ❌ Use old test API keys
- ❌ Skip updating environment variables

### Do:
- ✅ Set `EVOLUTION_API_URL=https://evolution.soul23.cloud`
- ✅ Use your real OpenAI API key
- ✅ Update both `EVOLUTION_API_URL` and `OPENAI_API_KEY`
- ✅ Check logs after deployment

---

**Deployment Status:** ✅ READY
**Repository URL:** https://github.com/marcogll/bot_vanity
**Coolify App:** pw4400k8ws0s0ogc88ssko8s.soul23.cloud
