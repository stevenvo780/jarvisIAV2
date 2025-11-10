#!/usr/bin/env bash
# Monitor VRAM y limpia procesos zombie cada 60s

while true; do
    gpu0_free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
    
    if [ "$gpu0_free" -lt 8000 ]; then
        echo "[$(date '+%H:%M:%S')] GPU0 baja memoria: ${gpu0_free}MB. Limpiando zombies..."
        pkill -9 -f "vllm|EngineCore|ray" 2>/dev/null
        sleep 2
    fi
    
    sleep 60
done
