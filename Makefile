# Highlight MCP Server - Makefile
# Python-based MCP server for CAST Highlight API

.PHONY: all install dev run test lint lint-fix format quality clean help test-api hooks

# Default target
all: quality

# ============================================================================
# SETUP
# ============================================================================

## Install dependencies in virtual environment
install:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"

## Initial project setup
setup: install hooks
	@echo "Setting up project..."
	@test -f .env || cp .env.example .env
	@echo "Setup complete. Edit .env with your CAST Highlight credentials."

## Install pre-commit hooks (shift-left on linting)
hooks:
	@.venv/bin/pip install pre-commit -q
	@.venv/bin/pre-commit install
	@echo "Pre-commit hooks installed. Lint/format runs automatically on commit."

# ============================================================================
# DEVELOPMENT
# ============================================================================

## Run MCP server
run:
	.venv/bin/highlight-mcp

## Run server (alias)
dev: run

## Test API connection
test-api:
	.venv/bin/python scripts/test_api.py

# ============================================================================
# TESTING
# ============================================================================

## Run all tests
test:
	.venv/bin/pytest tests/ -v

## Run tests with coverage
test-coverage:
	.venv/bin/pytest tests/ -v --cov=src/highlight_mcp --cov-report=term-missing

# ============================================================================
# CODE QUALITY
# ============================================================================

## Lint code
lint:
	.venv/bin/ruff check src/ tests/

## Fix linting issues
lint-fix:
	.venv/bin/ruff check --fix src/ tests/

## Format code
format:
	.venv/bin/ruff format src/ tests/

## Run all quality checks
quality: lint
	@echo "Quality checks passed"

## Run quality checks with fixes
quality-fix: lint-fix format

# ============================================================================
# CLEANUP
# ============================================================================

## Clean build artifacts
clean:
	rm -rf .venv dist *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ============================================================================
# HELP
# ============================================================================

## Show this help
help:
	@echo "Highlight MCP Server - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install dependencies in venv"
	@echo "  make setup          Initial project setup (includes hooks)"
	@echo "  make hooks          Install pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  make run            Run MCP server"
	@echo "  make test-api       Test API connection"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run all tests"
	@echo "  make test-coverage  Run tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           Run ruff linter"
	@echo "  make lint-fix       Fix linting issues"
	@echo "  make format         Format code with ruff"
	@echo "  make quality        Run all quality checks"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          Clean build artifacts"
