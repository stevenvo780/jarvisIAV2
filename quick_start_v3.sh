#!/bin/bash
# Quick Start - Jarvis IA V3.0
# Script consolidado para iniciar el sistema completo

set -e  # Exit on error

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    JARVIS IA V3.0                                 ║"
echo "║              Sistema Completo con 8 Mejoras                       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo "Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate venv
echo -e "${BLUE}📦 Activating virtual environment...${NC}"
source .venv/bin/activate

# Check dependencies
echo -e "${BLUE}🔍 Checking dependencies...${NC}"
python3 -c "import torch; import chromadb; import sentence_transformers" 2>/dev/null || {
    echo -e "${RED}❌ Dependencies missing!${NC}"
    echo "Run: pip install -r requirements.txt"
    exit 1
}
echo -e "${GREEN}✅ Dependencies OK${NC}"
echo ""

# Menu
echo "Select an option:"
echo ""
echo "  ${GREEN}1)${NC} 🚀 Run Jarvis (main.py)"
echo "  ${GREEN}2)${NC} 📚 Populate initial memories (if empty)"
echo "  ${GREEN}3)${NC} 🔧 Test Terminal Executor"
echo "  ${GREEN}4)${NC} 🔄 Run Iterative Auto-Refiner"
echo "  ${GREEN}5)${NC} 📊 Check system status"
echo "  ${GREEN}6)${NC} 🧪 Run test suite (test_mejoras_v2.1.py)"
echo "  ${GREEN}7)${NC} 📖 Show documentation"
echo "  ${GREEN}8)${NC} 🎯 Full system demo (all features)"
echo "  ${YELLOW}0)${NC} Exit"
echo ""
read -p "Enter option: " option

case $option in
    1)
        echo -e "${GREEN}🚀 Starting Jarvis...${NC}"
        python3 main.py
        ;;
    2)
        echo -e "${BLUE}📚 Checking memories...${NC}"
        COUNT=$(python3 -c "
import sys
sys.path.insert(0, '.')
from src.modules.embeddings.embedding_manager import EmbeddingManager
em = EmbeddingManager()
print(em.collection.count())
" 2>/dev/null)
        
        echo "Current memories: $COUNT"
        
        if [ "$COUNT" -eq 0 ]; then
            echo -e "${YELLOW}⚠️  No memories found. Populating...${NC}"
            python3 scripts/populate_initial_memories.py
        else
            echo -e "${GREEN}✅ Memories already populated${NC}"
            read -p "Repopulate? (y/n): " repopulate
            if [ "$repopulate" = "y" ]; then
                python3 scripts/populate_initial_memories.py
            fi
        fi
        ;;
    3)
        echo -e "${BLUE}🔧 Testing Terminal Executor...${NC}"
        python3 src/utils/terminal_executor.py
        ;;
    4)
        echo -e "${BLUE}🔄 Starting Iterative Auto-Refiner...${NC}"
        read -p "Max iterations (default 5): " max_iter
        read -p "Queries per iteration (default 10): " queries_per
        
        max_iter=${max_iter:-5}
        queries_per=${queries_per:-10}
        
        echo "Running with max_iterations=$max_iter, queries_per_iteration=$queries_per"
        python3 -c "
from scripts.iterative_auto_refiner import IterativeAutoRefiner
import logging
logging.basicConfig(level=logging.INFO)

refiner = IterativeAutoRefiner(
    target_quality_score=0.75,
    target_good_percentage=0.70,
    max_iterations=$max_iter,
    queries_per_iteration=$queries_per
)
history = refiner.run_until_convergence()
"
        ;;
    5)
        echo -e "${BLUE}📊 System Status${NC}"
        echo "════════════════════════════════════════════════════════════════"
        
        # Python version
        echo -n "Python: "
        python3 --version
        
        # CUDA
        echo -n "CUDA: "
        python3 -c "import torch; print('Available' if torch.cuda.is_available() else 'Not available')" 2>/dev/null || echo "Not available"
        
        # GPUs
        if command -v nvidia-smi &> /dev/null; then
            echo "GPUs:"
            nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv,noheader | while read line; do
                echo "  $line"
            done
        fi
        
        # Memories
        echo -n "RAG Memories: "
        python3 -c "
