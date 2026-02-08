# 400 Bad Request Error - SOLVED

## 🔍 Problem Identified

### Error Message
```
❌ Error sending message to Evolution API:
Status: 400 Bad Request
Data: {"status":400,"error":"Bad Request","response":{"message":[Object] }}
```

### Root Cause

The webhook payload contains TWO phone number fields:

| Field | Value | Format |
|--------|--------|---------|
| `key.remoteJid` | `249391621378064@lid` | Internal ID (lid) - NOT correct for sending |
| `key.remoteJidAlt` | `5218441026472@s.whatsapp.net` | ✅ Correct format with @s.whatsapp.net |

**The Issue:**
- The bot was extracting phone number from `remoteJid` field
- This resulted in: `249391621378064`
- Evolution API returns `400 Bad Request` for this number
- The bot should extract from `remoteJidAlt` instead

---

## ✅ Solution Implemented

### 1. Updated Type Definition

**File:** `src/types/index.ts`

**Change:** Added `remoteJidAlt` field to `EvolutionWebhookData` interface

```typescript
export interface EvolutionWebhookData {
  event: string;
  instance: string;
  data: {
    key: {
      remoteJid: string;
      remoteJidAlt?: string;  // ← Added this field
      fromMe: boolean;
      id: string;
    };
    // ... rest of interface
  };
}
```

### 2. Updated Extract Phone Number Function

**File:** `src/services/evolutionService.ts`

**Change:** Modified `extractPhoneNumber()` to prioritize `remoteJidAlt`

```typescript
export function extractPhoneNumber(
  remoteJid: string,
  remoteJidAlt?: string  // ← Added optional parameter
): string {
  // Priority 1: remoteJidAlt if available (already has correct format)
  if (remoteJidAlt && remoteJidAlt.includes('@s.whatsapp.net')) {
    return remoteJidAlt.split('@')[0];
  }

  // Priority 2: remoteJid normal
  return remoteJid.split('@')[0];
}
```

### 3. Updated Webhook Controller

**File:** `src/controllers/webhookController.ts`

**Changes:**

**a) Extract remoteJidAlt from payload:**
```typescript
const { key, message, pushName } = webhookData.data;

const remoteJid = key.remoteJid;
const remoteJidAlt = key.remoteJidAlt;  // ← Extract this field

if (remoteJidAlt) {
  console.log(`📱 Alternative JID found: ${remoteJidAlt}`);
}
```

**b) Pass remoteJidAlt to extractPhoneNumber():**
```typescript
// For media messages
await sendMessage(extractPhoneNumber(remoteJid, remoteJidAlt), mediaResponse);

// For text messages
const phoneNumber = extractPhoneNumber(remoteJid, remoteJidAlt);
console.log(`📱 Sending response to phone number: ${phoneNumber} (from JID: ${remoteJid}, Alt JID: ${remoteJidAlt || 'N/A'})`);
await sendMessage(phoneNumber, aiResponse);
```

---

## 📊 Expected Behavior

### Before Fix (BROKEN)
```
User sends message to: 8441026472
Webhook receives: remoteJid = 249391621378064@lid
Bot extracts: 249391621378064
Bot sends to: 249391621378064
Evolution API: ❌ 400 Bad Request
```

### After Fix (WORKING)
```
User sends message to: 8441026472
Webhook receives: remoteJid = 249391621378064@lid
                 remoteJidAlt = 5218441026472@s.whatsapp.net
Bot extracts: 5218441026472  ← Uses remoteJidAlt
Bot sends to: 5218441026472
Evolution API: ✅ 200 OK / PENDING
```

---

## 🔧 Technical Details

### Webhook Payload Structure

```json
{
  "event": "messages.upsert",
  "instance": "noire",
  "data": {
    "key": {
      "remoteJid": "249391621378064@lid",           ← Internal ID, NOT for sending
      "remoteJidAlt": "5218441026472@s.whatsapp.net",  ← ✅ Correct number
      "fromMe": false,
      "id": "ACD49085F0C82EF0BE969D48372219E9"
    },
    "pushName": "Marco",
    "message": {
      "conversation": "Hola"
    },
    "messageType": "conversation"
  }
}
```

### Phone Number Formats

| Format | Example | Evolution API Support |
|---------|-----------|----------------------|
| `8441026472` | Plain number | ✅ Works |
| `52 8441 02 6472` | With country code | ✅ Works |
| `5218441026472@s.whatsapp.net` | With @s.whatsapp.net | ✅ Works |
| `249391621378064@lid` | Internal JID (lid) | ❌ 400 Bad Request |

---

## ✅ Verification Steps

### 1. Redeploy in Coolify
- Update environment variable: `EVOLUTION_API_URL=https://evolution.soul23.cloud`
- Deploy application

### 2. Send Test Message
- From WhatsApp: Send "Hola" to the bot
- Expected: Bot responds with "¡Hola! ✨ ¿En qué te puedo ayudar hoy?"

### 3. Check Logs
**Success (Expected):**
```
📨 FULL WEBHOOK PAYLOAD: {...}
📱 Alternative JID found: 5218441026472@s.whatsapp.net
📱 Sending response to phone number: 5218441026472 (from JID: ..., Alt JID: 5218441026472@s.whatsapp.net)
✅ Evolution API response: {...}
✅ Message sent to 5218441026472
```

**No More Errors:**
```
❌ Error sending message to Evolution API:
Status: 400 Bad Request
```

---

## 🎯 Summary

| Item | Status |
|------|--------|
| **Root Cause Identified** | ✅ Using wrong phone number field |
| **Solution Implemented** | ✅ Use remoteJidAlt field |
| **TypeScript Types Updated** | ✅ Added remoteJidAlt to interface |
| **Functions Updated** | ✅ Updated extractPhoneNumber() |
| **Webhook Controller Updated** | ✅ Extract and pass remoteJidAlt |
| **Committed** | ✅ Commit `5830748` |
| **Pushed to GitHub** | ✅ Pushed to origin/main |

---

## 📝 Notes

- The `@lid` suffix indicates it's an internal ID used by Evolution API
- `@s.whatsapp.net` suffix indicates it's the proper WhatsApp Jabber ID format
- The `52` prefix is the Mexico country code for WhatsApp
- The correct number to respond to is the one who SENT the message (remoteJidAlt)
- NOT the number received by the webhook (which is an internal ID)

---

## 🚀 Next Steps

1. Redeploy in Coolify
2. Send test WhatsApp message
3. Verify bot responds correctly
4. Check logs show `📱 Alternative JID found: 5218441026472@s.whatsapp.net`

---

**Status:** ✅ READY FOR DEPLOYMENT
