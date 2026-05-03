# WEBUI Plan de Tareas

## Objetivo
Construir un panel web interno de control para operar el sistema de Sofía y los servicios conectados desde una sola interfaz. El panel debe servir para administrar catálogo, revisar datos, importar/exportar información, operar acciones de soporte y dar visibilidad cruda tipo CRM/DB sin depender de acceso manual a la base de datos o a herramientas externas.

## Prioridad Cero: seguridad de acceso
Como el panel tendrá una URL propia, la primera decisión no debe ser la UI sino el perímetro de seguridad. Antes de habilitar cualquier función administrativa, el acceso debe quedar protegido para reducir riesgo de exposición, robo de sesión, filtración de datos o ejecución de acciones destructivas.

### Requisitos mínimos obligatorios
- URL administrativa separada, por ejemplo `/admin` o idealmente un subdominio interno tipo `admin.midominio.com`.
- Acceso solo por `HTTPS`.
- Password inicial fuerte generado aleatoriamente, no definido manualmente con algo predecible.
- Password guardado solo como hash seguro, nunca en texto plano.
- Sesión autenticada con cookie segura `HttpOnly`.
- Rate limit y bloqueo temporal en login.
- Registro de auditoría desde el primer release.
- Posibilidad de restringir acceso por IP, VPN o reverse proxy autenticado.

### Política de password recomendada
- Longitud mínima real: 20 caracteres si es autogenerado.
- Si se permite definirlo manualmente: mínimo 16 caracteres con passphrase fuerte.
- No reutilizar credenciales de otros sistemas.
- Rotación obligatoria del password temporal en primer login.
- Expiración configurable para usuarios temporales.
- Reautenticación para acciones críticas como resets globales o borrados masivos.

### Almacenamiento seguro de credenciales
- Usar hash con `argon2id` como primera opción.
- Alternativa aceptable si ya existe compatibilidad en stack: `bcrypt` con costo adecuado.
- Nunca guardar passwords reversibles.
- Nunca loggear passwords, hashes completos ni secretos.
- Si se genera password temporal, mostrarlo una sola vez al crear el usuario.
- Guardar secretos de aplicación solo en variables de entorno o secret manager.

### Protección del URL admin
- No asumir que “tener una ruta rara” protege nada.
- Evitar exponer el panel directamente a internet si no es necesario.
- Preferir una de estas capas:
  - VPN
  - allowlist de IP
  - basic auth en reverse proxy además del login interno
  - túnel privado o access proxy tipo Cloudflare Access/Tailscale/nginx con auth externa
- Si va a estar público, activar cabeceras de seguridad y endurecer cookies desde el día uno.

## Alcance funcional

### 1. Acceso administrativo temporal
- Login simple con `user + password` temporal.
- Sesiones de corta duración con expiración automática.
- Posibilidad de rotar credenciales rápido desde variables de entorno o tabla administrativa.
- Opción de deshabilitar el panel completo con un flag de entorno.
- Registro de auditoría básico: quién entró, cuándo, desde qué IP y qué acción ejecutó.
- Password temporal forzado a cambio en primer acceso.
- Hash de password con `argon2id`.
- Reautenticación para acciones críticas.

### 2. Dashboard principal
- Estado general de la app FastAPI.
- Estado de conexión a PostgreSQL.
- Estado de Evolution API.
- Métricas rápidas:
  - conversaciones activas
  - citas pendientes
  - citas completadas
  - follow-ups pendientes
  - errores recientes
  - última ejecución del janitor
- Tarjetas con acciones rápidas:
  - reiniciar app
  - reiniciar integración Evolution
  - limpiar cachés en memoria
  - pausar bot
  - reactivar bot

### 3. Módulo de servicios
- Ver lista de servicios disponibles.
- Agregar servicio nuevo.
- Editar nombre, precio, duración, categoría y descripción.
- Eliminar servicio con confirmación.
- Activar o desactivar servicios sin borrarlos.
- Administrar extras:
  - retiro
  - nail art
  - promociones
  - etiquetas operativas
