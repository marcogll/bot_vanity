# Evolution API Configuration Options

## Current Issue
Endpoint `/message/sendText/{instance}` returns 404 Not Found

## Possible Correct Endpoints

Based on different versions of Evolution API, try these endpoints:

### Option 1: /text/send/{instance}
```
EVOLUTION_API_URL=https://evolution.soul23.cloud/manager
EVOLUTION_API_KEY=RaHNDk8eBZ9myHaDhHW5shtuNlS67A85
EVOLUTION_INSTANCE=noire
EVOLUTION_API_ENDPOINT=/text/send
```

Full URL would be: `https://evolution.soul23.cloud/manager/text/send/noire`

### Option 2: /message/send/{instance}
```
EVOLUTION_API_URL=https://evolution.soul23.cloud/manager
EVOLUTION_API_ENDPOINT=/message/send
```

Full URL would be: `https://evolution.soul23.cloud/manager/message/send/noire`

### Option 3: /send/{instance}/text
```
EVOLUTION_API_URL=https://evolution.soul23.cloud/manager
EVOLUTION_API_ENDPOINT=/send/{instance}/text
```

Full URL would be: `https://evolution.soul23.cloud/manager/send/noire/text`

### Option 4: /message/{instance}/sendText
```
EVOLUTION_API_URL=https://evolution.soul23.cloud/manager
EVOLUTION_API_ENDPOINT=/message/{instance}/sendText
```

Full URL would be: `https://evolution.soul23.cloud/manager/message/noire/sendText`

### Option 5: No /manager/ prefix
```
EVOLUTION_API_URL=https://evolution.soul23.cloud
EVOLUTION_API_ENDPOINT=/message/sendText/{instance}
```

Full URL would be: `https://evolution.soul23.cloud/message/sendText/noire`

### Option 6: Different base path
```
EVOLUTION_API_URL=https://evolution.soul23.cloud/api
EVOLUTION_API_ENDPOINT=/message/sendText/{instance}
```

Full URL would be: `https://evolution.soul23.cloud/api/message/sendText/noire`

## Testing Each Option

Use this curl command to test each option:

```bash
curl -X POST "FULL_URL" \
  -H "Content-Type: application/json" \
  -H "apikey: RaHNDk8eBZ9myHaDhHW5shtuNlS67A85" \
  -d '{"number":"528441026472","text":"Test message","delay":1000}'
```

Replace `FULL_URL` with one of the options above.

## Quick Solution

Once you find the working endpoint, add this environment variable in Coolify:

```
EVOLUTION_API_ENDPOINT=/text/send
```

Then update the code to use this variable (see next section).

## Code Update Required

In `src/services/evolutionService.ts`, replace:

```typescript
const api = axios.create({
  baseURL: `${EVOLUTION_API_URL}/message/sendText/${EVOLUTION_INSTANCE}`,
  headers: {
    'Content-Type': 'application/json',
    'apikey': EVOLUTION_API_KEY
  }
});
```

With:

```typescript
const EVOLUTION_API_ENDPOINT = process.env.EVOLUTION_API_ENDPOINT || '/message/sendText';
const api = axios.create({
  baseURL: `${EVOLUTION_API_URL}${EVOLUTION_API_ENDPOINT}/${EVOLUTION_INSTANCE}`,
  headers: {
    'Content-Type': 'application/json',
    'apikey': EVOLUTION_API_KEY
  }
});
```

## Next Steps

1. Test each endpoint option with curl above
2. Find which one works (returns 200 instead of 404)
3. Add `EVOLUTION_API_ENDPOINT` environment variable in Coolify
4. Update code to use `EVOLUTION_API_ENDPOINT`
5. Redeploy and test
