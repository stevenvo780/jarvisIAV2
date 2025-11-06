#!/usr/bin/env python3
"""
Script para descargar modelos optimizados para Jarvis IA V2
Distribuye modelos entre GPU1 (16GB) y GPU2 (6GB)
"""

import os
import sys
from huggingface_hub import snapshot_download, login
from pathlib import Path
import argparse

# Colores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(msg):
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{msg}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.OKGREEN}✅ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKBLUE}ℹ️  {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠️  {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}❌ {msg}{Colors.ENDC}")

# Configuración de modelos
MODELS = {
    "llm_gpu1": [
        {
            "name": "Llama-3.3-70B-Instruct-AWQ",
            "repo": "casperhansen/llama-3.3-70b-instruct-awq",
            "local_dir": "models/llm/llama-3.3-70b-awq",
            "size": "~40GB",
            "vram": "14GB",
            "gpu": "GPU1",
            "description": "Modelo principal para razonamiento complejo"
        },
        {
            "name": "Qwen2.5-32B-Instruct-AWQ",
            "repo": "Qwen/Qwen2.5-32B-Instruct-AWQ",
            "local_dir": "models/llm/qwen2.5-32b-awq",
            "size": "~18GB",
            "vram": "10GB",
            "gpu": "GPU1",
            "description": "Especializado en matemáticas y código"
        },
        {
            "name": "DeepSeek-R1-Distill-Qwen-14B",
            "repo": "solidrust/DeepSeek-R1-Distill-Qwen-14B-GPTQ",
            "local_dir": "models/llm/deepseek-r1-14b-gptq",
            "size": "~8GB",
            "vram": "9GB",
            "gpu": "GPU1",
            "description": "Razonamiento paso a paso estilo Chain-of-Thought"
        }
    ],
    "llm_gpu2": [
        {
            "name": "Llama-3.2-8B-Instruct",
            "repo": "meta-llama/Llama-3.2-8B-Instruct",
            "local_dir": "models/llm/llama-3.2-8b-instruct",
            "size": "~16GB",
            "vram": "5GB (FP16)",
            "gpu": "GPU2",
            "description": "Modelo rápido para consultas simples"
        }
    ],
    "whisper": [
        {
            "name": "Whisper-Large-V3-Turbo",
            "repo": "openai/whisper-large-v3-turbo",
            "local_dir": "models/whisper/large-v3-turbo",
            "size": "~3GB",
            "vram": "2GB (INT8)",
            "gpu": "GPU2",
            "description": "ASR optimizado (convertir a CTranslate2)"
        }
    ],
    "embeddings": [
        {
            "name": "BGE-M3",
            "repo": "BAAI/bge-m3",
            "local_dir": "models/embeddings/bge-m3",
            "size": "~2GB",
            "vram": "1.5GB",
            "gpu": "GPU2/CPU",
            "description": "Embeddings multilingües para RAG"
        },
        {
            "name": "E5-Mistral-7B-Instruct",
            "repo": "intfloat/e5-mistral-7b-instruct",
            "local_dir": "models/embeddings/e5-mistral-7b",
            "size": "~15GB",
            "vram": "4GB",
            "gpu": "GPU2",
            "description": "Embeddings de alta calidad (opcional)"
        }
    ]
}

def check_disk_space():
    """Verifica espacio en disco disponible"""
    import shutil
    total, used, free = shutil.disk_usage("/")
    free_gb = free // (2**30)
    
    print_info(f"Espacio libre en disco: {free_gb} GB")
    
    if free_gb < 150:
        print_warning(f"Se recomienda tener al menos 150GB libres")
        print_warning(f"Solo tienes {free_gb}GB disponibles")
        return False
    
    print_success(f"Espacio en disco suficiente: {free_gb}GB")
    return True

def download_model(repo_id, local_dir, name, size):
    """Descarga un modelo de HuggingFace"""
    
    print_info(f"Descargando {name}...")
    print_info(f"  Repositorio: {repo_id}")
    print_info(f"  Tamaño estimado: {size}")
    print_info(f"  Destino: {local_dir}")
    
    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
            resume_download=True
        )
        print_success(f"{name} descargado correctamente")
        return True
    except Exception as e:
        print_error(f"Error descargando {name}: {str(e)}")
        return False