- Guardar historial de cambios del catálogo.

### 4. Importación y exportación
- Importar servicios desde `CSV` o `JSON`.
- Exportar catálogo actual a `CSV` o `JSON`.
- Validaciones antes de importar:
  - columnas requeridas
  - tipos numéricos
  - duplicados
  - nombres vacíos
  - precios inválidos
- Modo `preview` antes de confirmar importación.
- Política de merge:
  - crear nuevos
  - actualizar existentes por `slug` o nombre normalizado
  - rechazar conflictos ambiguos
- Registro del resultado de la importación:
  - creados
  - actualizados
  - ignorados
  - fallidos

### 5. Vista CRM cruda
- Bandeja de conversaciones con búsqueda por número, nombre o texto.
- Vista por contacto con:
  - nombre/alias
  - número
  - último mensaje
  - estado conversacional
  - memoria/resumen
  - citas pendientes
  - citas completadas
  - timestamps relevantes
- Filtros:
  - activas
  - con follow-up
  - con handover humano
  - con incidencia
  - con comprobante recibido
- Timeline legible del chat cifrado ya descifrado solo para admin autenticado.
- Acciones operativas:
  - marcar handover humano
  - cerrar incidencia
  - resetear estado conversacional
  - borrar memoria de una clienta
  - reenviar follow-up

### 6. Explorador de base de datos
- Vista tabular de las tablas clave:
  - `interacciones`
  - `sesiones_memoria`
  - `citas_pendientes`
  - `citas_completadas`
- Filtros, ordenamiento y paginación.
- Ver detalle por fila.
- Exportación del resultado filtrado.
- Acciones limitadas y seguras:
  - borrar una fila puntual
  - editar campos permitidos
  - reintentar descifrado si falla lectura
- Nunca exponer SQL libre en la primera versión.

### 7. Controles operativos
- Toggle para pausar respuestas automáticas.
- Toggle para desactivar follow-ups.
- Botón para vaciar deduplicación en memoria.
- Botón para limpiar rate limits en memoria.
- Botón para disparar manualmente el janitor.
- Botón para refrescar documentos RAG desde `/docs`.
- Botón para probar conectividad con Evolution.
- Botón para probar conectividad con OpenAI sin exponer secretos.

### 8. Resets y soporte de sistemas
- Reset suave del estado de la app:
  - caché
  - colas en memoria
  - banderas temporales
- Reset de estados conversacionales seleccionados.
- Reset de integración Evolution:
  - revalidar instancia
  - reintentar handshake
  - limpiar estado temporal de webhook si aplica
- Reset global protegido por doble confirmación para:
  - memoria
  - historial
  - citas pendientes
  - citas completadas
- El reset global debe quedar restringido al administrador principal, aunque exista login temporal.

### 9. Configuración interna
- Pantalla para revisar configuración efectiva no sensible:
  - URLs internas
  - flags activos
  - retención
  - delays
  - estado del bot
- Secrets nunca visibles completos.
- Mostrar secretos solo en forma parcial o enmascarada.
- Acciones de cambio sensibles solo vía confirmación adicional.

## Arquitectura propuesta

### Opción recomendada
- Backend admin integrado al proyecto FastAPI existente.
- Frontend server-rendered con Jinja2 + HTMX para velocidad de entrega.
- CSS simple tipo panel interno; no hace falta framework pesado en v1.
- Autenticación por sesión firmada en cookie `HttpOnly`.

### Razón
- Reusa el backend actual.
- Reduce complejidad de despliegue.
- Permite construir una UI operativa rápido.
- Evita montar un SPA completo para una herramienta administrativa de uso interno.

### Alternativa si crece
- Separar en:
  - `app/main.py` para API pública/webhook
  - `app/admin.py` o router admin dedicado
  - frontend React/Vue solo si el panel se vuelve más complejo

## Modelo de datos sugerido