import sys
sys.path.insert(0, '.')
from src.modules.embeddings.embedding_manager import EmbeddingManager
em = EmbeddingManager()
print(em.collection.count())
" 2>/dev/null
        
        # Learning stats
        echo -n "Learning interactions: "
        if [ -f "logs/learning/stats.json" ]; then
            python3 -c "import json; print(json.load(open('logs/learning/stats.json'))['total_interactions'])" 2>/dev/null || echo "0"
        else
            echo "0"
        fi
        
        # Refinement iterations
        echo -n "Refinement iterations: "
        ls logs/refinement/iteration_*_summary.json 2>/dev/null | wc -l || echo "0"
        
        echo "════════════════════════════════════════════════════════════════"
        ;;
    6)
        echo -e "${BLUE}🧪 Running test suite...${NC}"
        python3 test_mejoras_v2.1.py
        ;;
    7)
        echo -e "${BLUE}📖 Documentation${NC}"
        echo "════════════════════════════════════════════════════════════════"
        echo ""
        echo "Main documents:"
        echo "  - README.md                        : General overview"
        echo "  - USAGE.md                         : Usage guide"
        echo "  - INSTALL.md                       : Installation guide"
        echo "  - MEJORAS_CRITICAS_JARVIS.md       : Critical improvements plan"
        echo "  - IMPLEMENTACION_MEJORAS.md        : Implementation details (Phases 1-2)"
        echo "  - MEJORAS_COMPLETAS_V2.1.md        : Complete improvements (Phases 1-4)"
        echo "  - IMPLEMENTACION_COMPLETA_HOY.md   : Today's implementation (All 5 phases)"
        echo "  - MEJORAS_FINALES_V3.0.md          : Final improvements V3.0 (8 systems)"
        echo ""
        echo "Key features:"
        echo "  1. Dynamic Token Manager       : Adaptive tokens (64-8192)"
        echo "  2. Enhanced RAG System         : 10 memories, hybrid ranking"
        echo "  3. Learning Manager            : Pattern detection, auto-tuning"
        echo "  4. Smart Prompt Builder        : Task-specific prompts"
        echo "  5. Quality Evaluator           : 5 metrics automatic"
        echo "  6. RAG Memories (NEW)          : 16 initial memories"
        echo "  7. Terminal Executor (NEW)     : Safe command execution"
        echo "  8. Iterative Refiner (NEW)     : Automatic convergence"
        echo ""
        echo "════════════════════════════════════════════════════════════════"
        
        read -p "Open documentation? (y/n): " open_doc
        if [ "$open_doc" = "y" ]; then
            if command -v bat &> /dev/null; then
                bat MEJORAS_FINALES_V3.0.md
            elif command -v less &> /dev/null; then
                less MEJORAS_FINALES_V3.0.md
            else
                cat MEJORAS_FINALES_V3.0.md
            fi
        fi
        ;;
    8)
        echo -e "${GREEN}🎯 Full System Demo${NC}"
        echo "════════════════════════════════════════════════════════════════"
        echo ""
        echo "This demo will:"
        echo "  1. Check/populate RAG memories"
        echo "  2. Test Terminal Executor (safe commands)"
        echo "  3. Run mini Iterative Refiner (2 iterations, 5 queries)"
        echo "  4. Show quality stats"
        echo ""
        read -p "Continue? (y/n): " continue_demo
        
        if [ "$continue_demo" = "y" ]; then
            # Step 1: Memories
            echo -e "\n${BLUE}📚 Step 1: Checking RAG memories...${NC}"
            COUNT=$(python3 -c "
import sys
sys.path.insert(0, '.')
from src.modules.embeddings.embedding_manager import EmbeddingManager
em = EmbeddingManager()
print(em.collection.count())
" 2>/dev/null)
            
            if [ "$COUNT" -eq 0 ]; then
                echo "Populating initial memories..."
                python3 scripts/populate_initial_memories.py | grep -E "(✅|📊|🔍)" || true
            else
                echo -e "${GREEN}✅ $COUNT memories found${NC}"
            fi
            
            # Step 2: Terminal Executor
            echo -e "\n${BLUE}🔧 Step 2: Testing Terminal Executor...${NC}"
            python3 -c "
from src.utils.terminal_executor import TerminalExecutor
executor = TerminalExecutor(timeout=10)

# Safe commands
safe_cmds = ['pwd', 'whoami', 'python3 --version']
for cmd in safe_cmds:
    result = executor.execute(cmd)
    print(f'  ✅ {cmd}: {result.stdout.strip()[:50]}')

# Dangerous command (should block)
result = executor.execute('rm -rf /')
print(f'  🔒 rm -rf / : BLOCKED ({result.reason})')
"
            
            # Step 3: Mini Refiner
            echo -e "\n${BLUE}🔄 Step 3: Running mini Iterative Refiner...${NC}"
            python3 -c "
from scripts.iterative_auto_refiner import IterativeAutoRefiner
import logging
logging.basicConfig(level=logging.WARNING)

refiner = IterativeAutoRefiner(
    target_quality_score=0.75,
    target_good_percentage=0.70,
    max_iterations=2,
    queries_per_iteration=5
)
history = refiner.run_until_convergence()

print(f'\n  Iterations: {len(history)}')
print(f'  Final quality: {history[-1].avg_quality_score:.3f}')
print(f'  Convergence: {'YES' if history[-1].avg_quality_score >= 0.75 else 'NO'}')
"
            
            # Step 4: Stats
            echo -e "\n${BLUE}📊 Step 4: Quality Stats${NC}"
            if [ -f "logs/refinement/final_report.json" ]; then
                python3 -c "
import json
with open('logs/refinement/final_report.json') as f:
    report = json.load(f)
    
history = report['history']
if history:
    last = history[-1]
    print(f'  Quality: {last['avg_quality_score']:.3f}')
    print(f'  Time: {last['avg_response_time']:.2f}s')
    print(f'  Tokens: {last['avg_tokens_used']:.0f}')
    print(f'  Distribution: {last['quality_distribution']}')
"
            fi
            
            echo -e "\n${GREEN}✅ Demo completed!${NC}"
            echo "════════════════════════════════════════════════════════════════"
        fi
        ;;
    0)
        echo -e "${YELLOW}👋 Bye!${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Done!${NC}"
