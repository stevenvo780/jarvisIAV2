# 🔥 SUITES DE PRUEBAS EXTREMAS - JARVIS IA V2

## ⚠️ ADVERTENCIA IMPORTANTE

Estas suites están diseñadas para **DESTRUIR** el sistema y encontrar cualquier punto débil.
**NO ejecutar en producción - Solo en entornos de pruebas controlados.**

---

## 📊 RESUMEN DE SUITES

### 1. **extreme_stress_test.py** (18KB)
**Descripción**: Bombardeo masivo desde todos los ángulos

**8 FASES DE DESTRUCCIÓN**:
- **FASE 1: Concurrent Bomb** 💣
  - 50 threads x 10 requests = **500 requests simultáneos**
  - Timeout de solo 5 segundos
  - Sin pausas entre requests
  - Rate: ~100 req/s

- **FASE 2: Payload Hell** 👹
  - Payload gigante de 10MB
  - Caracteres especiales masivos
  - Emoji bomb (30,000 emojis)
  - XSS bomb (5000 script tags)
  - SQL injection masivo
  - Null bytes, Unicode exótico

- **FASE 3: Memory Exhaustion** 💾
  - 100 requests grandes simultáneos
  - 20 workers en paralelo
  - Payloads de 4000 chars cada uno
  - Monitoreo de memoria en tiempo real

- **FASE 4: Request Bombing** 💥
  - 60 segundos de bombardeo continuo
  - 10 threads bombardeando sin parar
  - Requests cada 0.1 segundos
  - Monitoreo de CPU/Memory cada 5s

- **FASE 5: Race Conditions** 🏁
  - 20 threads haciendo operaciones conflictivas
  - GET/POST/DELETE simultáneos en history
  - 20 iteraciones por thread
  - Intentar corromper estado interno

- **FASE 6: Endpoint Abuse** 🔨
  - 5 endpoints x 100 requests x 10 rondas
  - 30 workers por endpoint
  - Total: **5,000 requests**

- **FASE 7: Malformed Requests** 🤪
  - 6 tipos de payloads inválidos
  - 50 requests por tipo
  - 20 workers en paralelo
  - JSON inválido, headers raros, etc.

- **FASE 8: Resource Exhaustion** 🧨
  - 200 threads con conexiones activas
  - Timeout largo (300s) para mantener conexiones
  - Intentar agotar file descriptors
  - Monitoreo de recursos del sistema

**Estadísticas recolectadas**:
- Total requests
- Successful/Failed
- Errors por tipo
- CPU/Memory usage
- Tasa de requests/segundo

---

### 2. **gpu_destruction_test.py** (14KB)
**Descripción**: Estrés específico de GPU para saturar VRAM

**5 TESTS BRUTALES**:
- **TEST 1: GPU Saturation**
  - 10 prompts extremadamente largos en paralelo
  - Prompts de 500-1000 palabras
  - Timeout de 10 minutos por request
  - Monitoreo de tiempos de respuesta

- **TEST 2: Sequential Pressure**
  - 50 prompts pesados consecutivos sin descanso
  - Detección de degradación de rendimiento
  - Si tiempo > 1.5x promedio → alerta
  - Detiene si encuentra OOM error

- **TEST 3: Burst Wave**
  - 5 olas de 20 requests cada una
  - Pausa de 10s entre olas
  - Medir recuperación del sistema

- **TEST 4: Memory Leak Hunt**
  - 100 iteraciones del mismo request
  - Detectar si los tiempos aumentan
  - Si tiempo duplica → posible leak

- **TEST 5: Maximum Context**
  - Prompts que fuerzan búsqueda RAG máxima
  - "Busca en todo tu conocimiento..."
  - "Analiza todos los datos históricos..."

**Prompts diseñados para consumir VRAM**:
- Historias épicas de 5000 palabras
- Análisis completo de teoría de relatividad
- Tutorial de SO desde cero
- Análisis de todas las obras de Shakespeare

---

### 3. **chaos_engineering_test.py** (18KB)
**Descripción**: Chaos Monkey - Intentar romper ACTIVAMENTE

**7 ATAQUES CAÓTICOS**:
- **CHAOS 1: Random Fuzzing**
  - 200 payloads completamente aleatorios
  - Binary garbage, Unicode hell, Control chars
  - JSON malformado, Null bytes
  - Buscar 5xx errors o crashes

- **CHAOS 2: Timing Attacks**
  - 10 threads por endpoint
  - 50 rapid-fire por thread
  - Timeout de 0.1s (intencional)
  - Buscar race conditions

- **CHAOS 3: State Corruption**
  - Crear historial grande (100 items)
  - 20 threads haciendo GET/DELETE/POST simultáneos
  - Verificar consistencia después
  - Detectar si history deja de ser lista

- **CHAOS 4: Resource Starvation**
  - 500 conexiones colgadas
  - Mientras tanto, bombardear con más requests
  - Intentar agotar file descriptors
  - Verificar si sigue vivo después

- **CHAOS 5: Malicious Payloads**
  - Path traversal: `../../../etc/passwd`
  - Command injection: `; rm -rf /`
  - SQL injection: `1' OR '1'='1`
  - XXE, SSRF, CRLF injection
  - Buffer overflow attempts
  - Verificar si tienen efecto

