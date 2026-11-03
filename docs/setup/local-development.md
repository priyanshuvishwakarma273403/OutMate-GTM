# Outmate GTM — Local Development Guide

This guide provides step-by-step setup instructions for both **Windows PowerShell** and **macOS / Linux** environments.

---

## 1. Prerequisites

- **Python**: Version 3.11 or 3.12 installed and added to `PATH`.
- **uv** (recommended for ultra-fast packaging) or standard `pip`.
- **Git**
- **curl** (for endpoint testing)

---

## 2. Windows PowerShell Setup

### Step 1: Clone Repository & Create Virtual Environment
Open Windows PowerShell (Run as standard user):

```powershell
# Clone the repository
git clone https://github.com/your-org/outmate-gtm.git
cd "d:\Outmate GTM"

# Create virtual environment using uv
uv venv .venv

# Activate the virtual environment
.venv\Scripts\Activate.ps1
```

*(If script execution is disabled in PowerShell, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`)*

### Step 2: Install Project in Editable Mode with Dev Dependencies
```powershell
uv pip install -e ".[dev]" --python .venv\Scripts\python.exe
```

### Step 3: Configure Environment Variables
```powershell
Copy-Item .env.example .env
```
Open `.env` and set your preferred keys (e.g. `OPENROUTER_API_KEY` for Mode A).

### Step 4: Run Development Commands via Helper Script
A PowerShell helper script is provided in `scripts/dev.ps1`:

```powershell
# Run the FastAPI + MCP SSE Server with hot reload
.\scripts\dev.ps1 run

# Run tests
.\scripts\dev.ps1 test

# Run Ruff linter
.\scripts\dev.ps1 lint

# Format code
.\scripts\dev.ps1 format

# Run static type checking with Mypy
.\scripts\dev.ps1 typecheck
```

---

## 3. macOS / Linux Setup

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/your-org/outmate-gtm.git
cd outmate-gtm

# Create virtual environment using uv
uv venv .venv
source .venv/bin/activate
```

### Step 2: Install Project & Dev Dependencies
```bash
uv pip install -e ".[dev]"
```

### Step 3: Configure Environment Variables
```bash
cp .env.example .env
```

### Step 4: Run Development Commands via Makefile or Helper Script
```bash
# Using Makefile
make run        # Starts server on http://127.0.0.1:8000
make test       # Executes pytest test suite
make lint       # Executes Ruff linter
make format     # Checks and formats code
make typecheck  # Executes mypy

# Or using the shell helper script:
./scripts/dev.sh run
./scripts/dev.sh test
./scripts/dev.sh lint
```

---

## 4. Verifying Application Health

When the server is running on `http://127.0.0.1:8000`:

```bash
# 1. Check process liveness
curl http://127.0.0.1:8000/health

# 2. Check subsystem readiness
curl http://127.0.0.1:8000/ready

# 3. Interactive OpenAPI documentation
# Open your browser to: http://127.0.0.1:8000/docs
```

---

## 5. Running the MCP Server Locally (stdio)

To connect Outmate tools directly to local desktop agents (such as Claude Desktop):

```bash
# Windows
.venv\Scripts\python.exe -m app.cli.main run-mcp

# macOS / Linux
.venv/bin/python -m app.cli.main run-mcp
```
