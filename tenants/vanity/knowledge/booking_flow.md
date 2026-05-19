# Flujo de Booking

## Secuencia de Booking

1. Saludo inicial y solicitud de nombre
2. Detección de servicio (uñas, pestañas, cejas)
3. Para uñas: preguntar por sub-servicio (gelish, manicure, pedicure, etc.)
4. Preguntar por retiro de producto (gel, acrílico, polygel)
5. Preguntar por diseño (tono liso, francés, nail art)
6. Preguntar si tiene app de Fresha
   - Si NO: enviar links de App Store/Play Store y esperar confirmación
   - Si SÍ: enviar liga de booking con resumen
7. Programar follow-up si no hay comprobante
8. Validar comprobante de cita cuando llegue
9. Validar comprobante de pago cuando llegue

## Reglas del Flujo

- NO enviar liga de booking antes de completar los pasos 1-5
- NO consultar disponibilidad en Fresha
- NO confirmar citas manualmente
- Guiar a Fresha para elegir horario real
- Follow-up solo si no hubo respuesta del usuario

## Estados del Flujo

- `new`: Conversación nueva, pedir nombre
- `collecting_service`: Recopilando servicio
- `booking_link_sent`: Liga enviada, esperando comprobante
- `awaiting_deposit`: Esperando comprobante de pago
- `confirmed`: Booking completado
