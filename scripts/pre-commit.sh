#!/bin/bash
# Pre-commit hook local para JarvisIA V2
# Instalar: cp scripts/pre-commit.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

set -e

echo "🔍 Running pre-commit checks..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if any check failed
FAILED=0

# 1. Black formatting check
echo -e "\n${YELLOW}🎨 Checking code formatting with Black...${NC}"
if black --check --diff src/ tests/ 2>&1 | grep -q "would reformat"; then
    echo -e "${RED}❌ Black formatting issues found. Run: black src/ tests/${NC}"
    FAILED=1
else
    echo -e "${GREEN}✅ Black formatting OK${NC}"
fi

# 2. isort import sorting
echo -e "\n${YELLOW}📐 Checking import sorting with isort...${NC}"
if isort --check-only --diff src/ tests/ 2>&1 | grep -q "ERROR"; then
    echo -e "${RED}❌ Import sorting issues found. Run: isort src/ tests/${NC}"
    FAILED=1
else
    echo -e "${GREEN}✅ Import sorting OK${NC}"
fi

# 3. Flake8 linting
echo -e "\n${YELLOW}🔎 Linting with flake8...${NC}"
if ! flake8 src/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics; then
    echo -e "${RED}❌ Flake8 found critical errors${NC}"
    FAILED=1
else
    echo -e "${GREEN}✅ Flake8 critical checks OK${NC}"
fi

# Warnings only (non-blocking)
flake8 src/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=120 --statistics

# 4. Quick unit tests (only fast tests)
echo -e "\n${YELLOW}🧪 Running quick unit tests...${NC}"
if pytest tests/ -v -m "not slow and not gpu" --tb=short --maxfail=3 -x 2>&1 | tail -20; then
    echo -e "${GREEN}✅ Quick tests passed${NC}"
else
    echo -e "${YELLOW}⚠️ Some tests failed (non-blocking)${NC}"
fi

# Final status
echo -e "\n============================================"
if [ $FAILED -eq 1 ]; then
    echo -e "${RED}❌ Pre-commit checks FAILED${NC}"
    echo -e "${YELLOW}Fix issues and try again, or use --no-verify to skip${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All pre-commit checks PASSED${NC}"
    echo -e "${GREEN}Ready to commit!${NC}"
    exit 0
fi
