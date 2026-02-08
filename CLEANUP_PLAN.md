# Plan de Limpieza de Repositorio

## 📊 Archivos en el Repositorio

### Esenciales (MANTENER)

| Archivo | Propósito | Líneas | Estado |
|---------|---------|-------|---------|
| README.md | Documentación principal del proyecto | 360 | ✅ Mantener |
| COOLIFY.md | Guía de deployment en Coolify | 140 | ✅ Mantener |
| system_prompt.md | Prompt del sistema para OpenAI (~500 líneas) | 500+ | ✅ Mantener |
| PRD.md | Especificaciones y requisitos | 150 | ✅ Mantener |
| PROGRESO.md | Seguimiento de desarrollo | 80 | ✅ Mantener |
| tech_specs.md | Especificaciones técnicas | 180 | ✅ Mantener |

### Temporales de Documentación (CONSIDERAR ELIMINAR)

| Archivo | Propósito | Razón para eliminar |
|---------|---------|----------|
| DEBUG_EVOLUTION.md | Guía de debugging Evolution API | 60 | Temporal - Ya resuelto el problema |
| EVOLUTION_API_ENDPOINTS.md | Opciones de endpoints para pruebas | 35 | Temporal - Solo para desarrollo local |
| ERROR_400_SOLVED.md | Documentación del error 400 resuelto | 95 | Temporal - Error ya identificado y solucionado |
| DEPLOYMENT_CHECKLIST.md | Checklist de deployment | 140 | Temporal - Solo para verificar antes de deploy |

**Total temporales a eliminar: 4 archivos**
**Total líneas a eliminar: ~330 líneas**

---

## 🎯 Recomendación

### Archivos Temporales
- **Eliminable después de confirmar producción funcionando:**
  - `DEBUG_EVOLUTION.md` - Ya resuelto el problema, puedes eliminar después
  - `EVOLUTION_API_ENDPOINTS.md` - Solo para pruebas locales, puedes eliminar
  - `ERROR_400_SOLVED.md` - Documentación de error ya resuelto, puedes eliminar
  - `DEPLOYMENT_CHECKLIST.md` - Solo checklist, puedes mantener o eliminar

### Archivos Esenciales (MANTENER SIEMPRE)

**1. README.md** - Documentación principal del proyecto
**2. system_prompt.md** - Prompt del sistema para OpenAI
**3. PRD.md** - Requisitos y especificaciones
**4. PROGRESO.md** - Seguimiento de desarrollo
**5. tech_specs.md** - Especificaciones técnicas
**6. COOLIFY.md** - Guía de deployment para producción

---

## 📋 Acción Solicitada

¿Deseas que elimine los archivos temporales de documentación?

**Archivos a eliminar:**
1. `DEBUG_EVOLUTION.md`
2. `EVOLUTION_API_ENDPOINTS.md`
3. `ERROR_400_SOLVED.md`
4. `DEPLOYMENT_CHECKLIST.md`

**Archivos a mantener:**
1. `README.md`
2. `system_prompt.md`
3. `PRD.md`
4. `PROGRESO.md`
5. `tech_specs.md`
6. `COOLIFY.md`

---

## 🔍 Análisis del Proyecto

### Estructura Final del Repositorio

```
bot_vanity/
├── src/                    (9 archivos TypeScript)
│   ├── controllers/
│   │   └── webhookController.ts
│   ├── services/
│   │   ├── ragService.ts
│   │   ├── openaiService.ts
│   │   ├── evolutionService.ts
│   │   ├── conversationMemory.ts
│   │   ├── upsellingService.ts
│   │   └── conversationService.ts
│   ├── utils/
│   │   └── sentimentAnalyzer.ts
│   ├── types/
│   │   └── index.ts
│   ├── vanity_data/
│   │   ├── services.jsonl
│   │   └── locations.jsonl
│   ├── system_prompt.md         (NECESARIO - 500+ líneas)
│   ├── COOLIFY.md               (NECESARIO - guía de deployment)
│   ├── PRD.md                   (NECESARIO - requisitos)
│   ├── PROGRESO.md               (NECESARIO - seguimiento)
├── conversation_guides/         (8 archivos)
│   ├── personality_rules/            (5 archivos)
├── .env.example              (NECESARIO)
├── .dockerignore              (NECESARIO)
├── Dockerfile                  (NECESARIO)
├── docker-compose.yml          (NECESARIO)
└── README.md                  (NECESARIO)
```

### Estadísticas
- **Total archivos TypeScript:** 9
- **Archivos .md:** 10 (6 esenciales + 4 temporales)
- **Líneas de código total:** ~1,200
- **Líneas de documentación:** ~2,000
- **Scripts y configuración:** 5 archivos

---

## 📊 Propuesta Final

**Mantener:**
- 6 archivos .md esenciales (README, system_prompt, PRD, PROGRESO, tech_specs, COOLIFY, +2 guías de conversación)

**Eliminar:**
- 4 archivos .md temporales (DEBUG_EVOLUTION, EVOLUTION_API_ENDPOINTS, ERROR_400_SOLVED, DEPLOYMENT_CHECKLIST)

**Resultado:**
- **De 10 archivos .md → 6 archivos .md** (reducción del 40%)
- **Mantener solo documentación esencial y funcional**

---

## 🚀 Próximos Pasos

### Paso 1: Revisión de Archivos Temporales
- Verificar si ya no son necesarios
- Confirmar que el error 400 está resuelto y documentado

### Paso 2: Eliminación (OPCIONAL)
```bash
rm DEBUG_EVOLUTION.md
rm EVOLUTION_API_ENDPOINTS.md
rm ERROR_400_SOLVED.md
rm DEPLOYMENT_CHECKLIST.md
```

### Paso 3: Verificación Final
- Listar archivos restantes
- Confirmar que solo queden los esenciales

### Paso 4: Commit
```bash
git add .
git commit -m "chore: remove temporary documentation files

- Remove temporary/debugging files (DEBUG_EVOLUTION.md, EVOLUTION_API_ENDPOINTS.md, ERROR_400_SOLVED.md, DEPLOYMENT_CHECKLIST.md)
- Keep only essential documentation: README, system_prompt, PRD, PROGRESO, tech_specs, COOLIFY
- Reduces markdown files from 10 to 6 (40% reduction)
- Clean repository structure"
```

---

## 📝 Notas

1. Los archivos temporales contienen información valiosa de debugging que ayudaron a resolver el problema del error 400
2. Puedes mantenerlos si necesitas referenciar las soluciones
3. Considera mover algunos a una carpeta `docs/archived/` antes de eliminar

---

**¿Deseas que proceda con la limpieza?** 🤔
