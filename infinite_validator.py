#!/usr/bin/env python3
"""
Validador infinito de Jarvis - Ejecuta consultas variadas sin parar
Detecta errores, reporta métricas, optimiza configuración automáticamente
"""
import subprocess
import time
import json
import random
from datetime import datetime
from pathlib import Path

# Consultas variadas por complejidad (difficulty estimada)
QUERIES = {
    "simple": [
        "¿Cuánto es 5+3?",
        "¿Qué hora es?",
        "Hola Jarvis",
        "¿Cómo estás?",
        "¿Cuál es tu nombre?",
        "Di un número del 1 al 10",
        "¿Qué día es hoy?",
        "Cuenta hasta 5",
    ],
    "medium": [
        "Explica qué es Python en 2 líneas",
        "¿Cuál es la capital de Francia?",
        "¿Quién inventó la bombilla?",
        "¿Cuántos planetas hay en el sistema solar?",
        "Define inteligencia artificial brevemente",
        "¿Qué es el teorema de Pitágoras?",
        "Nombra 3 lenguajes de programación",
        "¿Qué es un algoritmo?",
    ],
    "complex": [
        "Explica la teoría de la relatividad de Einstein",
        "¿Cómo funciona una red neuronal convolucional?",
        "Analiza las diferencias entre async/await y threads en Python",
        "Explica el algoritmo de backpropagation",
        "¿Qué es la computación cuántica?",
        "Describe la arquitectura transformer en deep learning",
        "Explica el teorema de Bayes con ejemplos",
        "¿Cómo funciona el algoritmo de Dijkstra?",
    ]
}

class InfiniteValidator:
    def __init__(self):
        self.iteration = 0
        self.stats = {
            "success": 0,
            "errors": 0,
            "local_model": 0,
            "api_fallback": 0,
            "total_time": 0.0
        }
        self.log_file = Path("artifacts/infinite_validation.log")
        self.log_file.parent.mkdir(exist_ok=True)
        
    def log(self, msg):
        """Log con timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        with open(self.log_file, "a") as f:
            f.write(line + "\n")
    
    def run_query(self, query, model="qwen-14b"):
        """Ejecuta consulta y captura resultado"""
        start = time.time()
        cmd = ["python3", "main.py", "--query", query]
        if model:
            cmd.extend(["--model", model])
        
        self.log(f"▶ Ejecutando: {query[:50]}...")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # Reducido de 120s a 60s
                cwd="/datos/repos/Personal/jarvisIAV2"
            )
            elapsed = time.time() - start
            
            output = result.stdout + result.stderr
            
            # Detectar tipo de respuesta
            used_local = "vllm" in output.lower() or "qwen" in output.lower()
            used_api = "api.openai.com" in output or "generativeai" in output
            has_error = result.returncode != 0 or "error" in output.lower() or "traceback" in output.lower()
            
            return {
                "success": not has_error,
                "elapsed": elapsed,
                "used_local": used_local,
                "used_api": used_api,
                "output": output[-500:]  # Solo últimas 500 chars
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "elapsed": 120.0,
                "used_local": False,
                "used_api": False,
                "output": "TIMEOUT after 120s"
            }
        except Exception as e:
            return {
                "success": False,
                "elapsed": time.time() - start,
                "used_local": False,
                "used_api": False,
                "output": f"Exception: {str(e)}"
            }
    
    def select_query(self):
        """Selecciona consulta con distribución: 60% simple, 30% medium, 10% complex"""
        rand = random.random()
        if rand < 0.6:
            category = "simple"
        elif rand < 0.9:
            category = "medium"
        else:
            category = "complex"
        
        return random.choice(QUERIES[category]), category
    
    def run_iteration(self):
        """Ejecuta una iteración del ciclo"""
        self.iteration += 1
        query, category = self.select_query()
        
        self.log(f"\n{'='*80}")
        self.log(f"ITERATION #{self.iteration} | Category: {category.upper()}")
        self.log(f"Query: {query}")
        self.log(f"{'='*80}")
        
        # Decidir modelo: simple usa auto-select (puede caer en API), rest prefiere local
        model = None if category == "simple" else "qwen-14b"
        result = self.run_query(query, model)
        
        # Actualizar stats
        if result["success"]:
            self.stats["success"] += 1
        else:
            self.stats["errors"] += 1
            self.log(f"❌ ERROR DETECTED:\n{result['output']}")
        
        if result["used_local"]:
            self.stats["local_model"] += 1
            self.log(f"✅ LOCAL MODEL (qwen-14b) | {result['elapsed']:.2f}s")
        elif result["used_api"]:
            self.stats["api_fallback"] += 1
            self.log(f"🌐 API FALLBACK | {result['elapsed']:.2f}s")
        
        self.stats["total_time"] += result["elapsed"]
        
        # Reportar stats cada 10 iteraciones
        if self.iteration % 10 == 0:
            self.report_stats()
        
        # Pausa breve para evitar saturación
        time.sleep(2)
    
    def report_stats(self):
        """Reporte de estadísticas acumuladas"""
        self.log(f"\n{'='*80}")
        self.log(f"📊 STATS AFTER {self.iteration} ITERATIONS")
        self.log(f"{'='*80}")
        self.log(f"Success rate: {self.stats['success']}/{self.iteration} ({100*self.stats['success']/self.iteration:.1f}%)")
        self.log(f"Errors: {self.stats['errors']}")
        self.log(f"Local model: {self.stats['local_model']} ({100*self.stats['local_model']/self.iteration:.1f}%)")
        self.log(f"API fallback: {self.stats['api_fallback']} ({100*self.stats['api_fallback']/self.iteration:.1f}%)")
        self.log(f"Avg time: {self.stats['total_time']/self.iteration:.2f}s")
        self.log(f"{'='*80}\n")
        
        # Guardar stats JSON
        with open("artifacts/infinite_validation_stats.json", "w") as f:
            json.dump({
                "iteration": self.iteration,
                "timestamp": datetime.now().isoformat(),
                "stats": self.stats
            }, f, indent=2)
    
    def run_forever(self):
        """Ciclo infinito principal"""
        self.log("🚀 INFINITE VALIDATOR STARTED")
        self.log("Press Ctrl+C to stop (but don't, keep it running!)")
        
        try:
            while True:
                self.run_iteration()
        except KeyboardInterrupt:
            self.log("\n⚠️  Validator stopped by user")
            self.report_stats()
        except Exception as e:
            self.log(f"\n❌ FATAL ERROR: {e}")
            self.report_stats()
            # Restart automático
            time.sleep(5)
            self.run_forever()

if __name__ == "__main__":
    validator = InfiniteValidator()
    validator.run_forever()
