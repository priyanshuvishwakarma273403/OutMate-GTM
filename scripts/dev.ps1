# Windows PowerShell developer helper script for Outmate GTM
param (
    [Parameter(Position=0)]
    [ValidateSet("install", "run", "run-mcp", "test", "lint", "format", "typecheck")]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"
$VenvPython = ".venv\Scripts\python.exe"

function Ensure-Venv {
    if (-not (Test-Path $VenvPython)) {
        Write-Host "Creating virtual environment with uv..." -ForegroundColor Cyan
        uv venv .venv
        uv pip install -e ".[dev]" --python $VenvPython
    }
}

switch ($Command) {
    "install" {
        Ensure-Venv
        Write-Host "Installing dependencies..." -ForegroundColor Green
        uv pip install -e ".[dev]" --python $VenvPython
    }
    "run" {
        Ensure-Venv
        Write-Host "Starting Outmate GTM FastAPI + MCP Server on http://127.0.0.1:8000..." -ForegroundColor Green
        & $VenvPython -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    }
    "run-mcp" {
        Ensure-Venv
        Write-Host "Starting Outmate MCP server over stdio transport..." -ForegroundColor Green
        & $VenvPython -m app.cli.main run-mcp
    }
    "test" {
        Ensure-Venv
        Write-Host "Running pytest test suite..." -ForegroundColor Green
        & ".venv\Scripts\pytest.exe" tests/ -v
    }
    "lint" {
        Ensure-Venv
        Write-Host "Running Ruff lint checks..." -ForegroundColor Green
        & ".venv\Scripts\ruff.exe" check app tests
    }
    "format" {
        Ensure-Venv
        Write-Host "Formatting code with Ruff..." -ForegroundColor Green
        & ".venv\Scripts\ruff.exe" format app tests
        & ".venv\Scripts\ruff.exe" check --fix app tests
    }
    "typecheck" {
        Ensure-Venv
        Write-Host "Running mypy type analysis..." -ForegroundColor Green
        & ".venv\Scripts\mypy.exe" app tests
    }
    default {
        Write-Host "Usage: .\scripts\dev.ps1 [install|run|run-mcp|test|lint|format|typecheck]" -ForegroundColor Yellow
    }
}