- **CHAOS 6: Crash Recovery**
  - Intentar crashear con payloads específicos
  - Stack overflow, regex DoS
  - Esperar 10s recovery time
  - Verificar si se recupera (5 intentos)

- **CHAOS 7: Chaos Monkey**
  - 120 segundos de caos aleatorio
  - 20 monkeys haciendo cosas random
  - Acciones cada 0-0.5 segundos
  - Verificar supervivencia final

**Reporte final**:
- Total chaos attacks
- Successful attacks (causaron issues)
- Failed attacks (server handled)
- Crashes detected
- Lista de anomalías

---

## 🚀 EJECUCIÓN

### Quick Start

```bash
# Test 1: Extreme Stress (más general)
python3 tests/extreme_stress_test.py

# Test 2: GPU Destruction (específico GPU)
python3 tests/gpu_destruction_test.py

# Test 3: Chaos Engineering (más agresivo)
python3 tests/chaos_engineering_test.py
```

### Ejecutar en background

```bash
# Extreme stress
python3 tests/extreme_stress_test.py > extreme_results.log 2>&1 &

# GPU destruction
python3 tests/gpu_destruction_test.py > gpu_results.log 2>&1 &

# Chaos engineering
python3 tests/chaos_engineering_test.py > chaos_results.log 2>&1 &
```

### Monitorear progreso

```bash
# Ver output en tiempo real
tail -f extreme_results.log

# Ver solo errores
grep ERROR extreme_results.log

# Ver estadísticas finales
grep "FINAL" extreme_results.log -A 20
```

---

## 📈 INTERPRETANDO RESULTADOS

### ✅ Señales de Sistema Saludable
- Pocos o ningún crash
- Errores manejados correctamente (422, 400)
- No OOM errors
- Timeouts esperados (modelo lento)
- Memoria estable
- CPU se recupera

### ⚠️ Señales de Advertencia
- Crashes ocasionales
- Memory leaks (memoria aumenta constantemente)
- Degradación de rendimiento progresiva
- Estado inconsistente
- Errores 5xx frecuentes

### 🚨 Problemas Críticos
- Crashes frecuentes
- Server no se recupera
- OOM errors continuos
- Payloads maliciosos tienen efecto
- Race conditions causan corrupción
- Sistema completamente inestable

---

## 🎯 QUÉ BUSCAR

### En extreme_stress_test.py
- ¿Maneja 500 requests concurrent?
- ¿Valida payloads gigantes?
- ¿Se recupera del bombardeo?
- ¿Hay memory leaks?

### En gpu_destruction_test.py
- ¿Maneja requests pesados?
- ¿VRAM se libera correctamente?
- ¿Detecta OOM y se recupera?
- ¿Los tiempos aumentan progresivamente?

### En chaos_engineering_test.py
- ¿Bloquea payloads maliciosos?
- ¿Se recupera de crashes?
- ¿Maneja fuzzing random?
- ¿Estado permanece consistente?

---

## 💾 REQUISITOS

```bash
pip install requests psutil
```

---

## ⏱️ DURACIÓN ESTIMADA

- **extreme_stress_test.py**: 20-40 minutos
- **gpu_destruction_test.py**: 60-120 minutos (depende del modelo)
- **chaos_engineering_test.py**: 15-30 minutos

**Total**: ~2-3 horas para ejecutar todas las suites completas

---

## 🛡️ SAFETY

- Ejecutar en entorno aislado
- No en producción
- Tener backups
- Monitorear temperaturas GPU
- Prepararse para crashes
- Tener forma de matar procesos rápido

```bash
# Matar todo si se pone mal
pkill -9 -f "python3 tests"
pkill -9 -f "start_web.py"
pkill -9 -f "vllm"
```

---

## 📊 COMPARACIÓN CON OTROS TESTS

| Suite | Intensidad | Duración | Foco Principal |
|-------|-----------|----------|----------------|
| test_web_api.py | 🟢 Baja | 1-2 min | Funcionalidad básica |
| quick_smoke_test.py | 🟢 Baja | 1-2 min | Validación rápida |
| massive_stress_test.py | 🟡 Media | 30-60 min | Testing completo |
| extreme_stress_test.py | 🔴 Extrema | 20-40 min | Concurrencia masiva |
| gpu_destruction_test.py | 🔴 Extrema | 60-120 min | Estrés de GPU/VRAM |
| chaos_engineering_test.py | 🔴🔴 BRUTAL | 15-30 min | Romper activamente |

---

## 🎉 RESULTADO ESPERADO

Si el sistema **SOBREVIVE** estas 3 suites, entonces:

✅ Es extremadamente robusto
✅ Maneja cargas masivas
✅ No tiene memory leaks obvios
✅ Valida input correctamente
✅ Se recupera de errores
✅ Estado permanece consistente
✅ **PRODUCTION READY CONFIRMED**

Si el sistema **NO SOBREVIVE**, has encontrado bugs críticos que necesitan arreglarse URGENTEMENTE.

---

**¡Buena suerte! Que tu sistema sobreviva. 🔥**
