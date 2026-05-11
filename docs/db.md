# DB: Memoria y Retención

Sofía guarda contexto mínimo para mejorar la continuidad de la conversación.

Datos guardados:
- `tenant_id` para separar historial, memoria, citas y eventos por tenant.
- Historial reciente de mensajes.
- Nombre de WhatsApp cifrado.
- Resumen breve del interés de la clienta.
- Servicio de interés cuando puede detectarse.
- Citas pendientes cuando la clienta envía comprobante/captura de cita después de recibir la liga para elegir horario.
- Citas completadas cuando, teniendo una cita pendiente, la clienta envía después el comprobante de pago/anticipo.

Políticas:
- Los mensajes y nombres se almacenan cifrados.
- La memoria se conserva por un máximo de 30 días de inactividad.
- Las citas pendientes se purgan con la misma retención de la app.
- Las citas completadas no se purgan automáticamente por tiempo; quedan como registro permanente.
- El comando administrativo `dipiridú`, tras confirmación explícita, borra memoria, historial, pendientes y completadas del chat actual.
- El comando administrativo `dipirdu -rf`/`dipiridú -rf`, tras responder exactamente `sí borrar toda la db`, borra todas las tablas de la app.
- Estos comandos solo pueden ejecutarse desde números configurados en `ADMIN_PHONE_NUMBER` o `ADMIN_PHONE_NUMBERS`.
- Si Sofía no puede leer memoria cifrada por cambio de llave, debe descartarla y continuar sin contexto previo.
- Las instalaciones existentes reciben `tenant_id='vanity'` mediante migración idempotente en `init_db`.

Tablas:
- `interacciones`: historial cifrado de conversación.
- `sesiones_memoria`: perfil/resumen por WhatsApp.
- `citas_pendientes`: una cita abierta por WhatsApp con comprobante de cita recibido.
- `citas_completadas`: registro permanente cuando ya se recibió comprobante de cita y comprobante de pago.
- `webhook_events`: deduplicación y locks operativos por evento.
- `service_catalog`: catálogo activo de Fresha. Es la fuente canónica para nombres de servicios, paquetes, promociones, extras, precios y duraciones.

## Catálogo de servicios

`service_catalog` se sincroniza desde el CSV de Fresha configurado en `FRESHA_SERVICE_CSV_PATH`.

No hay catálogo de servicios en Markdown. Sofía debe usar registros activos de esta tabla para responder promociones, combos y resúmenes de booking. Si un servicio no aparece en la tabla, debe pedir aclaración o pasar el caso a recepción.

Ver [service_catalog.md](service_catalog.md).
