# Debugging Evolution API Integration

## Current Issue
Bot generates responses but messages are not being delivered via WhatsApp.

## Possible Causes

### 1. Wrong Evolution API Endpoint
Evolution API has different endpoint formats depending on the version:

**Common endpoints:**
- `/message/sendText/{instance}` - Used in current code
- `/text/send/{instance}` - Alternative endpoint
- `/message/send/{instance}` - Another alternative

### 2. Phone Number Format
Evolution API may require:
- Plain number: `525212345678`
- With JID format: `525212345678@s.whatsapp.net`
- With country code only: `+525212345678`

### 3. Instance Not Connected
The Evolution instance `noire` may not be:
- Connected to WhatsApp
- Authorized to send messages
- Active in the Evolution panel

### 4. API Key Permissions
The API key may not have permissions to:
- Send messages
- Access the specific instance
- Make POST requests

## Debugging Steps

### 1. Check Evolution API Panel
1. Log in to your Evolution API instance
2. Verify the instance `noire` is:
   - ✅ Connected (green status)
   - ✅ Active
   - ✅ Can send messages
3. Check the API key permissions
4. Verify the API URL format in the panel

### 2. Test Evolution API Directly
Use curl to test the endpoint:

```bash
curl -X POST "https://evolution.soul23.cloud/manager/message/sendText/noire" \
  -H "Content-Type: application/json" \
  -H "apikey: RaHNDk8eBZ9myHaDhHW5shtuNlS67A85" \
  -d '{
    "number": "YOUR_PHONE_NUMBER",
    "text": "Test message from curl",
    "delay": 1000
  }'
```

Replace `YOUR_PHONE_NUMBER` with your actual number (e.g., `525212345678`)

### 3. Check Detailed Logs (After Redeploy)
After redeploying, the logs will show:
```
📤 Sending message to Evolution API:
   URL: https://evolution.soul23.cloud/manager/message/sendText/noire
   Phone: 525212345678
   Text: ¡Hola! ✨
   Delay: 1000ms
✅ Evolution API response: {...}
✅ Message sent to 525212345678
```

Or error details:
```
❌ Error sending message to Evolution API:
   Status: 404
   StatusText: Not Found
   Data: {...}
```

### 4. Common Evolution API Endpoint Formats

Check your Evolution API documentation for the correct endpoint:

**Option A (Current):**
```
POST /message/sendText/{instance}
```

**Option B:**
```
POST /text/send/{instance}
```

**Option C:**
```
POST /message/send/{instance}
```

**Option D:**
```
POST /send/{instance}/text
```

## Quick Fixes

### Fix 1: Update Endpoint
If the endpoint is wrong, update `src/services/evolutionService.ts`:

```typescript
const api = axios.create({
  baseURL: `${EVOLUTION_API_URL}/text/send/${EVOLUTION_INSTANCE}`,  // Change endpoint
  headers: {
    'Content-Type': 'application/json',
    'apikey': EVOLUTION_API_KEY
  }
});
```

### Fix 2: Update Phone Number Format
If the number needs @s.whatsapp.net, update `src/services/evolutionService.ts`:

```typescript
const payload: EvolutionSendMessage = {
  number: phoneNumber.includes('@') ? phoneNumber : `${phoneNumber}@s.whatsapp.net`,  // Add @s.whatsapp.net if missing
  text: text,
  delay: delay
};
```

### Fix 3: Update Instance Name
If the instance name is different, update environment variable in Coolify:
- `EVOLUTION_INSTANCE=correct_instance_name`

## Next Steps

1. **Redeploy in Coolify** to get detailed logs
2. **Send a test message** via WhatsApp
3. **Check the logs** in Coolify to see:
   - The exact URL being called
   - The phone number being sent
   - Evolution API response
4. **Test with curl** using the same URL/phone/key
5. **Check Evolution API panel** to verify instance status

## Evolution API Resources

- Evolution API Documentation: Check your instance panel for API docs
- Webhook Configuration: Verify webhook is set to your Coolify URL
- Instance Status: Check if instance is connected and active

## Contact Support

If none of the above works:
1. Check Evolution API error messages in logs
2. Verify API key is valid and has permissions
3. Contact Evolution API support with the error details
