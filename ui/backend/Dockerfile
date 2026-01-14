# Azure Cost Optimizer - Backend Dockerfile
# Multi-stage build with UV for fast package installation

# ============================================================================
# Stage 1: Builder - Install dependencies with UV
# ============================================================================
FROM python:3.12-slim AS builder

# Install uv for fast package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory for build
WORKDIR /build

# Copy project files for installation
COPY pyproject.toml ./

# Create virtual environment and install packages with UV (super fast!)
# Use --prerelease=allow to install beta packages like agent-framework
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache --prerelease=allow .

# Copy application code
COPY . ./

# ============================================================================
# Stage 2: Runtime - Minimal final image
# ============================================================================
FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install only runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    unixodbc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy the virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
WORKDIR /app
COPY --chown=nobody:nogroup . /app/

# Create static directory with proper permissions
RUN mkdir -p /app/static && chown nobody:nogroup /app/static

# Run as non-root user for security
USER nobody

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