def convert_whisper_to_ct2(model_path, output_path):
    """Convierte modelo Whisper a CTranslate2"""
    
    print_info("Convirtiendo Whisper a CTranslate2 (INT8)...")
    
    try:
        from ctranslate2.converters import TransformersConverter
        
        converter = TransformersConverter(model_path)
        converter.convert(
            output_dir=output_path,
            quantization="int8",
            force=True
        )
        
        print_success(f"Whisper convertido a CTranslate2: {output_path}")
        return True
    except Exception as e:
        print_warning(f"No se pudo convertir Whisper: {str(e)}")
        print_info("Instala CTranslate2: pip install ctranslate2")
        return False

def main():
    parser = argparse.ArgumentParser(description="Descargar modelos para Jarvis IA V2")
    parser.add_argument("--category", choices=["llm_gpu1", "llm_gpu2", "whisper", "embeddings", "all"],
                       default="all", help="Categoría de modelos a descargar")
    parser.add_argument("--skip-existing", action="store_true",
                       help="Omitir modelos ya descargados")
    parser.add_argument("--hf-token", type=str,
                       help="Token de HuggingFace (o usa huggingface-cli login)")
    
    args = parser.parse_args()
    
    print_header("🚀 Jarvis IA V2 - Descarga de Modelos")
    
    # Login a HuggingFace si se proporciona token
    if args.hf_token:
        print_info("Autenticando en HuggingFace...")
        login(token=args.hf_token)
        print_success("Autenticado correctamente")
    
    # Verificar espacio en disco
    if not check_disk_space():
        print_warning("Continuar de todos modos? (s/n)")
        if input().lower() != 's':
            sys.exit(1)
    
    # Crear directorios base
    Path("models/llm").mkdir(parents=True, exist_ok=True)
    Path("models/whisper").mkdir(parents=True, exist_ok=True)
    Path("models/embeddings").mkdir(parents=True, exist_ok=True)
    
    # Seleccionar modelos a descargar
    if args.category == "all":
        categories = ["llm_gpu1", "llm_gpu2", "whisper", "embeddings"]
    else:
        categories = [args.category]
    
    total_models = sum(len(MODELS[cat]) for cat in categories)
    current = 0
    successful = 0
    failed = []
    
    # Descargar modelos
    for category in categories:
        print_header(f"📦 Categoría: {category.upper()}")
        
        for model in MODELS[category]:
            current += 1
            print(f"\n[{current}/{total_models}] {model['name']}")
            print(f"  GPU: {model['gpu']} | VRAM: {model['vram']}")
            print(f"  {model['description']}")
            
            # Verificar si ya existe
            if args.skip_existing and Path(model['local_dir']).exists():
                print_info("Ya existe, omitiendo...")
                successful += 1
                continue
            
            # Descargar
            if download_model(
                model['repo'],
                model['local_dir'],
                model['name'],
                model['size']
            ):
                successful += 1
                
                # Convertir Whisper si es necesario
                if category == "whisper":
                    ct2_path = model['local_dir'] + "-ct2"
                    convert_whisper_to_ct2(model['local_dir'], ct2_path)
            else:
                failed.append(model['name'])
    
    # Resumen final
    print_header("📊 Resumen de Descarga")
    print(f"Total: {total_models}")
    print_success(f"Exitosos: {successful}")
    
    if failed:
        print_error(f"Fallidos: {len(failed)}")
        for name in failed:
            print(f"  - {name}")
    
    print("\n")
    if successful == total_models:
        print_success("✨ ¡Todos los modelos descargados correctamente!")
        print_info("Próximo paso: Ejecutar benchmarks y configurar el orquestador")
    else:
        print_warning("Algunos modelos no se descargaron. Revisa los errores arriba.")
    
    # Notas importantes
    print_header("📝 Notas Importantes")
    print("1. Modelos de Llama requieren aceptar licencia en HuggingFace")
    print("2. Convierte Whisper a CTranslate2 para mejor rendimiento:")
    print("   ct2-transformers-converter --model models/whisper/large-v3-turbo \\")
    print("     --output_dir models/whisper/large-v3-turbo-ct2 --quantization int8")
    print("3. Los modelos AWQ/GPTQ ya están cuantizados (4-bit)")
    print("4. Espacio total usado: ~100-120GB")

if __name__ == "__main__":
    main()
