# Manual de Usuario - Bot Vanity

Este documento describe cómo usar los comandos administrativos del bot.

## Requisitos Previos

Para ejecutar comandos administrativos, tu número de teléfono debe estar registrado en las variables de entorno:

- `ADMIN_PHONE_NUMBER` - Un solo número
- `ADMIN_PHONE_NUMBERS` - Múltiples números separados por comas

El bot verifica el número del-remitente contra esta lista antes de ejecutar cualquier comando.

---

## Comandos de Control del Bot

### 1. Pausar el Bot (Chat Individual)

**Comando:** `serac` o `serac pausa` o `serac pause`

**Efecto:** El bot deja de responder solo en el chat donde se envió el comando. Otros usuarios no se ven afectados.

**Ejemplo:**
```
Usuario: serac
Bot: Bot pausado para este chat. Sofía continuará respondiendo en otros chats.
```

---

### 2. Reanudar el Bot (Chat Individual)

**Comando:** `serac -r` o `serac resume` o `serac reanudar`

**Efecto:** El bot vuelve a responder en el chat específico donde se envía.

**Ejemplo:**
```
Usuario: serac -r
Bot: Bot reactivado para este chat. Sofía puede volver a responder.
```

---

### 3. Apagar el Bot (Global)

**Comando:** `serac shutdown` o `serac apagar` o `serac apagar bot`

**Efecto:** El bot deja de responder a **TODOS** los usuarios. Solo el admin puede reactivarlo.

**Importante:** Usa este comando con precaución. Todos los usuarios recibirán silencio del bot.

**Ejemplo:**
```
Usuario: serac shutdown
Bot: ⚠️ Bot shutdown global ejecutado. Sofía ha dejado de responder a TODOS los usuarios. Para reactivarlo, envía `serac start` desde este número.
```

---

### 4. Reanudar el Bot (Global)

**Comando:** `serac start` o `serac iniciar` o `serac start bot` o `serac iniciar bot`

**Efecto:** El bot vuelve a responder a todos los usuarios.

**Ejemplo:**
```
Usuario: serac start
Bot: ✅ Bot global reactivado. Sofía vuelve a responder a todos los usuarios.
```

---

## Comandos de Memoria

### 5. Borrar Memoria (Chat Individual)

**Comando:** `dipiridú`

**Efecto:** Solicita confirmación para borrar la memoria e historial de conversación en el chat específico.

**Ejemplo:**
```
Usuario: dipiridú
Bot: ¿Confirmas que deseas borrar la memoria e historial de este chat en Sofía? Responde sí para borrar este chat o no para cancelar.
```

**Confirmación:** Responde `sí` para confirmar o `no` para cancelar.

---

### 6. Borrar Base de Datos Completa

**Comando:** `borrar toda la db`

**Efecto:** Solicita confirmación para borrar TODA la base de datos del bot (todas las conversaciones, memorias, citas, etc.).

**Advertencia:** Este comando es destructivo y no se puede deshacer.

**Ejemplo:**
```
Usuario: borrar toda la db
Bot: ¿Confirmas que deseas borrar TODA la base de datos de Sofía? Responde exactamente `sí borrar toda la db` para borrar todo o `no` para cancelar.
```

**Confirmación:** Responde `sí borrar toda la db` para confirmar o `no` para cancelar.

---

## Comandos de Diagnóstico

### 7. Debug de Remitente

**Comando:** `debug sender` o `sender`

**Efecto:** Muestra información de diagnóstico sobre elremitente del mensaje (útil para troubleshooting).

**Ejemplo:**
```
Usuario: debug sender
Bot: Debug sender
remote_jid: <tu_numero>@s.whatsapp.net
sender: <tu_numero>
reply_candidates: []
reply_diagnostics: []
target: <tu_numero>
instance: vanity-instance
message_type: conversation
```

---

## Resumen de Comandos

| Comando | Acción | Alcance |
|---------|--------|---------|
| `serac` | Pausar bot | Chat individual |
| `serac -r` / `serac resume` | Reanudar bot | Chat individual |
| `serac shutdown` | Apagar bot | **Global** |
| `serac start` | Reanudar bot | **Global** |
| `dipiridú` | Borrar memoria | Chat individual |
| `borrar toda la db` | Borrar DB completa | **Todo el sistema** |
| `debug sender` | Info de diagnóstico | Chat individual |

---

## Notas de Seguridad

1. **Solo el admin puede ejecutar:** Cualquier comando que no venga de un número autorizado será rechazado con el mensaje: "No puedo ejecutar ese comando administrativo desde este número."

2. **Confirmaciones obligatorio:** Los comandos destructivos (`dipiridú`, `borrar toda la db`) requieren confirmación explícita.

3. **Logging:** Todos los comandos administrativos son registrados en los logs del sistema.

---

## Solución de Problemas

### El bot no responde a comandos admin

1. Verifica que tu número esté en `ADMIN_PHONE_NUMBERS` en el archivo `.env`
2. El número debe estar en formato WhatsApp (con código de país, sin +)
3. Reinicia el servidor después de modificar `.env`

### El bot no responde después de `serac shutdown`

1. Asegúrate de usar `serac start` desde el mismo número que ejecutó el shutdown
2. Verifica los logs del servidor

### Necesitas recuperar acceso

Si perdiste acceso al panel admin:

1. Edita `.env`:
   ```env
   ADMIN_BOOTSTRAP_USERNAME=admin
   ADMIN_BOOTSTRAP_PASSWORD=<password-temporal>
   ADMIN_BOOTSTRAP_RESET_EXISTING=true
   ```
2. Reinicia el servidor
3. Ingresa con el password temporal
4. El sistema te obligará a cambiar el password
5. Vuelve a poner `ADMIN_BOOTSTRAP_RESET_EXISTING=false`