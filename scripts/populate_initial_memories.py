#!/usr/bin/env python3
"""
Populate Initial Memories - Jarvis IA
Genera memorias de entrenamiento iniciales para el sistema RAG
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.modules.embeddings.embedding_manager import EmbeddingManager


# Dataset de memorias de entrenamiento iniciales
INITIAL_MEMORIES = [
    # Programación Python - Básico
    {
        "query": "¿Cómo crear una lista en Python?",
        "response": "Para crear una lista en Python usa corchetes []. Ejemplos:\n```python\n# Lista vacía\nmi_lista = []\n\n# Lista con elementos\nnumeros = [1, 2, 3, 4, 5]\nfrutas = ['manzana', 'pera', 'uva']\nmixta = [1, 'texto', True, 3.14]\n```",
        "model": "qwen-14b",
        "difficulty": 15,
        "task_type": "code_explanation"
    },
    {
        "query": "Explica qué son las funciones en Python",
        "response": "Las funciones en Python son bloques de código reutilizables que realizan una tarea específica.\n\n**Definición básica:**\n```python\ndef mi_funcion():\n    print('Hola')\n\nmi_funcion()  # Llama la función\n```\n\n**Con parámetros:**\n```python\ndef saludar(nombre):\n    return f'Hola {nombre}'\n\nresultado = saludar('Ana')  # 'Hola Ana'\n```\n\n**Ventajas:** código organizado, reutilizable y fácil de mantener.",
        "model": "qwen-14b",
        "difficulty": 25,
        "task_type": "explanation"
    },
    
    # Programación Python - Intermedio
    {
        "query": "¿Qué es una list comprehension?",
        "response": "Una list comprehension es una forma concisa de crear listas en Python.\n\n**Sintaxis:** `[expresion for item in iterable if condicion]`\n\n**Ejemplos:**\n```python\n# Cuadrados del 1 al 10\ncuadrados = [x**2 for x in range(1, 11)]\n# [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]\n\n# Solo números pares\npares = [x for x in range(20) if x % 2 == 0]\n# [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]\n\n# Transformar strings\nmayusculas = [palabra.upper() for palabra in ['hola', 'mundo']]\n# ['HOLA', 'MUNDO']\n```\n\n**Ventaja:** Más legible y rápido que usar bucles for tradicionales.",
        "model": "qwen-14b",
        "difficulty": 35,
        "task_type": "code_explanation"
    },
    {
        "query": "Genera una función para búsqueda binaria",
        "response": "Aquí está la implementación de búsqueda binaria:\n\n```python\ndef busqueda_binaria(arr, objetivo):\n    \"\"\"\n    Búsqueda binaria en array ordenado.\n    \n    Args:\n        arr: Lista ordenada\n        objetivo: Valor a buscar\n    \n    Returns:\n        Índice del elemento o -1 si no existe\n    \"\"\"\n    izq, der = 0, len(arr) - 1\n    \n    while izq <= der:\n        medio = (izq + der) // 2\n        \n        if arr[medio] == objetivo:\n            return medio\n        elif arr[medio] < objetivo:\n            izq = medio + 1\n        else:\n            der = medio - 1\n    \n    return -1\n\n# Ejemplo de uso\nnumeros = [1, 3, 5, 7, 9, 11, 13, 15]\nresultado = busqueda_binaria(numeros, 7)\nprint(f'Encontrado en índice: {resultado}')  # 3\n```\n\n**Complejidad:** O(log n) - muy eficiente para listas grandes.",
        "model": "qwen-14b",
        "difficulty": 50,
        "task_type": "code_generation"
    },
    
    # Algoritmos y Estructuras de Datos
    {
        "query": "Explica el algoritmo QuickSort paso a paso",
        "response": "**QuickSort** es un algoritmo de ordenamiento eficiente que usa divide y conquista.\n\n**Pasos:**\n1. Elegir un **pivote** (ej: último elemento)\n2. **Particionar:** elementos menores a la izquierda, mayores a la derecha\n3. **Recursión:** aplicar QuickSort a ambas particiones\n\n**Implementación:**\n```python\ndef quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    \n    pivote = arr[-1]\n    menores = [x for x in arr[:-1] if x <= pivote]\n    mayores = [x for x in arr[:-1] if x > pivote]\n    \n    return quicksort(menores) + [pivote] + quicksort(mayores)\n\n# Ejemplo\nnums = [64, 34, 25, 12, 22, 11, 90]\nordenado = quicksort(nums)\nprint(ordenado)  # [11, 12, 22, 25, 34, 64, 90]\n```\n\n**Complejidad:**\n- Promedio: O(n log n)\n- Peor caso: O(n²)\n- Espacio: O(log n) por recursión",
        "model": "qwen-32b",
        "difficulty": 65,
        "task_type": "explanation"
    },
    {
        "query": "¿Qué es un árbol binario de búsqueda?",
        "response": "Un **árbol binario de búsqueda (BST)** es una estructura de datos donde cada nodo tiene como máximo 2 hijos, y cumple:\n\n- Hijo izquierdo < Nodo padre\n- Hijo derecho > Nodo padre\n\n**Implementación:**\n```python\nclass Nodo:\n    def __init__(self, valor):\n        self.valor = valor\n        self.izquierdo = None\n        self.derecho = None\n\nclass BST:\n    def __init__(self):\n        self.raiz = None\n    \n    def insertar(self, valor):\n        if not self.raiz:\n            self.raiz = Nodo(valor)\n        else:\n            self._insertar_recursivo(self.raiz, valor)\n    \n    def _insertar_recursivo(self, nodo, valor):\n        if valor < nodo.valor:\n            if nodo.izquierdo is None:\n                nodo.izquierdo = Nodo(valor)\n            else:\n                self._insertar_recursivo(nodo.izquierdo, valor)\n        else:\n            if nodo.derecho is None:\n                nodo.derecho = Nodo(valor)\n            else:\n                self._insertar_recursivo(nodo.derecho, valor)\n    \n    def buscar(self, valor):\n        return self._buscar_recursivo(self.raiz, valor)\n    \n    def _buscar_recursivo(self, nodo, valor):\n        if nodo is None or nodo.valor == valor:\n            return nodo\n        if valor < nodo.valor:\n            return self._buscar_recursivo(nodo.izquierdo, valor)\n        return self._buscar_recursivo(nodo.derecho, valor)\n```\n\n**Operaciones:** búsqueda, inserción, eliminación en O(log n) promedio.",
        "model": "qwen-32b",
        "difficulty": 70,
        "task_type": "code_generation"
    },
    
    # Conceptos de IA/ML
    {
        "query": "¿Qué es una red neuronal?",
        "response": "Una **red neuronal** es un modelo de ML inspirado en el cerebro humano.\n\n**Componentes:**\n1. **Neuronas:** Unidades que procesan información\n2. **Capas:** Input, Hidden, Output\n3. **Pesos:** Conexiones entre neuronas\n4. **Función de activación:** Introduce no-linealidad (ReLU, Sigmoid, Tanh)\n\n**Funcionamiento:**\n```\nInput → Hidden Layers → Output\n  ↓         ↓              ↓\n x₁      w₁×x₁+w₂×x₂    y\n x₂      activation\n```\n\n**Tipos:**\n- **Feedforward:** Información fluye hacia adelante\n- **Convolutional (CNN):** Para imágenes\n- **Recurrent (RNN):** Para secuencias (texto, audio)\n- **Transformer:** Atención para NLP\n\n**Aplicaciones:** Visión computacional, NLP, speech recognition, juegos.",
        "model": "qwen-32b",
        "difficulty": 55,
        "task_type": "explanation"
    },
    {
        "query": "Explica qué es RAG (Retrieval Augmented Generation)",
        "response": "**RAG** combina recuperación de información con generación de texto.\n\n**Cómo funciona:**\n1. **Embedding:** Convierte documentos a vectores\n2. **Vectorstore:** Almacena embeddings (ChromaDB, Pinecone)\n3. **Query:** Usuario hace pregunta\n4. **Retrieval:** Busca documentos relevantes por similitud semántica\n5. **Augmentation:** Añade contexto al prompt\n6. **Generation:** LLM genera respuesta con contexto\n\n**Ventajas:**\n- Información actualizada (no solo conocimiento pre-entrenado)\n- Reducción de alucinaciones\n- Citas/fuentes verificables\n- No requiere re-entrenar el modelo\n\n**Arquitectura típica:**\n```\nDocumentos → Embeddings → VectorDB\n                              ↓\nQuery → Embedding → Similarity Search → Top K docs\n                                           ↓\n                               Prompt + Context → LLM → Response\n```\n\n**Use cases:** Chatbots empresariales, Q&A sobre documentación, asistentes personalizados.",
        "model": "qwen-32b",
        "difficulty": 60,
        "task_type": "explanation"
    },
    
    # Linux/Terminal
    {
        "query": "¿Cómo buscar archivos en Linux?",
        "response": "Hay varias formas de buscar archivos en Linux:\n\n**1. find (más potente):**\n```bash\n# Por nombre\nfind /ruta -name \"archivo.txt\"\n\n# Por extensión\nfind . -name \"*.py\"\n\n# Por tamaño\nfind . -size +100M\n\n# Modificados últimos 7 días\nfind . -mtime -7\n\n# Ejecutar comando en resultados\nfind . -name \"*.log\" -exec rm {} \\;\n```\n\n**2. locate (más rápido, usa índice):**\n```bash\nlocate archivo.txt\nupdatedb  # Actualizar índice\n```\n\n**3. grep (buscar contenido):**\n```bash\n# Buscar texto en archivos\ngrep -r \"patrón\" /ruta\n\n# Con número de línea\ngrep -rn \"error\" /var/log\n\n# Ignorar mayúsculas\ngrep -ri \"warning\" .\n```",
        "model": "qwen-14b",
        "difficulty": 30,
        "task_type": "explanation"
    },
    {
        "query": "Comandos útiles de git",
        "response": "Comandos esenciales de **git**:\n\n**Básicos:**\n```bash\ngit init                    # Iniciar repo\ngit clone <url>            # Clonar repo\ngit status                 # Ver estado\ngit add .                  # Añadir todos\ngit commit -m \"mensaje\"    # Commit\ngit push origin main       # Subir cambios\ngit pull                   # Bajar cambios\n```\n\n**Branches:**\n```bash\ngit branch                 # Listar branches\ngit branch nueva-rama      # Crear branch\ngit checkout nueva-rama    # Cambiar a branch\ngit checkout -b feature    # Crear y cambiar\ngit merge feature          # Fusionar branch\ngit branch -d feature      # Borrar branch\n```\n\n**Historial:**\n```bash\ngit log                    # Ver commits\ngit log --oneline          # Resumido\ngit diff                   # Ver cambios\ngit show <commit>          # Ver commit específico\n```\n\n**Deshacer:**\n```bash\ngit reset --hard HEAD      # Descartar cambios\ngit revert <commit>        # Revertir commit\ngit stash                  # Guardar temporalmente\ngit stash pop              # Recuperar\n```",
        "model": "qwen-14b",
        "difficulty": 40,
        "task_type": "explanation"
    },
    
    # Conceptos Generales
    {
        "query": "¿Qué es Docker?",
        "response": "**Docker** es una plataforma para crear, distribuir y ejecutar aplicaciones en contenedores.\n\n**Contenedor:** Paquete ligero con todo lo necesario para ejecutar una app (código, runtime, librerías, dependencias).\n\n**Ventajas:**\n- **Portabilidad:** Funciona igual en dev, staging, prod\n- **Aislamiento:** Cada contenedor es independiente\n- **Eficiencia:** Más ligero que VMs (comparte kernel)\n- **Escalabilidad:** Fácil crear múltiples instancias\n\n**Comandos básicos:**\n```bash\n# Descargar imagen\ndocker pull ubuntu:22.04\n\n# Ejecutar contenedor\ndocker run -it ubuntu:22.04 bash\n\n# Listar contenedores\ndocker ps\ndocker ps -a  # Incluir detenidos\n\n# Detener/iniciar\ndocker stop <container_id>\ndocker start <container_id>\n\n# Eliminar\ndocker rm <container_id>\ndocker rmi <image_id>\n```\n\n**Dockerfile ejemplo:**\n```dockerfile\nFROM python:3.10\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD [\"python\", \"app.py\"]\n```",
        "model": "qwen-32b",
        "difficulty": 45,
        "task_type": "explanation"
    },
    {
        "query": "Explica REST API",
        "response": "**REST API** (Representational State Transfer) es un estilo de arquitectura para servicios web.\n\n**Principios:**\n1. **Cliente-Servidor:** Separación de responsabilidades\n2. **Stateless:** Cada request es independiente\n3. **Cacheable:** Respuestas pueden ser cacheadas\n4. **Uniform Interface:** URIs consistentes\n\n**Métodos HTTP:**\n- **GET:** Obtener recursos\n- **POST:** Crear recursos\n- **PUT:** Actualizar completo\n- **PATCH:** Actualizar parcial\n- **DELETE:** Eliminar recursos\n\n**Ejemplo:**\n```\nGET    /api/users          # Listar usuarios\nGET    /api/users/123      # Obtener usuario 123\nPOST   /api/users          # Crear usuario\nPUT    /api/users/123      # Actualizar usuario 123\nDELETE /api/users/123      # Eliminar usuario 123\n```\n\n**Códigos de estado:**\n- 200 OK: Éxito\n- 201 Created: Recurso creado\n- 400 Bad Request: Error del cliente\n- 401 Unauthorized: No autenticado\n- 404 Not Found: No existe\n- 500 Internal Server Error: Error del servidor\n\n**Formato:** Generalmente JSON\n```json\n{\n  \"id\": 123,\n  \"name\": \"Juan\",\n  \"email\": \"juan@example.com\"\n}\n```",
        "model": "qwen-32b",
        "difficulty": 50,
        "task_type": "explanation"
    },
    
    # Debugging y Testing
    {
        "query": "¿Cómo hacer debugging en Python?",
        "response": "Técnicas de **debugging** en Python:\n\n**1. Print statements (básico):**\n```python\nprint(f\"Variable x: {x}\")\nprint(f\"Tipo: {type(x)}, Valor: {x}\")\n```\n\n**2. pdb (Python Debugger):**\n```python\nimport pdb\n\ndef funcion_problematica():\n    x = 10\n    pdb.set_trace()  # Breakpoint\n    y = x * 2\n    return y\n```\nComandos: `n` (next), `s` (step), `c` (continue), `p var` (print), `q` (quit)\n\n**3. logging (profesional):**\n```python\nimport logging\n\nlogging.basicConfig(level=logging.DEBUG)\nlogger = logging.getLogger(__name__)\n\nlogger.debug(\"Info detallada\")\nlogger.info(\"Info general\")\nlogger.warning(\"Advertencia\")\nlogger.error(\"Error\")\nlogger.critical(\"Crítico\")\n```\n\n**4. try/except con traceback:**\n```python\nimport traceback\n\ntry:\n    resultado = 1 / 0\nexcept Exception as e:\n    logger.error(f\"Error: {e}\")\n    logger.error(traceback.format_exc())\n```\n\n**5. assert (validaciones):**\n```python\nassert x > 0, \"x debe ser positivo\"\nassert isinstance(y, int), \"y debe ser int\"\n```",
        "model": "qwen-14b",
        "difficulty": 40,
        "task_type": "explanation"
    },
    {
        "query": "¿Qué es unit testing?",
        "response": "**Unit testing** son pruebas automáticas de unidades individuales de código (funciones, métodos, clases).\n\n**Ventajas:**\n- Detecta bugs temprano\n- Facilita refactoring\n- Documenta comportamiento esperado\n- Aumenta confianza en el código\n\n**Framework:** pytest (Python)\n```python\n# archivo: calculadora.py\ndef sumar(a, b):\n    return a + b\n\ndef dividir(a, b):\n    if b == 0:\n        raise ValueError(\"División por cero\")\n    return a / b\n\n# archivo: test_calculadora.py\nimport pytest\nfrom calculadora import sumar, dividir\n\ndef test_sumar():\n    assert sumar(2, 3) == 5\n    assert sumar(-1, 1) == 0\n    assert sumar(0, 0) == 0\n\ndef test_dividir():\n    assert dividir(10, 2) == 5\n    assert dividir(7, 2) == 3.5\n\ndef test_dividir_por_cero():\n    with pytest.raises(ValueError):\n        dividir(10, 0)\n```\n\n**Ejecutar:**\n```bash\npytest test_calculadora.py\npytest -v  # Verbose\npytest --cov  # Con coverage\n```\n\n**Buenas prácticas:**\n- Un test por caso de uso\n- Nombres descriptivos\n- AAA pattern: Arrange, Act, Assert\n- Tests independientes (no dependen entre sí)",
        "model": "qwen-14b",
        "difficulty": 45,
        "task_type": "explanation"
    },
    
    # Preguntas conversacionales
    {
        "query": "Hola Jarvis",
        "response": "¡Hola! 👋 Soy Jarvis, tu asistente de IA. Estoy aquí para ayudarte con:\n\n- 💻 Programación y código\n- 🧠 Conceptos técnicos\n- 🐧 Comandos Linux\n- 🤖 Machine Learning e IA\n- 🔧 Debugging y testing\n- 📚 Documentación y explicaciones\n\n¿En qué puedo ayudarte hoy?",
        "model": "qwen-14b",
        "difficulty": 5,
        "task_type": "chat"
    },
    {
        "query": "¿Qué puedes hacer?",
        "response": "Puedo ayudarte con muchas cosas:\n\n**Programación:**\n- Explicar conceptos (Python, JS, algoritmos)\n- Generar código funcional\n- Debuggear problemas\n- Sugerir mejores prácticas\n\n**Técnico:**\n- Comandos Linux/terminal\n- Git, Docker, APIs\n- Testing y debugging\n- Arquitecturas de software\n\n**IA/ML:**\n- Conceptos de ML/DL\n- RAG, embeddings, LLMs\n- Frameworks (PyTorch, TensorFlow)\n\n**Capacidades especiales:**\n- 🧠 Memoria semántica (recuerdo conversaciones)\n- 🎯 Adaptación a complejidad de queries\n- 📊 Respuestas estructuradas\n- 💡 Ejemplos de código funcionales\n\n¿Qué necesitas?",
        "model": "qwen-14b",
        "difficulty": 10,
        "task_type": "chat"
    }
]


def populate_memories():
    """Poblar vectorstore con memorias iniciales"""
    print("🚀 Iniciando población de memorias iniciales...\n")
    
    # Inicializar EmbeddingManager
    print("📦 Cargando EmbeddingManager...")
    em = EmbeddingManager()
    
    # Verificar estado inicial
    initial_count = em.collection.count()
    print(f"📊 Memorias actuales en vectorstore: {initial_count}\n")
    
    # Preparar datos para add_to_memory
    texts = []
    metadatas = []
    
    # Simular timestamps variados (últimos 30 días)
    base_date = datetime.now()
    
    for i, memory in enumerate(INITIAL_MEMORIES):
        # Generar timestamp realista
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        timestamp = base_date - timedelta(days=days_ago, hours=hours_ago)
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Formato de texto para embeddings (query + response combinados)
        text = f"Usuario: {memory['query']}\nAsistente: {memory['response']}"
        texts.append(text)
        
        # Metadata completa
        metadata = {
            "query": memory['query'],
            "response": memory['response'],
            "model": memory['model'],
            "difficulty": memory['difficulty'],
            "task_type": memory['task_type'],
            "timestamp": timestamp_str,
            "tokens": len(memory['response'].split()),  # Aproximación
            "quality_score": random.uniform(0.75, 0.95)  # Todas son buenas memorias
        }
        metadatas.append(metadata)
        
        print(f"✅ [{i+1}/{len(INITIAL_MEMORIES)}] {memory['task_type']}: {memory['query'][:50]}...")
    
    # Añadir todas las memorias
    print(f"\n📥 Añadiendo {len(texts)} memorias al vectorstore...")
    success = em.add_to_memory(texts, metadatas)
    
    if success:
        final_count = em.collection.count()
        print(f"\n✅ Éxito! Memorias añadidas: {final_count - initial_count}")
        print(f"📊 Total en vectorstore: {final_count}")
        
        # Test de búsqueda
        print("\n🔍 Test de búsqueda semántica:")
        test_queries = [
            "¿Cómo ordenar una lista?",
            "Explica machine learning",
            "Comandos de git"
        ]
        
        for query in test_queries:
            context = em.get_context_for_query(
                query=query,
                max_context=3,
                min_similarity=0.5
            )
            
            num_results = context.count("Memoria #") if context else 0
            print(f"  • '{query}' → {num_results} memorias relevantes")
        
        print("\n🎉 Población de memorias completada exitosamente!")
        return True
    else:
        print("\n❌ Error al añadir memorias")
        return False


if __name__ == "__main__":
    try:
        populate_memories()
    except KeyboardInterrupt:
        print("\n⚠️  Interrumpido por usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