### Tabla nueva `admin_users`
- `id`
- `username`
- `password_hash`
- `password_algo`
- `is_active`
- `is_superadmin`
- `temporary_password`
- `must_rotate_password`
- `failed_login_attempts`
- `locked_until`
- `password_expires_at`
- `created_at`
- `updated_at`
- `last_login_at`

### Tabla nueva `admin_audit_log`
- `id`
- `admin_user_id`
- `action`
- `entity_type`
- `entity_id`
- `payload_json`
- `ip_address`
- `created_at`

### Tabla nueva `service_catalog`
- `id`
- `slug`
- `name`
- `category`
- `description`
- `base_price`
- `duration_minutes`
- `is_active`
- `source`
- `created_at`
- `updated_at`

### Tabla nueva `service_extras`
- `id`
- `service_id`
- `extra_type`
- `name`
- `price_delta`
- `duration_delta`
- `is_active`

### Tabla opcional `system_flags`
- `key`
- `value_json`
- `updated_at`
- `updated_by`

## Endpoints sugeridos

### Auth
- `GET /admin/login`
- `POST /admin/login`
- `POST /admin/logout`

### Dashboard
- `GET /admin`
- `GET /admin/health`
- `GET /admin/metrics`

### Servicios
- `GET /admin/services`
- `GET /admin/services/new`
- `POST /admin/services`
- `GET /admin/services/{id}/edit`
- `POST /admin/services/{id}`
- `POST /admin/services/{id}/delete`
- `POST /admin/services/import`
- `GET /admin/services/export.csv`
- `GET /admin/services/export.json`

### CRM y DB
- `GET /admin/crm`
- `GET /admin/crm/{phone}`
- `POST /admin/crm/{phone}/reset-state`
- `POST /admin/crm/{phone}/clear-memory`
- `GET /admin/db/{table_name}`
- `GET /admin/db/{table_name}/{row_id}`

### Operación
- `POST /admin/actions/pause-bot`
- `POST /admin/actions/resume-bot`
- `POST /admin/actions/reset-runtime`
- `POST /admin/actions/reset-evolution`
- `POST /admin/actions/run-janitor`
- `POST /admin/actions/reload-docs`

## Tareas por fases

## Fase 1. Base administrativa
- [ ] Definir estrategia de exposición del panel: VPN, IP allowlist, proxy protegido o público endurecido.
- [ ] Crear router `/admin`.
- [ ] Crear layout base del panel.
- [ ] Implementar login/logout por sesión.
- [ ] Agregar middleware para proteger rutas admin.
- [ ] Agregar tabla `admin_users`.
- [ ] Crear comando o seed para credencial temporal inicial autogenerada.
- [ ] Hash de password con `argon2id`.
- [ ] Agregar expiración y rotación de password temporal.
- [ ] Forzar cambio de password en primer login.
- [ ] Agregar política de password fuerte.
- [ ] Agregar bloqueo por intentos fallidos.
- [ ] Configurar cookies seguras y expiración de sesión.

## Fase 2. Dashboard y observabilidad
- [ ] Construir home del panel con tarjetas de estado.
- [ ] Exponer métricas internas mínimas.
- [ ] Integrar chequeos de DB, app y Evolution.
- [ ] Agregar tablero de eventos recientes y errores.

## Fase 3. CRUD de servicios
- [ ] Diseñar esquema `service_catalog` y `service_extras`.
- [ ] Crear listado de servicios.
- [ ] Crear alta/edición/baja lógica.
- [ ] Implementar validaciones de negocio.
- [ ] Registrar auditoría por cambio.

## Fase 4. Import/export
- [ ] Definir formato oficial `CSV` y `JSON`.
- [ ] Implementar parser y validador.
- [ ] Crear flujo preview antes de confirmar.
- [ ] Implementar exportación filtrada.
- [ ] Agregar reporte de resultados de importación.

## Fase 5. CRM crudo
- [ ] Construir listado de conversaciones.
- [ ] Construir detalle por contacto.
- [ ] Conectar con `interacciones`, `sesiones_memoria`, `citas_pendientes` y `citas_completadas`.
- [ ] Agregar filtros operativos.
- [ ] Implementar acciones por contacto.

