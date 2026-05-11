# Service Catalog

`service_catalog` es la fuente canónica de servicios, paquetes, extras, promociones, precios y duraciones que Sofía puede mencionar.

## Fuente de datos

La tabla se alimenta desde el export CSV de Fresha configurado con:

```env
FRESHA_SERVICE_CSV_PATH=export_service_list_2026-05-11.csv
```

El archivo CSV es operativo/local y no se versiona. `.gitignore` ignora `export_service_list_*.csv`.

## Regla principal

Sofía no debe inventar servicios ni paquetes. Si el nombre no existe como registro activo en `service_catalog`, no debe enviarlo como opción de booking.

Los documentos Markdown no son fuente de servicios ni promociones. `docs/knowledge_base.md`, `docs/promos.md` y `app/pricing.py` fueron eliminados para evitar catálogos paralelos.

## Sincronización

La sincronización ocurre:

- al arrancar `vanessa-app`, si existe el CSV configurado
- desde `/admin/ops` con la acción `Sincronizar Fresha CSV`

La sincronización hace upsert por `external_service_id` cuando existe, y por `slug`/nombre cuando no.

## Columnas usadas

- `Nombre del servicio` -> `name`
- `Precio de compra` -> `base_price`
- `Duración` -> `duration_minutes`
- `Tiempo adicional` -> `additional_time_minutes`
- `Impuestos` -> `tax_percent`
- `Descripción` -> `description`
- `Nombre de la categoría` -> `category`
- `Tipo de servicio` -> ayuda a inferir `service_type`
- `ID del servicio` -> `external_service_id`

## Promociones y combos

Cuando la clienta pide promociones, paquetes, combos o manos y pies, Sofía consulta opciones activas de `service_catalog`.

Ejemplos válidos si existen en Fresha:

- `GELISH GLOW (gelish manos y pies)`
- `SHINE DELUXE (manicure + pedicure deluxe)`
- `SPA GLAMOUR (gelish manos + pedicure spa)`
- `RUBBER SHINE (base rubber + gel manos)`

Sofía no debe responder con etiquetas genéricas como `Combo manos y pies` en el resumen de reserva, porque no es un servicio real de Fresha.

## Flujo de booking

Para reservar, Sofía debe armar el resumen con nombres reales de catálogo:

```text
Retiro de Gel/Acrílico - GELISH GLOW (gelish manos y pies)
```

Luego, al enviar la liga de booking, debe listar duración real tomada de la tabla:

```text
- Retiro de Gel/Acrílico: 20 min
- GELISH GLOW (gelish manos y pies): 95 min
```

Si hay varias promociones posibles, Sofía primero pregunta cuál paquete quiere reservar antes de mandar la liga.

## Operación

Después de actualizar el CSV en el servidor:

1. Coloca el archivo en la ruta configurada por `FRESHA_SERVICE_CSV_PATH`.
2. Ejecuta `Sincronizar Fresha CSV` desde `/admin/ops` o reinicia `vanessa-app`.
3. Revisa `/admin/db/service_catalog` para confirmar nombres, precios, duración y estado activo.
4. Prueba por WhatsApp: `tienen promociones?` o `quiero combos`.

## Diagnóstico

Si Sofía menciona un servicio incorrecto:

- confirma que el nombre exista y esté activo en `service_catalog`
- revisa que el CSV más reciente haya sido sincronizado
- revisa que producción esté corriendo una imagen posterior al commit que eliminó catálogo Markdown
- revisa logs del flujo `catalog_guided_booking` o `local_booking_flow`
