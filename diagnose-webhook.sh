#!/bin/bash

# Script para diagnosticar qué envía Evolution API al webhook
# Este script debe ejecutarse en tu servidor Coolify

echo "🔍 Diagnosticador de Webhook de Evolution API"
echo ""

echo "📋 Instrucciones:"
echo "1. Abre los logs de tu aplicación en Coolify"
echo "2. Envía un mensaje de WhatsApp: 'Hola bot'"
echo "3. Busca en los logs: '📨 Message from'"
echo "4. Copia el objeto JSON completo que aparece en los logs"
echo ""
echo "5. Pega el JSON aquí:"
echo "   (será analizado para encontrar el número correcto)"
echo ""
echo "📄 También puedes verificar en el panel de Evolution API:"
echo "   → Logs de Webhook"
echo "   → Qué datos está enviando al endpoint"
echo "   → El campo 'key' debería tener 'remoteJid' con el número 8441026472"
echo ""
echo "🎯 El webhook debería enviar algo como:"
echo '{
  "event": "messages.upsert",
  "data": {
    "key": {
      "remoteJid": "5218441026472@s.whatsapp.net",  <- Este es el número del usuario
      "fromMe": false,
      "id": "xxx"
    },
    "message": {...},
    "pushName": "Usuario"
  }
}'
echo ""
echo "📱 NOTA: El remoteJid es el número del REMITENTE (quien envió)"
echo "   NO el número de la instancia (1206472)"
echo "   Si el webhook envía 249391621378064, está mal configurado"
