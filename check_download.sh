#!/bin/bash
# Script para verificar el progreso de la descarga del modelo

MODEL_DIR="models/llm/llama-3.3-70b-awq"

echo "🔍 Verificando descarga de Llama-3.3-70B-AWQ..."
echo ""

if [ ! -d "$MODEL_DIR" ]; then
    echo "❌ Directorio $MODEL_DIR no existe todavía"
    echo "⏳ La descarga aún no ha iniciado o está iniciando..."
    exit 0
fi

echo "📁 Directorio: $MODEL_DIR"
echo ""

# Contar archivos descargados
TOTAL_FILES=$(ls -1 "$MODEL_DIR" 2>/dev/null | wc -l)
echo "📦 Archivos descargados: $TOTAL_FILES"
echo ""

# Mostrar tamaño actual
CURRENT_SIZE=$(du -sh "$MODEL_DIR" 2>/dev/null | cut -f1)
echo "💾 Tamaño actual: $CURRENT_SIZE / ~40GB"
echo ""

# Listar archivos .safetensors (los más grandes)
echo "📄 Archivos safetensors:"
ls -lh "$MODEL_DIR"/*.safetensors 2>/dev/null | awk '{print "  " $9 " - " $5}' || echo "  Ninguno todavía"
echo ""

# Verificar archivos de configuración
echo "⚙️  Archivos de configuración:"
for file in config.json tokenizer_config.json generation_config.json; do
    if [ -f "$MODEL_DIR/$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ⏳ $file (pendiente)"
    fi
done
echo ""

# Contar cuántos de los 9 archivos safetensors están completos
SAFETENSORS_COUNT=$(ls -1 "$MODEL_DIR"/model-*.safetensors 2>/dev/null | wc -l)
echo "🎯 Progreso: $SAFETENSORS_COUNT/9 archivos safetensors"

if [ "$SAFETENSORS_COUNT" -eq 9 ]; then
    echo ""
    echo "🎉 ¡Descarga completa!"
    echo ""
    echo "✅ Ahora puedes usar el modelo ejecutando:"
    echo "   python main.py --query 'Tu pregunta'"
else
    echo ""
    echo "⏳ Descarga en progreso... ($((SAFETENSORS_COUNT * 100 / 9))% completado)"
    echo ""
    echo "💡 Ejecuta este script nuevamente para ver el progreso actualizado"
fi
