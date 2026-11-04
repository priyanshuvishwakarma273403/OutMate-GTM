.PHONY: help install run run-mcp test lint format typecheck clean

PYTHON := $(shell which python3 2>/dev/null || which python 2>/dev/null || echo python)
VENV_BIN := .venv/bin
ifeq ($(OS),Windows_NT)
	VENV_BIN := .venv/Scripts
endif

UV := $(shell which uv 2>/dev/null)

help:
	@echo "Outmate GTM — Available Commands:"
	@echo "  make install    - Install project dependencies using uv or pip"
	@echo "  make run        - Run FastAPI and MCP HTTP/SSE server (hot-reload)"
	@echo "  make run-mcp    - Run MCP server over stdio for local tools/desktop"
	@echo "  make test       - Execute pytest test suite"
	@echo "  make lint       - Run Ruff linter"
	@echo "  make format     - Check and format code with Ruff"
	@echo "  make typecheck  - Run static type analysis with mypy"
	@echo "  make clean      - Clean temporary and cache artifacts"

install:
	@if [ -n "$(UV)" ]; then \
		echo "Installing with uv..."; \
		uv pip install -e ".[dev]"; \
	else \
		echo "Installing with pip..."; \
		pip install -e ".[dev]"; \
	fi

run:
	uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

run-mcp:
	python -m app.cli.main run-mcp

test:
	pytest tests/ -v

lint:
	ruff check app tests

format:
	ruff format app tests
	ruff check --fix app tests

typecheck:
	mypy app tests

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage dist build *.egg-info

