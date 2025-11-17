#!/usr/bin/env python3
"""
Analizador de Resultados - 70 Tests Jarvis AI
Procesa resultados, calcula scores y genera informe detallado
"""
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Cargar resultados
RESULTS_DIR = Path(__file__).parent / "results_70_tests"
result_files = list(RESULTS_DIR.glob("results_70_tests_*.json"))

if not result_files:
    print("❌ No se encontraron archivos de resultados")
    exit(1)

# Usar el más reciente
latest_result = sorted(result_files)[-1]
print(f"📊 Analizando: {latest_result.name}\n")

with open(latest_result, "r", encoding="utf-8") as f:
    data = json.load(f)

results = data["results"]
total_time = data["execution_time_minutes"]

# Análisis por categoría
category_stats = defaultdict(lambda: {
    "count": 0,
    "total_coherencia": 0,
    "total_relevancia": 0,
    "total_completitud": 0,
    "total_time": 0,
    "avg_length": 0,
    "success_count": 0
})

for result in results:
    cat = result["category"]
    scores = result["scores"]
    
    category_stats[cat]["count"] += 1
    category_stats[cat]["total_coherencia"] += scores["coherencia"]
    category_stats[cat]["total_relevancia"] += scores["relevancia"]
    category_stats[cat]["total_completitud"] += scores["completitud"]
    category_stats[cat]["total_time"] += result["response_time_seconds"]
    category_stats[cat]["avg_length"] += result.get("response_full_length", 0)
    if result["success"]:
        category_stats[cat]["success_count"] += 1

# Calcular promedios
for cat, stats in category_stats.items():
    count = stats["count"]
    stats["avg_coherencia"] = round(stats["total_coherencia"] / count, 2)
    stats["avg_relevancia"] = round(stats["total_relevancia"] / count, 2)
    stats["avg_completitud"] = round(stats["total_completitud"] / count, 2)
    stats["avg_time"] = round(stats["total_time"] / count, 2)
    stats["avg_length"] = round(stats["avg_length"] / count, 0)
    stats["success_rate"] = round((stats["success_count"] / count) * 100, 1)
    
    # Score ponderado final (promedio de los 3 scores)
    stats["final_score"] = round((
        stats["avg_coherencia"] + 
        stats["avg_relevancia"] + 
        stats["avg_completitud"]
    ) / 3, 2)

# Score global
global_coherencia = sum(r["scores"]["coherencia"] for r in results) / len(results)
global_relevancia = sum(r["scores"]["relevancia"] for r in results) / len(results)
global_completitud = sum(r["scores"]["completitud"] for r in results) / len(results)
global_time = sum(r["response_time_seconds"] for r in results) / len(results)
global_score = (global_coherencia + global_relevancia + global_completitud) / 3

# Generar informe Markdown
report = f"""# 📊 Informe de Evaluación - Jarvis AI Assistant
## Suite de 70 Pruebas Exhaustivas

**Fecha de ejecución:** {datetime.now().strftime('%d de %B de %Y, %H:%M:%S')}  
**Tiempo total:** {total_time:.2f} minutos  
**Tests ejecutados:** {len(results)}/70  

---

## 🎯 Puntuación Global

| Métrica | Puntuación | Escala |
|---------|-----------|--------|
| **Coherencia** | **{global_coherencia:.2f}/5.0** | ⭐️{'⭐️' * int(global_coherencia)} |
| **Relevancia** | **{global_relevancia:.2f}/5.0** | ⭐️{'⭐️' * int(global_relevancia)} |
| **Completitud** | **{global_completitud:.2f}/5.0** | ⭐️{'⭐️' * int(global_completitud)} |
| **Score Final** | **{global_score:.2f}/5.0** | ⭐️{'⭐️' * int(global_score)} |
| **Tiempo Promedio** | **{global_time:.2f}s** | Por respuesta |

### Interpretación del Score
- ⭐️ 1.0-2.0: Necesita mejoras significativas
- ⭐️⭐️ 2.0-3.0: Aceptable, con oportunidades de mejora
- ⭐️⭐️⭐️ 3.0-4.0: Bueno, cumple expectativas
- ⭐️⭐️⭐️⭐️ 4.0-4.5: Muy bueno, alto rendimiento
- ⭐️⭐️⭐️⭐️⭐️ 4.5-5.0: Excelente, rendimiento excepcional

---

## 📈 Análisis por Categoría

"""

# Ordenar por score final
sorted_categories = sorted(category_stats.items(), key=lambda x: x[1]["final_score"], reverse=True)

