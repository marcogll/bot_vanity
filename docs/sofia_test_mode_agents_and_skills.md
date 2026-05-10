# Agentes, Skills y Modo Test para el Refactor de Sofia

## Objetivo

Definir como desarrollar el refactor `Sofia Role Runtime` en modo test, con responsabilidades claras por agente, habilidades necesarias y controles para evitar impacto en produccion.

## Rama de Trabajo

Rama local:

```txt
test-sofia-role-runtime-refactor
```

Esta rama debe usarse para documentacion, prototipos, tests y cambios incrementales del runtime V2.

## Agentes Conceptuales del Sistema

Estos agentes son roles internos del producto, no procesos separados obligatorios. La primera implementacion puede vivir en un solo servicio FastAPI, pero con interfaces limpias para que despues se puedan separar.

### 1. `frontdesk_sofia`

Responsabilidad:

- atender al cliente en WhatsApp
- pedir el siguiente dato util
- cotizar con base documental
- enviar booking cuando corresponde
- mantener tono breve y humano

Entradas:

- mensaje actual
- historial reciente
- estado conversacional
- perfil del cliente
- plan de respuesta

Salidas:

- respuesta al cliente
- accion sugerida
- actualizacion de memoria

Limites:

- no confirma disponibilidad sin herramienta
- no mueve citas manualmente
- no contradice recepcion humana
- no inventa precios

### 2. `staff_1`

Responsabilidad:

- experiencia de recepcion desde el dia 1
- guía eficiente para convertir conversaciones en citas
- llenado de agenda con baja friccion
- eleccion de la siguiente pregunta util
- continuidad natural del flujo de cita

Uso dentro del runtime:

- influye cuando el objetivo es convertir la conversacion en una cita bien agendada y evitar vueltas innecesarias.

No debe:

- redactar como si fuera una persona humana tomando el chat manualmente.
- inventar disponibilidad.
- prometer acomodos manuales sin herramienta real.

### 3. `staff_2_manager`

Responsabilidad:

- resolver operacion diaria
- priorizar urgencias
- detectar incidencias
- decidir siguiente paso operativo
- activar handover cuando corresponde

Uso dentro del runtime:

- influye mas en incidencias, citas, comprobantes, retrasos, reacomodos y casos con friccion.

No debe:

- prometer excepciones fuera de politica.

### 4. `conversation_classifier`

Responsabilidad:

- clasificar intencion
- detectar estado conversacional
- detectar urgencia
- detectar intervencion humana reciente
- detectar riesgo de respuesta tardia o duplicada

Salida esperada:

```json
{
  "state": "collecting_service",
  "intent": "booking_interest",
  "urgency": "normal",
  "human_recently_intervened": false,
  "missing_fields": ["subservice"],
  "risk_flags": []
}
```

### 5. `policy_engine`

Responsabilidad:

- decidir si el bot responde, calla, escala o usa una respuesta estructurada.

Decisiones:

```txt
RESPOND
SILENCE
ESCALATE_HUMAN
SEND_STRUCTURED_REPLY
ASK_LLM
```

### 6. `response_planner`

Responsabilidad:

- convertir la clasificacion y politicas en un plan concreto de respuesta.

Ejemplo:

```json
{
  "action": "ask_missing_detail",
  "field": "retiro",
  "role_blend": {
    "frontdesk": 0.7,
    "manager": 0.2,
    "staff1": 0.1
  },
  "constraints": ["one_question", "short_reply", "no_booking_link"]
}
```

### 7. `tool_executor`

Responsabilidad:

- ejecutar acciones reales del sistema.

Herramientas iniciales:

- pausar bot
- enviar mensaje
- programar follow-up
- registrar handover
- validar comprobante
- registrar cita pendiente/completada

## Skills Necesarios para Desarrollo

### Skill 1: Arquitectura de bots conversacionales

Uso:

- disenar estados, intents, politicas y limites de autoridad.

