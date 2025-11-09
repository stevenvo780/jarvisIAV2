#!/usr/bin/env python3
"""
Script de validación continua de Jarvis - Ciclo infinito de mejora
Ejecuta pruebas, identifica problemas, propone mejoras, las implementa y repite.
"""
import subprocess
import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path

class JarvisValidator:
    def __init__(self, workspace_root):
        self.workspace = Path(workspace_root)
        self.iteration = 0
        self.results = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def run_command(self, cmd, capture=True):
        """Ejecuta comando y retorna resultado"""
        self.log(f"Ejecutando: {cmd}")
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=capture,
                text=True,
                timeout=30
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Timeout",
                "stdout": "",
                "stderr": "Command timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": str(e)
            }
    
    def test_basic_conversation(self):
        """Prueba capacidad de conversación básica"""
        self.log("=== TEST: Conversación Básica ===")
        
        # Simulamos una pregunta simple
        test_query = "¿Cuánto es 2+2?"
        
        # Por ahora solo verificamos que los módulos se puedan importar
        result = self.run_command(f"cd {self.workspace} && python3 -c 'import sys; sys.path.insert(0, \".\"); from src.modules.orchestrator.model_orchestrator import ModelOrchestrator; print(\"OK\")'")
        
        return {
            "name": "basic_conversation",
            "passed": result["success"],
            "details": result
        }
    
    def test_terminal_execution(self):
        """Prueba ejecución de comandos en terminal"""
        self.log("=== TEST: Ejecución en Terminal ===")
        
        result = self.run_command(f"cd {self.workspace} && python3 -c 'import subprocess; r = subprocess.run([\"echo\", \"test\"], capture_output=True, text=True); print(r.stdout.strip())'")
        
        return {
            "name": "terminal_execution",
            "passed": result["success"] and "test" in result["stdout"],
            "details": result
        }
    
    def test_file_operations(self):
        """Prueba operaciones con archivos"""
        self.log("=== TEST: Operaciones con Archivos ===")
        
        test_file = self.workspace / "test_temp.txt"
        
        # Crear archivo
        result1 = self.run_command(f"cd {self.workspace} && python3 -c 'with open(\"test_temp.txt\", \"w\") as f: f.write(\"test content\")'")
        
        # Leer archivo
        result2 = self.run_command(f"cd {self.workspace} && python3 -c 'with open(\"test_temp.txt\", \"r\") as f: print(f.read())'")
        
        # Eliminar archivo
        if test_file.exists():
            test_file.unlink()
        
        return {
            "name": "file_operations",
            "passed": result1["success"] and result2["success"] and "test content" in result2["stdout"],
            "details": {"write": result1, "read": result2}
        }
    
    def test_module_imports(self):
        """Prueba importación de módulos principales"""
        self.log("=== TEST: Importación de Módulos ===")
        
        modules = [
            "src.modules.orchestrator.model_orchestrator",
            "src.modules.text.terminal_manager",
            "src.utils.error_handler",
        ]
        
        results = {}
        all_passed = True
        
        for module in modules:
            cmd = f"cd {self.workspace} && python3 -c 'import sys; sys.path.insert(0, \".\"); import {module}; print(\"OK\")'"
            result = self.run_command(cmd)
            results[module] = result["success"]
            if not result["success"]:
                all_passed = False
                self.log(f"Failed to import {module}: {result['stderr']}", "ERROR")
        
        return {
            "name": "module_imports",
            "passed": all_passed,
            "details": results
        }
    
    def test_python_code_execution(self):
        """Prueba ejecución de código Python"""
        self.log("=== TEST: Ejecución de Código Python ===")
        
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = [fibonacci(i) for i in range(10)]
print(result)
"""
        
        result = self.run_command(f"cd {self.workspace} && python3 -c '{code}'")
        
        expected = "[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]"
        
        return {
            "name": "python_code_execution",
            "passed": result["success"] and expected in result["stdout"],
            "details": result
        }
    
    def analyze_improvements(self, test_results):
        """Analiza resultados y sugiere mejoras"""
        self.log("=== ANÁLISIS DE MEJORAS ===")
        
        failed_tests = [t for t in test_results if not t["passed"]]
        
        if not failed_tests:
            self.log("✓ Todos los tests pasaron!", "SUCCESS")
            return []
        
        improvements = []
        
        for test in failed_tests:
            self.log(f"✗ Test fallido: {test['name']}", "WARNING")
            
            if test['name'] == 'module_imports':
                improvements.append({
                    "priority": "HIGH",
                    "area": "dependencies",
                    "action": "Instalar dependencias faltantes",
                    "details": test['details']
                })
            
            elif test['name'] == 'basic_conversation':
                improvements.append({
                    "priority": "HIGH",
                    "area": "core",
                    "action": "Verificar configuración del orquestador de modelos",
                    "details": test['details']
                })
        
        return improvements
    
    def run_validation_cycle(self):
        """Ejecuta un ciclo completo de validación"""
        self.iteration += 1
        self.log(f"\n{'='*60}")
        self.log(f"ITERACIÓN #{self.iteration}")
        self.log(f"{'='*60}\n")
        
        # Ejecutar tests
        test_results = [
            self.test_module_imports(),
            self.test_file_operations(),
            self.test_terminal_execution(),
            self.test_python_code_execution(),
            # self.test_basic_conversation(),  # Requiere dependencias
        ]
        
        # Analizar resultados
        improvements = self.analyze_improvements(test_results)
        
        # Guardar resultados
        result_summary = {
            "iteration": self.iteration,
            "timestamp": datetime.now().isoformat(),
            "tests": test_results,
            "improvements": improvements,
            "stats": {
                "total": len(test_results),
                "passed": sum(1 for t in test_results if t["passed"]),
                "failed": sum(1 for t in test_results if not t["passed"])
            }
        }
        
        self.results.append(result_summary)
        
        # Mostrar resumen
        self.log(f"\n{'='*60}")
        self.log(f"RESUMEN ITERACIÓN #{self.iteration}")
        self.log(f"{'='*60}")
        self.log(f"Tests ejecutados: {result_summary['stats']['total']}")
        self.log(f"Tests exitosos: {result_summary['stats']['passed']}")
        self.log(f"Tests fallidos: {result_summary['stats']['failed']}")
        self.log(f"Mejoras identificadas: {len(improvements)}")
        
        # Guardar a archivo
        output_file = self.workspace / f"validation_results_iteration_{self.iteration}.json"
        with open(output_file, 'w') as f:
            json.dump(result_summary, f, indent=2)
        
        self.log(f"Resultados guardados en: {output_file}")
        
        return result_summary
    
    def run_continuous(self, max_iterations=None, delay=5):
        """Ejecuta validación continua"""
        self.log("Iniciando ciclo de validación continua de Jarvis...")
        self.log(f"Workspace: {self.workspace}")
        
        if max_iterations:
            self.log(f"Iteraciones máximas: {max_iterations}")
        else:
            self.log("Iteraciones: INFINITAS (Ctrl+C para detener)")
        
        self.log(f"Delay entre iteraciones: {delay}s\n")
        
        try:
            iteration_count = 0
            while True:
                if max_iterations and iteration_count >= max_iterations:
                    break
                
                result = self.run_validation_cycle()
                iteration_count += 1
                
                # Si todos los tests pasan, podemos aumentar la complejidad
                if result['stats']['failed'] == 0:
                    self.log("\n🎉 Todos los tests pasaron! Sistema estable.", "SUCCESS")
                    self.log("Próxima iteración: aumentar complejidad de pruebas...")
                
                # Esperar antes de la siguiente iteración
                if max_iterations is None or iteration_count < max_iterations:
                    self.log(f"\nEsperando {delay}s antes de la siguiente iteración...")
                    time.sleep(delay)
        
        except KeyboardInterrupt:
            self.log("\n\nValidación detenida por el usuario.", "WARNING")
        
        finally:
            self.log(f"\nTotal de iteraciones completadas: {self.iteration}")
            self.log("Generando reporte final...")
            
            # Guardar reporte final
            final_report = {
                "total_iterations": self.iteration,
                "all_results": self.results,
                "final_stats": {
                    "avg_passed": sum(r['stats']['passed'] for r in self.results) / len(self.results) if self.results else 0,
                    "avg_failed": sum(r['stats']['failed'] for r in self.results) / len(self.results) if self.results else 0,
                }
            }
            
            report_file = self.workspace / "validation_final_report.json"
            with open(report_file, 'w') as f:
                json.dump(final_report, f, indent=2)
            
            self.log(f"Reporte final guardado en: {report_file}")

if __name__ == "__main__":
    workspace = os.path.dirname(os.path.abspath(__file__))
    validator = JarvisValidator(workspace)
    
    # Por defecto, ejecutar indefinidamente
    # Cambiar max_iterations a un número para limitar
    validator.run_continuous(max_iterations=None, delay=10)
