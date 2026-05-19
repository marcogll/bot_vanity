# Guía de Migración Operativa - Sofia Role Runtime

## Objetivo

Esta guía documenta el proceso para activar el Runtime V2 en producción manteniendo compatibilidad total con el comportamiento actual de Vanity.

## Estado Actual

- **Runtime V1**: Activo y productivo
- **Runtime V2**: Implementado y probado, corre en shadow mode
- **Tenant vanity**: Configurado en `tenants/vanity/business.json`
- **Suite de tests**: 328 tests passing

## Flags de Activación

### Variables de Entorno

```env
# Control principal de V2
BOT_RUNTIME_V2_ENABLED=false          # false = V1 activo, true = V2 activo
BOT_RUNTIME_V2_SHADOW_MODE=true       # true = V2 evalúa pero no responde, false = V2 puede responder
BOT_RUNTIME_V2_ALLOWED_NUMBERS=       # Números permitidos para V2 cuando shadow_mode=false

# Control de roles
ROLE_BLEND_ENABLED=false              # false = sin mezcla de roles, true = RoleBlender activo

# Configuración de tenant
TENANT_CONFIG_PATH=tenants            # Path a configuraciones de tenant
DEFAULT_TENANT_ID=vanity              # Tenant por defecto
```

## Fases de Activación

### Fase 1: Shadow Mode (Recomendado para inicio)

```env
BOT_RUNTIME_V2_ENABLED=true
BOT_RUNTIME_V2_SHADOW_MODE=true
```

**Comportamiento:**
- V1 sigue respondiendo al cliente
- V2 evalúa contexto, intención, estado, política y plan
- V2 NO envía mensajes
- El resultado se registra en logs con prefijo `Runtime V2 shadow:`
- Se genera comparación V1 vs V2 en logs

**Validación:**
```bash
# Ejecutar script de validación
.venv/bin/python scripts/validate_migration.py

# Revisar logs para comparaciones
grep "Runtime V2 comparison" logs/app.log
```

### Fase 2: Allowlist Controlada

```env
BOT_RUNTIME_V2_ENABLED=true
BOT_RUNTIME_V2_SHADOW_MODE=false
BOT_RUNTIME_V2_ALLOWED_NUMBERS=528448087770,528445949068
```

**Comportamiento:**
- V2 toma control SOLO para números en la allowlist
- V1 sigue respondiendo para todos los demás números
- Permite validar V2 con usuarios de prueba reales

**Validación:**
- Monitorear conversaciones de números en allowlist
- Comparar respuestas V1 vs V2 en logs
- Verificar que no haya regresiones

### Fase 3: Producción Completa

```env
BOT_RUNTIME_V2_ENABLED=true
BOT_RUNTIME_V2_SHADOW_MODE=false
BOT_RUNTIME_V2_ALLOWED_NUMBERS=
ROLE_BLEND_ENABLED=true
```

**Comportamiento:**
- V2 toma control de todas las conversaciones
- RoleBlender activo para mezcla de roles por estado
- V1 queda como fallback en caso de error

**Rollback:**
```env
BOT_RUNTIME_V2_ENABLED=false
```

## Validación de Compatibilidad

### Script de Validación

```bash
.venv/bin/python scripts/validate_migration.py
```

Este script:
1. Carga configuración de tenant vanity
2. Ejecuta 12 escenarios predefinidos
3. Compara decisiones V1 vs V2
4. Reporta porcentaje de alineación

### Escenarios de Validación

| Escenario | V1 Flow | V2 Expected |
|-----------|---------|-------------|
| Nuevo lead - saludo | initial_greeting | SILENCE (missing name) |
| Lead proporciona nombre | name_followup | SEND_STRUCTURED_REPLY |
| Lead pregunta servicio | local_booking_flow | ASK_LLM |
| Lead pregunta precio | llm | ASK_LLM |
| Queja fuerte | human_handover | ESCALATE_HUMAN |
| Pide hablar con humano | human_handover | ESCALATE_HUMAN |
| Envía comprobante | structured_booking | ASK_LLM (con contexto) |
| Incidente | llm | ASK_LLM |
| Inyección de prompt | llm (bloqueado) | RESPOND (bloqueado) |
| Bot pausado | silence | SILENCE |

## Tenant Vanity

### Configuración Actual

Archivo: `tenants/vanity/business.json`

```json
{
  "tenant_id": "vanity",
  "business": {
    "business_id": "vanity",
    "display_name": "Vanity Nail Salon",
    "industry": "beauty_salon",
    "settings": {
      "booking_url": "https://vanitynails.fresh.com",
      "payment_url": "https://www.paypal.com/ncp/payment/L3AC4D47J3QDN",
      "timezone": "America/Monterrey",
      "language": "es-MX"
    }
  },
  "bot": {
    "bot_id": "sofia",
    "display_name": "Sofia",
    "default_language": "es-MX",
    "visible_role": "Recepcionista digital/concierge de Vanity Nail Salon"
  },
  "staff_roles": {
    "frontdesk": {...},
    "manager": {...},
    "staff1": {...}
  },
  "default_role_weights": {
    "frontdesk": 0.7,
    "manager": 0.2,
    "staff1": 0.1
  },
  "state_role_weights": {...},
  "policies": {
    "booking": {...},
    "escalation": {...},
    "style": {...},
    "bot_authority_limits": [...]
  }
}
```

### Conocimiento del Tenant

Archivos en `tenants/vanity/knowledge/`:
- `identity.md` - Identidad del bot, límites, estilo
- `policies.md` - Políticas de booking, escalación, autoridad
- `booking_flow.md` - Flujo estructurado de booking
- `roles.md` - Perfiles de staff y mezcla de roles
- `escalation.md` - Políticas de escalación humana

## Rollback

Si se detectan problemas en producción:

1. **Rollback inmediato:**
   ```env
   BOT_RUNTIME_V2_ENABLED=false
   ```

2. **Reiniciar aplicación:**
   ```bash
   docker-compose restart vanessa-app
   ```

3. **Verificar que V1 está activo:**
   ```bash
   curl http://localhost:8001/health
   ```

## Monitoreo

### Logs Clave

```bash
# Comparaciones V1 vs V2
grep "Runtime V2 comparison" logs/app.log

# Decisiones V2
grep "Runtime V2 shadow" logs/app.log
grep "Runtime V2 control" logs/app.log

# Escalaciones
grep "Human handover" logs/app.log

# Errores
grep "Runtime V2.*failed" logs/app.log
```

### Métricas a Monitorear

- Porcentaje de alineación V1 vs V2
- Tasa de escalaciones humanas
- Tiempo de respuesta promedio
- Tasa de errores

## Checklist de Producción

- [ ] Tenant vanity configurado correctamente
- [ ] Documentos de conocimiento en `tenants/vanity/knowledge/`
- [ ] Script de validación pasa (328 tests)
- [ ] Shadow mode activado y validado
- [ ] Allowlist configurada con números de prueba
- [ ] Monitoreo de logs configurado
- [ ] Plan de rollback documentado
- [ ] Equipo informado del cambio

## Soporte

Para dudas o problemas:
- Revisar `docs/refactor_status.md`
- Revisar `docs/sofia_role_runtime_refactor_plan.md`
- Contactar al equipo de desarrollo