Resultado esperado:

- runtime modular, no prompt monolitico.

### Skill 2: FastAPI asincrono

Uso:

- mantener webhook actual.
- extraer capas sin romper endpoints.
- conservar compatibilidad con Evolution API.

Resultado esperado:

- `app/main.py` queda como orquestador.

### Skill 3: SQLAlchemy async y migracion de datos

Uso:

- introducir `tenant_id`.
- aislar memoria por negocio.
- mantener compatibilidad con datos existentes.

Resultado esperado:

- modelo multi-tenant sin perdida de historial.

### Skill 4: Prompt engineering operacional

Uso:

- pasar de system prompt gigante a prompt modular.
- construir prompts por estado, rol y politica.

Resultado esperado:

- menor riesgo de contradicciones y alucinaciones.

### Skill 5: Testing conversacional

Uso:

- convertir chats reales en escenarios de prueba.
- cubrir autoridad, silencio, escalamiento, booking y cotizacion.

Resultado esperado:

- suite de regresion contra errores reales de Sofia.

### Skill 6: Seguridad de bots

Uso:

- conservar proteccion contra prompt injection.
- mantener sanitizacion de historial y media.
- separar instrucciones internas de contenido de usuario.

Resultado esperado:

- el runtime V2 no baja el nivel de seguridad actual.

### Skill 7: Multi-tenant SaaS ligero

Uso:

- permitir que el mismo bot atienda otros negocios.
- cargar configuracion por tenant.
- separar conocimiento y memoria.

Resultado esperado:

- replicabilidad sin fork del codigo.

## Modo Test

### Flags recomendados

```env
BOT_RUNTIME_V2_ENABLED=false
BOT_RUNTIME_V2_SHADOW_MODE=true
ROLE_BLEND_ENABLED=false
TENANT_CONFIG_PATH=tenants
DEFAULT_TENANT_ID=vanity
```

### Comportamiento por etapa

#### Etapa 1: Documentacion y modelos

- No cambia comportamiento productivo.
- Se agregan modelos, contratos y tests unitarios.

#### Etapa 2: Shadow mode

- V1 sigue respondiendo al cliente.
- V2 clasifica, decide y genera plan, pero no envia respuesta.
- Se loguea comparacion V1 vs V2.

#### Etapa 3: Allowlist

- V2 solo responde a numeros definidos en `TEST_MODE_ALLOWED_NUMBERS`.
- El resto sigue con V1 o queda ignorado segun configuracion actual.

#### Etapa 4: Cutover gradual

- V2 se activa por tenant.
- Vanity puede permanecer en V1 mientras otro tenant de prueba usa V2.

## Guardrails de Desarrollo

- No tocar produccion sin flag.
- No cambiar copy visible sin test conversacional.
- No eliminar reglas actuales hasta tener cobertura equivalente.
- No meter multi-negocio dentro de prompts; debe existir en configuracion y modelos.
- No dar autoridad operativa a un rol si no hay herramienta real para ejecutarla.
- No permitir que el LLM decida silencio, handover o acciones criticas sin validacion del `PolicyEngine`.

## Primer Corte Tecnico Recomendado

1. Crear modelos puros para tenant, roles, decisiones y planes.
2. Crear `RoleBlender` con tests.
3. Crear `PolicyEngine` minimo con reglas actuales de silencio/handover.
4. Crear tenant `vanity` en configuracion versionada.
5. Agregar shadow mode sin cambiar respuesta enviada.
6. Mover gradualmente funciones desde `app/main.py` a modulos nuevos.

## Criterio para Empezar Implementacion

El primer PR de codigo debe ser pequeno:

- agrega modelos internos
- agrega configuracion base de tenant `vanity`
- agrega `RoleBlender`
- agrega tests unitarios
- no cambia comportamiento productivo

Ese primer corte permite avanzar con bajo riesgo y valida la direccion del refactor.
