#!/usr/bin/env python3
"""
Evaluador Automatizado - 70 Pruebas Jarvis AI
Ejecuta tests, captura respuestas, mide tiempos y genera scoring
"""
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
import re

# Configuración
BASE_URL = "http://localhost:8090"
RESULTS_DIR = Path(__file__).parent / "results_70_tests"
RESULTS_DIR.mkdir(exist_ok=True)

# Cargar suite de tests
with open(Path(__file__).parent / "test_suite_70.json", "r", encoding="utf-8") as f:
    TEST_DATA = json.load(f)

TESTS = TEST_DATA["tests"]

# Scoring heurístico automático
def auto_score_response(query: str, response: str, response_time: float) -> dict:
    """
    Scoring automático basado en heurísticas
    """
    scores = {
        "coherencia": 3,  # Default medio
        "relevancia": 3,
        "completitud": 3,
        "response_time": response_time,
        "response_length": len(response),
        "word_count": len(response.split()),
    }
    
    # Heurísticas de coherencia
    if len(response) < 10:
        scores["coherencia"] = 1
        scores["completitud"] = 1
    elif "no puedo" in response.lower() or "lo siento" in response.lower():
        scores["coherencia"] = 4  # Respuesta coherente pero negativa
        scores["completitud"] = 2
    elif len(response) > 200:
        scores["completitud"] = 5
    elif len(response) > 100:
        scores["completitud"] = 4
    
    # Heurísticas de relevancia (palabras clave de la query en la respuesta)
    query_words = set(re.findall(r'\w+', query.lower()))
    response_words = set(re.findall(r'\w+', response.lower()))
    overlap = len(query_words & response_words) / max(len(query_words), 1)
    
    if overlap > 0.5:
        scores["relevancia"] = 5
    elif overlap > 0.3:
        scores["relevancia"] = 4
    elif overlap > 0.1:
        scores["relevancia"] = 3
    else:
        scores["relevancia"] = 2
    
    # Bonus por estructura (listas, código, etc)
    if "```" in response or re.search(r'\d+\.|\-\s', response):
        scores["completitud"] = min(5, scores["completitud"] + 1)
    
    # Penalización por tiempo excesivo
    if response_time > 15:
        scores["coherencia"] = max(1, scores["coherencia"] - 1)
    
    return scores


async def run_evaluation():
    """Ejecuta la evaluación completa de 70 tests"""
    
    results = []
    start_time_total = time.time()
    
    async with async_playwright() as p:
        print("🚀 Iniciando evaluación de 70 tests...")
        print(f"📁 Resultados se guardarán en: {RESULTS_DIR}")
        print("="*80)
        
        browser = await p.chromium.launch(
            headless=True,  # Modo headless para velocidad
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="es-ES"
        )
        
        page = await context.new_page()
        
        try:
            # Navegar a la aplicación
            print(f"📍 Conectando a {BASE_URL}...")
            await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
            await page.wait_for_load_state("domcontentloaded")
            print("✅ Conexión establecida\n")
            
            # Selectores
            input_selector = 'textarea[placeholder*="mensaje"], textarea, input[type="text"]'
            button_selector = 'button:has-text("Enviar"), button[type="submit"], button:visible'
            
            # Ejecutar cada test
            for idx, test in enumerate(TESTS, start=1):
                print(f"[{idx}/70] Categoría: {test['category']} | ID: {test['id']}")
                print(f"   Query: {test['query'][:60]}...")
                
                test_start = time.time()
                
                try:
                    # Limpiar campo y enviar query
                    await page.fill(input_selector, "")
                    await asyncio.sleep(0.3)
                    await page.fill(input_selector, test['query'])
                    await asyncio.sleep(0.5)
                    
                    # Click enviar
                    await page.click(button_selector)
                    
                    # Esperar respuesta (máximo 20 segundos)
                    await asyncio.sleep(2)  # Tiempo inicial de procesamiento
                    
                    wait_time = 0
                    max_wait = 20
                    response_text = ""
                    
                    while wait_time < max_wait:
                        # Intentar extraer mensajes del asistente
                        try:
                            messages = await page.query_selector_all('.message.assistant, .assistant-message, [class*="assistant"]')
                            if messages:
                                last_msg = messages[-1]
                                response_text = await last_msg.inner_text()
                                
                                # Si la respuesta no está vacía y no hay indicador de carga
                                if response_text and len(response_text) > 5:
                                    loading = await page.query_selector('.loading, .typing, [class*="loading"]')
                                    if not loading:
                                        break
                        except:
                            pass
                        
                        await asyncio.sleep(1)
                        wait_time += 1
                    
                    response_time = time.time() - test_start
                    
                    # Si no se pudo extraer respuesta, intentar método alternativo
                    if not response_text or len(response_text) < 5:
                        response_text = "[No se pudo extraer respuesta del DOM]"
                        print(f"   ⚠️  No se extrajo respuesta del DOM")
                    
                    # Scoring automático
                    scores = auto_score_response(test['query'], response_text, response_time)
                    
                    # Guardar resultado
                    result = {
                        **test,
                        "response": response_text[:500],  # Limitar a 500 chars
                        "response_full_length": len(response_text),
                        "response_time_seconds": round(response_time, 2),
                        "scores": scores,
                        "timestamp": datetime.now().isoformat(),
                        "success": True
                    }
                    
                    results.append(result)
                    
                    print(f"   ⏱️  Tiempo: {response_time:.2f}s | Longitud: {len(response_text)} chars")
                    print(f"   📊 Scores: C:{scores['coherencia']} R:{scores['relevancia']} Co:{scores['completitud']}")
                    print(f"   ✅ Test completado\n")
                    
                    # Pequeña pausa entre tests
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"   ❌ Error en test {idx}: {e}\n")
                    results.append({
                        **test,
                        "response": f"[ERROR: {str(e)}]",
                        "response_time_seconds": 0,
                        "scores": {"coherencia": 0, "relevancia": 0, "completitud": 0},
                        "success": False
                    })
                
                # Checkpoint cada 10 tests
                if idx % 10 == 0:
                    checkpoint_file = RESULTS_DIR / f"checkpoint_{idx}.json"
                    with open(checkpoint_file, "w", encoding="utf-8") as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)
                    print(f"💾 Checkpoint guardado: {checkpoint_file}\n")
            
            total_time = time.time() - start_time_total
            
            print("="*80)
            print("✅ EVALUACIÓN COMPLETADA")
            print(f"⏱️  Tiempo total: {total_time/60:.2f} minutos")
            print(f"📊 Tests ejecutados: {len(results)}/70")
            print("="*80)
            
        except Exception as e:
            print(f"\n❌ ERROR CRÍTICO: {e}")
            raise
        
        finally:
            await browser.close()
    
    # Guardar resultados finales
    output_file = RESULTS_DIR / f"results_70_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_tests": len(results),
            "execution_time_minutes": round((time.time() - start_time_total) / 60, 2),
            "timestamp": datetime.now().isoformat(),
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Resultados guardados en: {output_file}")
    
    return results, output_file


if __name__ == "__main__":
    print("="*80)
    print("🧪 EVALUADOR AUTOMÁTICO - JARVIS AI ASSISTANT")
    print("="*80)
    print(f"📝 Total de tests: {len(TESTS)}")
    print(f"🎯 Categorías: {len(set(t['category'] for t in TESTS))}")
    print(f"🌐 URL objetivo: {BASE_URL}")
    print("="*80 + "\n")
    
    results, output_file = asyncio.run(run_evaluation())
    
    print("\n✅ Proceso completado exitosamente")
    print(f"📄 Archivo de resultados: {output_file}")
