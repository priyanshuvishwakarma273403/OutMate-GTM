#!/usr/bin/env bash
# macOS / Linux developer helper script for Outmate GTM
set -euo pipefail

CMD="${1:-help}"
VENV_PYTHON=".venv/bin/python"

ensure_venv() {
    if [ ! -f "$VENV_PYTHON" ]; then
        echo "Creating virtual environment with uv..."
        uv venv .venv
        uv pip install -e ".[dev]" --python "$VENV_PYTHON"
    fi
}

case "$CMD" in
    install)
        ensure_venv
        echo "Installing dependencies..."
        uv pip install -e ".[dev]" --python "$VENV_PYTHON"
        ;;
    run)
        ensure_venv
        echo "Starting Outmate GTM FastAPI + MCP Server on http://127.0.0.1:8000..."
        "$VENV_PYTHON" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
        ;;
    run-mcp)
        ensure_venv
        echo "Starting Outmate MCP server over stdio..."
        "$VENV_PYTHON" -m app.cli.main run-mcp
        ;;
    test)
        ensure_venv
        echo "Running pytest test suite..."
        .venv/bin/pytest tests/ -v
        ;;
    lint)
        ensure_venv
        echo "Running Ruff lint checks..."
        .venv/bin/ruff check app tests
        ;;
    format)
        ensure_venv
        echo "Formatting code with Ruff..."
        .venv/bin/ruff format app tests
        .venv/bin/ruff check --fix app tests
        ;;
    typecheck)
        ensure_venv
        echo "Running mypy type analysis..."
        .venv/bin/mypy app tests
        ;;
    *)
        echo "Usage: ./scripts/dev.sh [install|run|run-mcp|test|lint|format|typecheck]"
        exit 1
        ;;
esac
