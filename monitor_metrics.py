#!/usr/bin/env python3
"""
Monitor de métricas del ciclo infinito:
- Total iteraciones
- Errores vs éxitos
- Uso local vs API
- Response times promedio
- GPU usage
"""
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

def get_gpu_stats():
    """Obtiene stats de GPU"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,memory.free,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split("\n")
        gpus = []
        for line in lines:
            idx, used, free, util = line.split(", ")
            gpus.append({
                "index": int(idx),
                "memory_used_mb": int(used),
                "memory_free_mb": int(free),
                "utilization_percent": int(util)
            })
        return gpus
    except:
        return []

def count_log_patterns(log_file):
    """Cuenta patrones en simple_loop.log"""
    if not Path(log_file).exists():
        return {"iterations": 0, "errors": 0, "api_calls": 0, "local_calls": 0}
    
    try:
        with open(log_file, "rb") as f:
            content = f.read().decode("utf-8", errors="ignore")
        
        iterations = content.count("[")  # Cada "[N]" es una iteración
        errors = content.count("ERROR") + content.count("Error")
        api_calls = content.count("api.openai") + content.count("generativeai")
        local_calls = content.count("qwen") + content.count("vllm")
        
        return {
            "iterations": iterations,
            "errors": errors,
            "api_calls": api_calls,
            "local_calls": local_calls
        }
    except:
        return {"iterations": 0, "errors": 0, "api_calls": 0, "local_calls": 0}

def main():
    """Loop principal de monitoreo"""
    log_file = "/datos/repos/Personal/jarvisIAV2/simple_loop.log"
    metrics_file = "/datos/repos/Personal/jarvisIAV2/artifacts/metrics_realtime.json"
    
    print("🔍 Monitoring infinite loop...")
    
    while True:
        stats = count_log_patterns(log_file)
        gpus = get_gpu_stats()
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "loop": stats,
            "gpus": gpus
        }
        
        # Guardar métricas
        Path(metrics_file).parent.mkdir(parents=True, exist_ok=True)
        with open(metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)
        
        # Print resumen
        success_rate = 0
        if stats["iterations"] > 0:
            success_rate = (1 - stats["errors"] / stats["iterations"]) * 100
        
        local_ratio = 0
        total_calls = stats["api_calls"] + stats["local_calls"]
        if total_calls > 0:
            local_ratio = (stats["local_calls"] / total_calls) * 100
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
              f"Iter:{stats['iterations']} | "
              f"Success:{success_rate:.1f}% | "
              f"Local:{local_ratio:.1f}% | "
              f"GPU0:{gpus[0]['memory_used_mb']}MB used" if gpus else "GPU0:N/A")
        
        time.sleep(30)  # Update cada 30s

if __name__ == "__main__":
    main()
