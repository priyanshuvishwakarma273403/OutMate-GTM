# Contributing to Outmate GTM

Thank you for your interest in contributing to **Outmate GTM**. As an enterprise AI research and decision-maker intelligence platform, we maintain strict architectural separation, rigorous typing, high test coverage, and security-first engineering standards.

---

## 1. Code Standards & Architectural Rules

1. **Strict Layer Separation**:
   - **Domain Layer (`app/domain/`)**: Pure Pydantic models only. Never import external provider SDKs (OpenAI, Nango, MCP SDK) inside domain models.
   - **Service Layer (`app/services/`)**: Implements business and research logic. Services must be protocol-agnostic and never accept FastAPI `Request` objects or MCP types directly.
   - **Protocol Layer (`app/mcp/`)**: Implements tool registration, schema translation, and transport. Must dispatch to shared services.
   - **Integration Layer (`app/integrations/`)**: Encapsulates external APIs (Nango, search engines). Keeps credentials and token handling isolated.

2. **No Fake Implementations**:
   - In Phase 1 foundation, methods without live backend services raise `NotImplementedError` or return empty data structures. Never return fabricated sample data disguised as real intelligence.

3. **No Hardcoded Credentials**:
   - All secrets, tokens, and model identifiers must be loaded from `AppSettings` via environment variables.

4. **Type Hints & Static Analysis**:
   - Every function and method must be fully type-annotated.
   - All code must pass `mypy` in strict configuration and `ruff check`.

---

## 2. Development Workflow

### Prerequisites
- Python 3.11+ (Python 3.12 recommended)
- `uv` (recommended) or `pip`
- Git

### Initial Setup
```bash
# Clone the repository
git clone https://github.com/your-org/outmate-gtm.git
cd outmate-gtm

# Copy environment template
cp .env.example .env

# Create virtual environment and install dev dependencies
uv venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

uv pip install -e ".[dev]"
```

---

## 3. Quality Checks Before Committing

Always execute the following checks prior to submitting a pull request:

```bash
# 1. Run full test suite
pytest tests/ -v

# 2. Run Ruff linter
ruff check app tests

# 3. Verify code formatting
ruff format --check app tests

# 4. Run Mypy static type checker
mypy app tests
```

---

## 4. Branching Strategy

- `main`: Production-ready release branch.
- `develop`: Ongoing integration branch.
- Feature branches: `feat/<feature-name>` (e.g. `feat/exa-search-integration`).
- Fix branches: `fix/<bug-name>` (e.g. `fix/mcp-auth-token-validation`).

---

## 5. Pull Request Guidelines

1. Ensure all new public methods have docstrings explaining inputs, outputs, and exceptions raised.
2. Provide unit tests for new domain models, services, and integration clients.
3. Provide contract tests for any added or modified MCP tools.
4. Keep PRs scoped to a single capability or architectural improvement.
