# Makefile for JarvisIA V2
# Quick commands for development workflow

.PHONY: help install test lint format check coverage clean run

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "🤖 JarvisIA V2 - Development Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	@echo "📦 Installing dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install flake8 black isort mypy pytest pytest-cov pytest-mock pytest-asyncio bandit safety
	@echo "✅ Dependencies installed"

install-dev: install ## Install development dependencies
	@echo "📦 Installing development tools..."
	pip install pre-commit ipython jupyter
	@echo "✅ Development tools installed"

test: ## Run all tests
	@echo "🧪 Running tests..."
	pytest tests/ -v --tb=short

test-fast: ## Run only fast tests (skip slow and GPU tests)
	@echo "⚡ Running fast tests..."
	pytest tests/ -v -m "not slow and not gpu" --tb=short

test-coverage: ## Run tests with coverage report
	@echo "📊 Running tests with coverage..."
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml
	@echo "📄 Coverage report: htmlcov/index.html"

lint: ## Run linting checks (flake8)
	@echo "🔎 Running flake8..."
	flake8 src/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=120 --statistics

format: ## Auto-format code with black and isort
	@echo "🎨 Formatting code with Black..."
	black src/ tests/
	@echo "📐 Sorting imports with isort..."
	isort src/ tests/
	@echo "✅ Code formatted"

format-check: ## Check code formatting without changes
	@echo "🎨 Checking Black formatting..."
	black --check --diff src/ tests/
	@echo "📐 Checking isort..."
	isort --check-only --diff src/ tests/

type-check: ## Run type checking with mypy
	@echo "🔬 Running mypy type checker..."
	mypy src/ --ignore-missing-imports --no-strict-optional || true

check: format-check lint type-check ## Run all checks (format, lint, type)
	@echo "✅ All checks completed"

security: ## Run security scans (bandit + safety)
	@echo "🔒 Running Bandit security scan..."
	bandit -r src/ -f screen || true
	@echo "📦 Checking for vulnerable dependencies..."
	safety check || true

validate-qw: ## Validate Quick Wins implementation
	@echo "✅ Validating Quick Wins 1 & 2..."
	python validate_quick_wins.py || true
	@echo "📊 Benchmarking Async Logging (Quick Win 3)..."
	timeout 30s python benchmark_async_logging.py || true

coverage: test-coverage ## Alias for test-coverage

clean: ## Clean build artifacts and cache
	@echo "🧹 Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage coverage.xml htmlcov/ 2>/dev/null || true
	@echo "✅ Cleaned"

clean-logs: ## Clean log files
	@echo "🧹 Cleaning logs..."
	rm -rf logs/*.log 2>/dev/null || true
	@echo "✅ Logs cleaned"

clean-cache: ## Clean embedding and vectorstore caches
	@echo "🧹 Cleaning caches..."
	rm -f vectorstore/chromadb/embedding_cache.pkl 2>/dev/null || true
	@echo "✅ Caches cleaned"

run: ## Run Jarvis (main.py)
	@echo "🚀 Starting Jarvis..."
	python main.py

run-dev: ## Run Jarvis with debug logging
	@echo "🔧 Starting Jarvis (DEBUG mode)..."
	LOG_LEVEL=DEBUG python main.py

pre-commit: format lint test-fast ## Run pre-commit checks (format, lint, fast tests)
	@echo "✅ Pre-commit checks completed"

ci-local: check test-coverage validate-qw security ## Run full CI pipeline locally
	@echo "✅ Local CI completed"

install-hooks: ## Install git pre-commit hook
	@echo "🔗 Installing git pre-commit hook..."
	cp scripts/pre-commit.sh .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "✅ Git hooks installed"

docs: ## Generate documentation (placeholder)
	@echo "📚 Documentation generation not yet implemented"

upgrade-deps: ## Upgrade all dependencies to latest versions
	@echo "⬆️ Upgrading dependencies..."
	pip list --outdated
	pip install --upgrade pip
	pip install --upgrade -r requirements.txt || true
	@echo "✅ Dependencies upgraded"

info: ## Show project info
	@echo "🤖 JarvisIA V2 - Project Information"
	@echo ""
	@echo "Python version:"
	@python --version
	@echo ""
	@echo "Installed packages:"
	@pip list | grep -E '(torch|transformers|vllm|chromadb|sentence-transformers|fastapi)' || true
	@echo ""
	@echo "Project structure:"
	@tree -L 2 -I 'venv|__pycache__|*.pyc|models|vectorstore|logs|htmlcov' || ls -la