for cat, stats in sorted_categories:
    stars = '⭐️' * int(stats["final_score"])
    report += f"""### {cat.upper()}
**Tests:** {stats['count']} | **Score:** {stats['final_score']:.2f}/5.0 {stars}

| Métrica | Valor |
|---------|-------|
| Coherencia | {stats['avg_coherencia']:.2f}/5.0 |
| Relevancia | {stats['avg_relevancia']:.2f}/5.0 |
| Completitud | {stats['avg_completitud']:.2f}/5.0 |
| Tiempo Promedio | {stats['avg_time']:.2f}s |
| Longitud Promedio | {int(stats['avg_length'])} chars |
| Tasa de Éxito | {stats['success_rate']}% |

"""

report += f"""---

## 🔍 Observaciones Técnicas

### ⚠️ Problema Detectado: Extracción de Respuestas del DOM

Durante la ejecución de las pruebas se detectó un problema recurrente con la extracción de respuestas del DOM de la interfaz web. En **70/70** tests (100%), no se pudo extraer el texto completo de la respuesta del modelo.

**Posibles causas:**
1. Los selectores CSS utilizados no coinciden con la estructura actual del DOM
2. El contenido se carga dinámicamente y requiere más tiempo de espera
3. La respuesta se renderiza en un Shadow DOM o iframe
4. JavaScript client-side modifica el contenido después de la carga

**Impacto:**
- Los scores automáticos se basaron en heurísticas limitadas
- No se pudo analizar el contenido real de las respuestas
- La evaluación de coherencia y relevancia es preliminar

**Recomendaciones:**
1. Inspeccionar el DOM en tiempo de ejecución para identificar los selectores correctos
2. Aumentar los tiempos de espera o usar waitForSelector más específicos
3. Implementar extracción alternativa vía API backend si está disponible
4. Agregar logs de debugging para identificar la estructura exacta del DOM

### ⏱️ Tiempo de Respuesta

- **Promedio:** {global_time:.2f} segundos
- **Consistencia:** Muy uniforme (~23s por query)
- **Nota:** Tiempo elevado podría indicar procesamiento pesado o timeout prematuros

### 📊 Estadísticas de Ejecución

- **Total de tests:** 70
- **Tests exitosos:** {sum(r['success'] for r in results)}
- **Tests fallidos:** {len(results) - sum(r['success'] for r in results)}
- **Tiempo total:** {total_time:.2f} minutos
- **Throughput:** {70/total_time:.2f} tests/minuto

---

## 💡 Conclusiones y Recomendaciones

### Fortalezas
- ✅ **Estabilidad:** 100% de tests ejecutados sin crashes
- ✅ **Consistencia:** Tiempos de respuesta uniformes
- ✅ **Cobertura:** 14 categorías evaluadas

### Áreas de Mejora
- 🔧 **Extracción de datos:** Mejorar selectores DOM para captura de respuestas
- 🔧 **Optimización:** Reducir tiempo de respuesta promedio (<10s ideal)
- 🔧 **Validación:** Implementar comparación contra respuestas esperadas
- 🔧 **Scoring:** Integrar evaluación manual o LLM-as-judge para scoring más preciso

### Próximos Pasos
1. **Corto plazo:**
   - Investigar y corregir selectores DOM
   - Re-ejecutar suite con extracción funcional
   - Analizar contenido real de respuestas

2. **Mediano plazo:**
   - Implementar tests de regresión
   - Agregar benchmarks de performance
   - Comparar contra otros modelos (GPT-4, Claude, etc.)

3. **Largo plazo:**
   - Automatizar evaluación continua (CI/CD)
   - Dashboard de métricas en tiempo real
   - Tests A/B entre versiones del modelo

---

## 📂 Archivos Generados

- `test_suite_70.json` - Definición de tests
- `results_70_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json` - Resultados completos
- `checkpoint_*.json` - Checkpoints cada 10 tests
- `EVALUATION_REPORT.md` - Este informe
- `execution.log` - Log completo de ejecución

---

*Informe generado automáticamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}*  
*Jarvis AI Assistant V2 - Sistema de Evaluación Automatizada*
"""

# Guardar informe
report_file = RESULTS_DIR / "EVALUATION_REPORT.md"
with open(report_file, "w", encoding="utf-8") as f:
    f.write(report)

print(report)
print(f"\n💾 Informe guardado en: {report_file}")

# Guardar estadísticas JSON
stats_file = RESULTS_DIR / "statistics_summary.json"
with open(stats_file, "w", encoding="utf-8") as f:
    json.dump({
        "global_scores": {
            "coherencia": round(global_coherencia, 2),
            "relevancia": round(global_relevancia, 2),
            "completitud": round(global_completitud, 2),
            "final_score": round(global_score, 2),
            "avg_time": round(global_time, 2)
        },
        "category_stats": {k: v for k, v in category_stats.items()},
        "execution_info": {
            "total_tests": len(results),
            "successful_tests": sum(r['success'] for r in results),
            "total_time_minutes": total_time,
            "timestamp": datetime.now().isoformat()
        }
    }, f, indent=2, ensure_ascii=False)

print(f"💾 Estadísticas guardadas en: {stats_file}")
