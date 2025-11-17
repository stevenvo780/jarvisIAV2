#!/bin/bash
# Script de validación para funcionalidad de voz de Jarvis

echo "=================================================="
echo "🎤 Validación de Sistema de Voz - Jarvis AI"
echo "=================================================="
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para validar endpoint
validate_endpoint() {
    local endpoint=$1
    local method=$2
    local description=$3
    
    echo -n "Testing ${description}... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8091${endpoint}")
    else
        response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:8091${endpoint}" \
            -H "Content-Type: application/json" \
            -d '{"test": true}')
    fi
    
    if [ "$response" = "200" ] || [ "$response" = "422" ]; then
        echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $response)"
        return 1
    fi
}

# Verificar servidor
echo "1. Verificando servidor web..."
if curl -s http://localhost:8091/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Servidor activo en puerto 8091${NC}"
else
    echo -e "${RED}✗ Servidor no responde. Iniciando...${NC}"
    cd /datos/repos/Personal/jarvisIAV2
    python3 start_web.py --port 8091 > /tmp/jarvis_web.log 2>&1 &
    echo "Esperando 10 segundos para inicialización..."
    sleep 10
    
    if curl -s http://localhost:8091/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Servidor iniciado correctamente${NC}"
    else
        echo -e "${RED}✗ Error al iniciar servidor${NC}"
        echo "Ver logs: tail -f /tmp/jarvis_web.log"
        exit 1
    fi
fi
echo ""

# Validar endpoints
echo "2. Validando endpoints de API..."
validate_endpoint "/api/status" "GET" "Status endpoint"
validate_endpoint "/api/voice/config" "GET" "Voice config endpoint"
validate_endpoint "/api/voice/settings" "POST" "Voice settings endpoint"
echo ""

# Verificar archivos del frontend
echo "3. Verificando archivos del frontend..."
FILES=(
    "/datos/repos/Personal/jarvisIAV2/src/web/templates/index.html"
    "/datos/repos/Personal/jarvisIAV2/src/web/api.py"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file (no encontrado)"
    fi
done
echo ""

# Verificar contenido de index.html
echo "4. Verificando implementación de voz en frontend..."
VOICE_FEATURES=(
    "SpeechRecognition|webkitSpeechRecognition"
    "speechSynthesis"
    "toggleVoiceMode"
    "toggleTTS"
    "activateCommandMode"
    "WAKE_WORD"
)

html_file="/datos/repos/Personal/jarvisIAV2/src/web/templates/index.html"
all_features_found=true

for feature in "${VOICE_FEATURES[@]}"; do
    if grep -q "$feature" "$html_file"; then
        echo -e "${GREEN}✓${NC} Función encontrada: $feature"
    else
        echo -e "${RED}✗${NC} Función NO encontrada: $feature"
        all_features_found=false
    fi
done
echo ""

# Test de configuración de voz
echo "5. Probando configuración de voz..."
voice_config=$(curl -s http://localhost:8091/api/voice/config)
if echo "$voice_config" | grep -q "wake_word"; then
    echo -e "${GREEN}✓ Configuración de voz disponible${NC}"
    echo "$voice_config" | jq '.' 2>/dev/null || echo "$voice_config"
else
    echo -e "${RED}✗ Error al obtener configuración${NC}"
fi
echo ""

# Resumen
echo "=================================================="
echo "📊 Resumen de Validación"
echo "=================================================="

if [ "$all_features_found" = true ]; then
    echo -e "${GREEN}✅ Todas las funcionalidades de voz están implementadas${NC}"
else
    echo -e "${YELLOW}⚠️  Algunas funcionalidades no se encontraron${NC}"
fi

echo ""
echo "🌐 Para probar la interfaz web, abre:"
echo "   http://localhost:8091"
echo ""
echo "📖 Instrucciones completas en:"
echo "   /datos/repos/Personal/jarvisIAV2/artifacts/voice_test_instructions.md"
echo ""
echo "🎤 Pruebas manuales recomendadas:"
echo "   1. Abre el navegador (Chrome o Edge)"
echo "   2. Acepta permisos del micrófono"
echo "   3. Haz clic en botón '🎤 Voz'"
echo "   4. Di 'Jarvis' en voz alta"
echo "   5. Haz una pregunta cuando escuches 'Sí, dime'"
echo "   6. Verifica respuesta visual + auditiva"
echo ""
echo "=================================================="
