# Minimal, secure, production-grade Docker container for Outmate GTM
FROM python:3.12-slim AS base

# Install system dependencies & security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory & environment variables
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

# Create unprivileged runtime user
RUN groupadd -g 1001 appuser && \
    useradd -u 1001 -g appuser -s /bin/bash -m appuser

# Install uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project specification files
COPY pyproject.toml README.md ./

# Install application dependencies into system Python
RUN uv pip install --system -e "."

# Copy application source code
COPY app/ ./app/

# Set ownership to unprivileged user
RUN chown -R appuser:appuser /app
USER appuser

# Expose HTTP / MCP port
EXPOSE 8000

# Health check probe against /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

# Launch FastAPI and Streamable MCP SSE application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
