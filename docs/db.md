# DB: Memoria y Retención

Sofía guarda contexto mínimo para mejorar la continuidad de la conversación.

Datos guardados:
- Historial reciente de mensajes.
- Nombre de WhatsApp cifrado.
- Resumen breve del interés de la clienta.
- Servicio de interés cuando puede detectarse.
- Citas pendientes cuando la clienta envía comprobante/captura de cita después de recibir la liga de agendamiento.
- Citas completadas cuando, teniendo una cita pendiente, la clienta envía después el comprobante de pago/anticipo.

Políticas:
- Los mensajes y nombres se almacenan cifrados.
- La memoria se conserva por un máximo de 30 días de inactividad.
- Las citas pendientes se purgan con la misma retención de la app.
- Las citas completadas no se purgan automáticamente por tiempo; quedan como registro permanente.
- El comando administrativo `dipiridú`, tras confirmación explícita, borra memoria, historial, pendientes y completadas de forma global.
- `dipiridú` solo puede ejecutarse desde el número configurado en `ADMIN_PHONE_NUMBER`.
- Si Sofía no puede leer memoria cifrada por cambio de llave, debe descartarla y continuar sin contexto previo.

Tablas:
- `interacciones`: historial cifrado de conversación.
- `sesiones_memoria`: perfil/resumen por WhatsApp.
- `citas_pendientes`: una cita abierta por WhatsApp con comprobante de cita recibido.
- `citas_completadas`: registro permanente cuando ya se recibió comprobante de cita y comprobante de pago.
