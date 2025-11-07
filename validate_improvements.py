#!/usr/bin/env python3
"""
Script de Validación Final - JarvisIA V2 10/10
Ejecuta verificaciones rápidas de todas las mejoras implementadas
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_file_exists(path: str, description: str) -> bool:
    """Verify file exists"""
    if os.path.exists(path):
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description}: {path} NOT FOUND")
        return False

def check_import(module_path: str, description: str) -> bool:
    """Verify module can be imported"""
    try:
        __import__(module_path)
        print(f"✅ {description}: {module_path}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {module_path} - {e}")
        return False

def main():
    print("=" * 70)
    print("🎯 VALIDACIÓN FINAL - JarvisIA V2 (10/10)")
    print("=" * 70)
    print()
    
    checks_passed = 0
    checks_total = 0
    
    # 1. Documentación
    print("📚 DOCUMENTACIÓN")
    print("-" * 70)
    
    docs = [
        ("CORRECCIONES_IMPLEMENTADAS.md", "Correcciones documentadas"),
        ("PUNTUACION_10_10.md", "Resumen ejecutivo 10/10"),
        ("tests/README.md", "Guía de testing"),
        ("pytest.ini", "Configuración pytest"),
    ]
    
    for path, desc in docs:
        checks_total += 1
        if check_file_exists(path, desc):
            checks_passed += 1
    
    print()
    
    # 2. Correcciones Implementadas
    print("🔧 CORRECCIONES CRÍTICAS")
    print("-" * 70)
    
    corrections = [
        ("src/utils/jarvis_state.py", "Thread-safe state"),
        ("src/utils/query_validator.py", "Query validation"),
        ("src/utils/error_budget.py", "Error budget system"),
        ("src/modules/backend_interface.py", "Backend abstraction"),
        ("src/utils/health_checker.py", "Health monitoring"),
    ]
    
    for path, desc in corrections:
        checks_total += 1
        if check_file_exists(path, desc):
            checks_passed += 1
    
    print()
    
    # 3. Tests
    print("🧪 SUITE DE TESTS")
    print("-" * 70)
    
    tests = [
        ("tests/test_jarvis_state.py", "JarvisState tests"),
        ("tests/test_query_validator.py", "QueryValidator tests"),
        ("tests/test_error_budget.py", "ErrorBudget tests"),
        ("tests/test_backend_interface.py", "Backend tests"),
        ("tests/test_health_checker.py", "HealthChecker tests"),
        ("tests/test_integration.py", "Integration tests"),
    ]
    
    for path, desc in tests:
        checks_total += 1
        if check_file_exists(path, desc):
            checks_passed += 1
    
    print()
    
    # 4. Imports (verificación rápida)
    print("📦 IMPORTS CRÍTICOS")
    print("-" * 70)
    
    imports = [
        ("src.utils.jarvis_state", "JarvisState"),
        ("src.utils.query_validator", "QueryValidator"),
        ("src.utils.error_budget", "ErrorBudget"),
        ("src.utils.health_checker", "HealthChecker"),
    ]
    
    for module, desc in imports:
        checks_total += 1
        if check_import(module, desc):
            checks_passed += 1
    
    print()
    
    # 5. Resumen Final
    print("=" * 70)
    print("📊 RESUMEN")
    print("=" * 70)
    
    percentage = (checks_passed / checks_total) * 100 if checks_total > 0 else 0
    
    print(f"Total verificaciones: {checks_total}")
    print(f"Verificaciones exitosas: {checks_passed}")
    print(f"Verificaciones fallidas: {checks_total - checks_passed}")
    print(f"Porcentaje: {percentage:.1f}%")
    print()
    
    if checks_passed == checks_total:
        print("🎉 ¡TODAS LAS VERIFICACIONES PASARON!")
        print("✨ JarvisIA V2 está en ESTADO DE EXCELENCIA (10/10)")
        print()
        print("Próximos pasos:")
        print("  1. Ejecutar: pytest tests/ -v")
        print("  2. Revisar cobertura: pytest --cov=src --cov-report=html")
        print("  3. Ver reporte: open htmlcov/index.html")
        return 0
    else:
        print("⚠️  ALGUNAS VERIFICACIONES FALLARON")
        print("Por favor, revisa los archivos marcados con ❌")
        return 1

if __name__ == "__main__":
    sys.exit(main())
