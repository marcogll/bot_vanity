#!/bin/bash

# Test different payload formats for Evolution API

BASE_URL="https://evolution.soul23.cloud/message/sendText/noire"
API_KEY="RaHNDk8eBZ9myHaDhHW5shtuNlS67A85"
PHONE="249391621378064"

echo "🧪 Testing different payload formats..."
echo ""

# Test 1: Current format
echo "Test 1: Current format (number only)"
RESPONSE=$(curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -H "apikey: $API_KEY" \
  -d "{\"number\":\"$PHONE\",\"text\":\"Test\",\"delay\":1000}")

STATUS=$(echo "$RESPONSE" | jq -r '.status // .error // "unknown"')
echo "  Status: $STATUS"
if [ "$STATUS" = "200" ] || [ "$STATUS" = "201" ] || [ "$STATUS" = "PENDING" ]; then
  echo "  ✅ SUCCESS"
else
  echo "  ❌ FAILED"
fi
echo ""

# Test 2: With country code
echo "Test 2: With country code (+52)"
RESPONSE=$(curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -H "apikey: $API_KEY" \
  -d "{\"number\":\"+52$PHONE\",\"text\":\"Test\",\"delay\":1000}")

STATUS=$(echo "$RESPONSE" | jq -r '.status // .error // "unknown"')
echo "  Status: $STATUS"
if [ "$STATUS" = "200" ] || [ "$STATUS" = "201" ] || [ "$STATUS" = "PENDING" ]; then
  echo "  ✅ SUCCESS"
else
  echo "  ❌ FAILED"
fi
echo ""

# Test 3: With @s.whatsapp.net
echo "Test 3: With @s.whatsapp.net"
RESPONSE=$(curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -H "apikey: $API_KEY" \
  -d "{\"number\":\"$PHONE@s.whatsapp.net\",\"text\":\"Test\",\"delay\":1000}")

STATUS=$(echo "$RESPONSE" | jq -r '.status // .error // "unknown"')
echo "  Status: $STATUS"
if [ "$STATUS" = "200" ] || [ "$STATUS" = "201" ] || [ "$STATUS" = "PENDING" ]; then
  echo "  ✅ SUCCESS"
else
  echo "  ❌ FAILED"
fi
echo ""

# Test 4: No delay
echo "Test 4: No delay"
RESPONSE=$(curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -H "apikey: $API_KEY" \
  -d "{\"number\":\"$PHONE\",\"text\":\"Test\"}")

STATUS=$(echo "$RESPONSE" | jq -r '.status // .error // "unknown"')
echo "  Status: $STATUS"
if [ "$STATUS" = "200" ] || [ "$STATUS" = "201" ] || [ "$STATUS" = "PENDING" ]; then
  echo "  ✅ SUCCESS"
else
  echo "  ❌ FAILED"
fi
echo ""

# Test 5: With delay: 0
echo "Test 5: With delay: 0"
RESPONSE=$(curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -H "apikey: $API_KEY" \
  -d "{\"number\":\"$PHONE\",\"text\":\"Test\",\"delay\":0}")

STATUS=$(echo "$RESPONSE" | jq -r '.status // .error // "unknown"')
echo "  Status: $STATUS"
if [ "$STATUS" = "200" ] || [ "$STATUS" = "201" ] || [ "$STATUS" = "PENDING" ]; then
  echo "  ✅ SUCCESS"
else
  echo "  ❌ FAILED"
fi
echo ""

echo "🎯 Test complete!"
