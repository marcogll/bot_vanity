#!/bin/bash

# Test different Evolution API endpoints to find the correct one

BASE_URL="https://evolution.soul23.cloud/manager"
INSTANCE="noire"
API_KEY="RaHNDk8eBZ9myHaDhHW5shtuNlS67A85"
PHONE="528441026472"

echo "🧪 Testing Evolution API endpoints..."
echo ""

# Test different endpoints
ENDPOINTS=(
  "/message/sendText/$INSTANCE"
  "/text/send/$INSTANCE"
  "/message/send/$INSTANCE"
  "/send/$INSTANCE/text"
  "/message/$INSTANCE/sendText"
  "/textMessage/send/$INSTANCE"
)

for endpoint in "${ENDPOINTS[@]}"; do
  echo "Testing: $endpoint"
  FULL_URL="${BASE_URL}${endpoint//$INSTANCE/$INSTANCE}"

  RESPONSE=$(curl -s -X POST "$FULL_URL" \
    -H "Content-Type: application/json" \
    -H "apikey: $API_KEY" \
    -d "{\"number\":\"$PHONE\",\"text\":\"Test\",\"delay\":1000}")

  STATUS=$(echo "$RESPONSE" | jq -r '.status // .error // "success"')
  MESSAGE=$(echo "$RESPONSE" | jq -r '.message // .error // "OK"')

  if [ "$STATUS" != "404" ]; then
    echo "  ✅ SUCCESS! Status: $STATUS"
    echo "  📄 Message: $MESSAGE"
    echo "  🔗 Working endpoint: $endpoint"
    echo ""
  else
    echo "  ❌ FAILED - 404 Not Found"
    echo ""
  fi
done

echo "🎯 Test complete!"
