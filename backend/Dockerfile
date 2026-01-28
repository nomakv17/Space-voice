# Production Dockerfile for SpaceVoice Backend
# Uses uv for fast dependency management

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency files first (for layer caching)
COPY pyproject.toml uv.lock README.md ./

# Install dependencies only (skip building local package)
RUN uv sync --frozen --no-dev --no-install-project

# Copy sv_internal module if present (must be in backend/ directory for Railway)
COPY sv_internal/ ./sv_internal/

# Install sv_internal
RUN uv pip install -e ./sv_internal

# Copy application code
COPY app ./app
COPY gunicorn.conf.py ./
COPY alembic.ini ./
COPY migrations ./migrations

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with gunicorn (production WSGI server)
CMD ["uv", "run", "gunicorn", "-c", "gunicorn.conf.py", "app.main:app"]