## Fase 6. Explorador DB
- [ ] Crear vistas seguras por tabla.
- [ ] Agregar paginación y filtros.
- [ ] Implementar exportación.
- [ ] Restringir edición solo a campos aprobados.

## Fase 7. Operación y resets
- [ ] Exponer toggles de runtime.
- [ ] Implementar acciones de limpieza en memoria.
- [ ] Implementar disparadores manuales de janitor y reload docs.
- [ ] Diseñar resets protegidos con confirmación doble.
- [ ] Separar permisos de operador vs superadmin.

## Fase 8. Seguridad y endurecimiento
- [ ] CSRF en formularios admin.
- [ ] Cookies `HttpOnly`, `Secure`, `SameSite`.
- [ ] Rate limit sobre login.
- [ ] Bloqueo temporal tras intentos fallidos.
- [ ] Auditoría de acciones sensibles.
- [ ] Enmascarado de secretos.
- [ ] Confirmación reforzada para borrados y resets globales.

## Fase 9. QA
- [ ] Tests de auth admin.
- [ ] Tests de CRUD de servicios.
- [ ] Tests de importación CSV/JSON.
- [ ] Tests de permisos por rol.
- [ ] Tests de acciones de reset.
- [ ] Tests de render de CRM con datos reales anonimizados.

## UI recomendada

### Menú lateral
- Dashboard
- Servicios
- Importar/Exportar
- CRM
- Base de datos
- Operación
- Configuración
- Auditoría

### Principios UX
- Priorizar velocidad y claridad, no diseño marketing.
- Todo cambio destructivo requiere confirmación.
- Todo cambio importante deja rastro.
- Las pantallas de tablas deben soportar búsqueda rápida.
- Los botones de reset deben estar visualmente separados del resto.

## Reglas de seguridad
- El panel no debe ser público.
- Idealmente exponerlo solo por VPN, IP allowlist o reverse proxy protegido.
- Si por operación debe ser público, usar `HTTPS`, cookies seguras, rate limit y segunda capa delante del login.
- Las contraseñas temporales deben tener expiración real.
- Las contraseñas deben guardarse con hash `argon2id` o `bcrypt`, nunca en texto plano.
- No guardar secretos en HTML ni en JavaScript.
- No mostrar contenido descifrado si no hay sesión admin válida.
- Cualquier acción global destructiva debe pedir reautenticación.

## Riesgos
- Mezclar demasiado poder operativo en una sola UI sin permisos por rol.
- Exponer datos sensibles del CRM sin controles de sesión sólidos.
- Permitir ediciones directas de DB demasiado temprano.
- Implementar reset global sin barreras suficientes.
- Crear dos fuentes de verdad entre `/docs` y `service_catalog`.

## Decisiones que conviene tomar antes de construir
- Definir si el catálogo maestro seguirá viviendo en Markdown, DB o ambos.
- Definir si el panel editará también promociones.
- Definir si el reset de Evolution será solo lógico o también por contenedor/proceso.
- Definir si habrá uno o varios admins temporales.
- Definir si el CRM solo será lectura con acciones puntuales o también edición de datos.

## Recomendación pragmática de v1
- Hacer primero:
  - estrategia de exposición segura del URL admin
  - login temporal
  - password fuerte autogenerado
  - hash seguro de credenciales
  - dashboard
  - CRUD de servicios
  - import/export
  - CRM de solo lectura con acciones básicas
  - controles operativos no destructivos
- Dejar para v2:
  - editor más libre de DB
  - resets globales profundos
  - permisos finos por rol
  - UI más compleja o SPA

## Entregable esperado de la v1
Un panel interno en `/admin` que permita entrar con credencial temporal, ver estado del sistema, administrar el catálogo de servicios, importar/exportar `CSV/JSON`, inspeccionar conversaciones y datos clave, y ejecutar acciones operativas seguras para mantener funcionando tanto la app como la integración externa.
