"""
Smart Prompt Builder - Advanced Prompt Engineering for JarvisIA V2

Construye prompts optimizados con:
- Formato estructurado de contexto RAG
- Few-shot learning automático
- Chain-of-thought para razonamiento complejo
- Instrucciones adaptativas por tarea y modelo
- Meta-prompts para auto-mejora

Author: JarvisIA Team
Version: 1.0
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime


class TaskType(Enum):
    """Tipos de tareas con diferentes estrategias de prompt"""
    CHAT = "chat"                    # Conversación casual
    QUESTION = "question"            # Pregunta factual
    EXPLANATION = "explanation"      # Explicación detallada
    CODE_GEN = "code_generation"     # Generación de código
    CODE_DEBUG = "code_debugging"    # Debug/análisis de código
    REASONING = "reasoning"          # Razonamiento paso a paso
    ANALYSIS = "analysis"            # Análisis comparativo
    CREATIVE = "creative"            # Generación creativa
    MATH = "math"                    # Problemas matemáticos


class ModelType(Enum):
    """Tipos de modelos con diferentes formatos preferidos"""
    QWEN = "qwen"
    LLAMA = "llama"
    DEEPSEEK = "deepseek"
    MISTRAL = "mistral"
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"


class SmartPromptBuilder:
    """
    Constructor inteligente de prompts con optimizaciones específicas por tarea
    
    Features:
    - Task detection automática
    - Few-shot examples del RAG
    - Chain-of-thought para razonamiento
    - Instrucciones adaptativas
    - Formato estructurado de contexto
    """
    
    # Patrones para detección de tipo de tarea
    TASK_PATTERNS = {
        TaskType.CODE_GEN: [
            r"\b(escribe|crea|genera|implementa|programa|code|write|create|implement)\b.*\b(código|code|función|function|clase|class|script)\b",
            r"```",
        ],
        TaskType.CODE_DEBUG: [
            r"\b(debug|depura|corrige|arregla|fix|error|bug)\b.*\b(código|code)\b",
            r"\b(qué está mal|what's wrong|problema con|problem with)\b",
        ],
        TaskType.REASONING: [
            r"\b(explica paso a paso|explain step by step|razona|reason|demuestra|prove)\b",
            r"\b(por qué|why|cómo funciona|how does.*work)\b.*\b(en detalle|in detail)\b",
        ],
        TaskType.ANALYSIS: [
            r"\b(compara|compare|analiza|analyze|diferencia|difference|ventajas|advantages|desventajas|disadvantages|pros|cons)\b",
            r"\bvs\b|\bversus\b",
        ],
        TaskType.MATH: [
            r"\b(calcula|calculate|resuelve|solve|ecuación|equation|integral|derivada|derivative)\b",
            r"[\+\-\*\/\=\(\)\^].*[\+\-\*\/\=]",  # Expresiones matemáticas
        ],
        TaskType.EXPLANATION: [
            r"\b(explica|explain|qué es|what is|cómo|how)\b",
        ],
    }
    
    def __init__(self, debug: bool = False):
        """
        Initialize SmartPromptBuilder
        
        Args:
            debug: Enable debug logging
        """
        self.logger = logging.getLogger("SmartPromptBuilder")
        self.debug = debug
        
        if debug:
            self.logger.setLevel(logging.DEBUG)
        
        self.logger.info("✅ SmartPromptBuilder initialized")
    
    def detect_task_type(self, query: str) -> TaskType:
        """
        Detecta el tipo de tarea desde la query
        
        Args:
            query: User query
        
        Returns:
            Detected TaskType
        """
        query_lower = query.lower().strip()
        
        # Saludos simples
        if re.match(r"^(hola|hi|hey|buenos días|buenas tardes)[\s\.\!]*$", query_lower):
            return TaskType.CHAT
        
        # Check patterns en orden de especificidad
        for task_type, patterns in self.TASK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    self.logger.debug(f"Detected task: {task_type.value}")
                    return task_type
        
        # Fallback
        return TaskType.QUESTION
    
    def detect_model_type(self, model_name: str) -> ModelType:
        """
        Detecta el tipo de modelo desde el nombre
        
        Args:
            model_name: Model name
        
        Returns:
            ModelType
        """
        name_lower = model_name.lower()
        
        if "qwen" in name_lower:
            return ModelType.QWEN
        elif "llama" in name_lower:
            return ModelType.LLAMA
        elif "deepseek" in name_lower:
            return ModelType.DEEPSEEK
        elif "mistral" in name_lower:
            return ModelType.MISTRAL
        elif "gpt" in name_lower or "openai" in name_lower:
            return ModelType.OPENAI
        elif "claude" in name_lower or "anthropic" in name_lower:
            return ModelType.CLAUDE
        elif "gemini" in name_lower or "google" in name_lower:
            return ModelType.GEMINI
        else:
            return ModelType.QWEN  # Default
    
    def extract_few_shot_examples(
        self,
        rag_context: str,
        task_type: TaskType,
        max_examples: int = 2
    ) -> List[Dict[str, str]]:
        """
        Extrae ejemplos few-shot del contexto RAG
        
        Args:
            rag_context: RAG context string
            task_type: Task type para filtrar ejemplos relevantes
            max_examples: Maximum number of examples
        
        Returns:
            List of {query, response} dicts
        """
        if not rag_context:
            return []
        
        examples = []
        
        # Parse RAG context (formato: [Memoria #N | ...]\nUsuario: ...\nAsistente: ...)
        memory_blocks = re.split(r'\[Memoria #\d+', rag_context)
        
        for block in memory_blocks[1:]:  # Skip first empty split
            # Extract Usuario and Asistente
            user_match = re.search(r'Usuario:\s*(.+?)(?=\nAsistente:|$)', block, re.DOTALL)
            asst_match = re.search(r'Asistente:\s*(.+?)$', block, re.DOTALL)
            
            if user_match and asst_match:
                user_text = user_match.group(1).strip()
                asst_text = asst_match.group(1).strip()
                
                # Filter by relevance (simple heuristic)
                if len(asst_text) > 20 and len(asst_text) < 300:  # Reasonable length
                    examples.append({
                        'query': user_text,
                        'response': asst_text
                    })
        
        # Limit to max_examples
        return examples[:max_examples]
    
    def build_system_instructions(
        self,
        task_type: TaskType,
        model_type: ModelType,
        difficulty: int
    ) -> str:
        """
        Construye instrucciones de sistema adaptadas
        
        Args:
            task_type: Type of task
            model_type: Type of model
            difficulty: Query difficulty (1-100)
        
        Returns:
            System instructions string
        """
        # Base instructions
        base = (
            "Eres Jarvis, un asistente de IA avanzado, útil, preciso y conciso. "
            "Tu objetivo es ayudar al usuario de la mejor manera posible."
        )
        
        # Task-specific instructions
        task_instructions = {
            TaskType.CHAT: (
                "\n\nPara conversaciones casuales: "
                "Sé amigable, natural y breve. Responde de forma directa."
            ),
            TaskType.CODE_GEN: (
                "\n\nPara generación de código: "
                "1. Proporciona código limpio, comentado y funcional\n"
                "2. Explica decisiones clave brevemente\n"
                "3. Usa best practices del lenguaje\n"
                "4. Formato: ```language\ncode\n```"
            ),
            TaskType.CODE_DEBUG: (
                "\n\nPara debugging de código: "
                "1. Identifica el problema específico\n"
                "2. Explica la causa\n"
                "3. Proporciona la solución corregida\n"
                "4. Sugiere cómo prevenir el error"
            ),
            TaskType.REASONING: (
                "\n\nPara razonamiento paso a paso: "
                "1. Desglosa el problema en pasos claros\n"
                "2. Explica cada paso con lógica\n"
                "3. Conecta conclusiones\n"
                "4. Verifica la respuesta final"
            ),
            TaskType.ANALYSIS: (
                "\n\nPara análisis comparativo: "
                "1. Define criterios de comparación\n"
                "2. Analiza cada opción objetivamente\n"
                "3. Destaca pros y contras\n"
                "4. Proporciona recomendación si aplica"
            ),
            TaskType.MATH: (
                "\n\nPara problemas matemáticos: "
                "1. Identifica datos y objetivo\n"
                "2. Muestra el proceso paso a paso\n"
                "3. Verifica la solución\n"
                "4. Formato: usa notación clara"
            ),
            TaskType.EXPLANATION: (
                "\n\nPara explicaciones: "
                "1. Comienza con definición clara\n"
                "2. Usa ejemplos concretos\n"
                "3. Profundiza según dificultad\n"
                "4. Resume puntos clave"
            ),
        }
        
        instructions = base + task_instructions.get(task_type, "")
        
        # Add chain-of-thought hint for complex queries
        if difficulty > 60:
            instructions += (
                "\n\n🧠 RAZONAMIENTO COMPLEJO DETECTADO:\n"
                "Piensa paso a paso antes de responder. "
                "Muestra tu razonamiento de forma clara."
            )
        
        return instructions
    
    def format_rag_context(
        self,
        rag_context: str,
        task_type: TaskType
    ) -> str:
        """
        Formatea el contexto RAG de manera estructurada
        
        Args:
            rag_context: Raw RAG context
            task_type: Task type para contexto relevante
        
        Returns:
            Formatted context string
        """
        if not rag_context:
            return ""
        
        formatted = "📚 CONTEXTO RELEVANTE DE CONVERSACIONES PREVIAS:\n\n"
        formatted += rag_context
        formatted += "\n\n---\n"
        
        return formatted
    
    def build_enriched_prompt(
        self,
        query: str,
        rag_context: str = "",
        difficulty: int = 50,
        model_name: str = "qwen-14b",
        force_task_type: Optional[TaskType] = None,
        enable_few_shot: bool = True,
        enable_cot: bool = True
    ) -> str:
        """
        Construye prompt enriquecido con todas las optimizaciones
        
        Args:
            query: User query
            rag_context: RAG context string
            difficulty: Query difficulty (1-100)
            model_name: Model name para adaptación
            force_task_type: Override task detection
            enable_few_shot: Enable few-shot examples
            enable_cot: Enable chain-of-thought hints
        
        Returns:
            Enriched prompt ready for model
        """
        # 1. Detect task and model type
        task_type = force_task_type or self.detect_task_type(query)
        model_type = self.detect_model_type(model_name)
        
        self.logger.debug(
            f"Building prompt: task={task_type.value}, "
            f"model={model_type.value}, difficulty={difficulty}"
        )
        
        # 2. Build system instructions
        system_instructions = self.build_system_instructions(
            task_type, model_type, difficulty
        )
        
        # 3. Format RAG context
        formatted_context = ""
        if rag_context:
            formatted_context = self.format_rag_context(rag_context, task_type)
        
        # 4. Extract few-shot examples (optional)
        few_shot_section = ""
        if enable_few_shot and rag_context:
            examples = self.extract_few_shot_examples(rag_context, task_type, max_examples=2)
            
            if examples:
                few_shot_section = "📋 EJEMPLOS DE INTERACCIONES SIMILARES:\n\n"
                for i, ex in enumerate(examples, 1):
                    few_shot_section += f"Ejemplo {i}:\n"
                    few_shot_section += f"Usuario: {ex['query']}\n"
                    few_shot_section += f"Asistente: {ex['response']}\n\n"
                few_shot_section += "---\n\n"
        
        # 5. Build chain-of-thought hint
        cot_hint = ""
        if enable_cot and difficulty > 60 and task_type in [
            TaskType.REASONING, TaskType.ANALYSIS, TaskType.MATH, TaskType.CODE_DEBUG
        ]:
            cot_hint = (
                "💭 INSTRUCCIONES ESPECIALES:\n"
                "Esta es una pregunta compleja. Por favor:\n"
                "1. Piensa paso a paso\n"
                "2. Muestra tu razonamiento\n"
                "3. Verifica tu conclusión\n\n"
                "---\n\n"
            )
        
        # 6. Assemble final prompt
        prompt_parts = [
            system_instructions,
            "\n\n",
        ]
        
        if formatted_context:
            prompt_parts.append(formatted_context)
        
        if few_shot_section:
            prompt_parts.append(few_shot_section)
        
        if cot_hint:
            prompt_parts.append(cot_hint)
        
        prompt_parts.extend([
            "🎯 PREGUNTA ACTUAL:\n",
            query,
        ])
        
        final_prompt = "".join(prompt_parts)
        
        if self.debug:
            self.logger.debug(f"Final prompt length: {len(final_prompt)} chars")
            self.logger.debug(f"Sections: system={bool(system_instructions)}, "
                            f"context={bool(formatted_context)}, "
                            f"few_shot={bool(few_shot_section)}, "
                            f"cot={bool(cot_hint)}")
        
        return final_prompt
    
    def get_prompt_stats(self, prompt: str) -> Dict:
        """
        Obtiene estadísticas del prompt generado
        
        Returns:
            Dict con estadísticas
        """
        return {
            "length_chars": len(prompt),
            "length_words": len(prompt.split()),
            "has_system": "Eres Jarvis" in prompt,
            "has_context": "CONTEXTO RELEVANTE" in prompt,
            "has_few_shot": "EJEMPLOS DE INTERACCIONES" in prompt,
            "has_cot": "RAZONAMIENTO COMPLEJO" in prompt or "paso a paso" in prompt,
            "sections": prompt.count("---"),
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    builder = SmartPromptBuilder(debug=True)
    
    # Test cases
    test_cases = [
        {
            "query": "Hola, ¿cómo estás?",
            "difficulty": 10,
            "rag": ""
        },
        {
            "query": "Explica paso a paso cómo funciona el algoritmo de búsqueda binaria",
            "difficulty": 70,
            "rag": "[Memoria #1 | Score: 0.85 | Dificultad: 65 | 2024-11-07]\nUsuario: ¿Qué es un algoritmo?\nAsistente: Un algoritmo es una secuencia finita de pasos bien definidos para resolver un problema."
        },
        {
            "query": "Escribe código Python para ordenar una lista de números",
            "difficulty": 55,
            "rag": ""
        },
    ]
    
    print("\n" + "="*80)
    print("SMART PROMPT BUILDER - TEST CASES")
    print("="*80 + "\n")
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST CASE {i}")
        print(f"{'='*80}")
        print(f"Query: {test['query']}")
        print(f"Difficulty: {test['difficulty']}")
        print(f"Has RAG: {bool(test['rag'])}\n")
        
        prompt = builder.build_enriched_prompt(
            query=test['query'],
            rag_context=test['rag'],
            difficulty=test['difficulty'],
            model_name="qwen-14b"
        )
        
        stats = builder.get_prompt_stats(prompt)
        
        print("GENERATED PROMPT:")
        print("-" * 80)
        print(prompt)
        print("-" * 80)
        
        print("\nSTATS:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print()
