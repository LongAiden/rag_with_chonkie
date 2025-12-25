# ============================================
# RAG + Knowledge Graph Application Dockerfile
# OPTIMIZED VERSION
# ============================================

ARG PYTHON_VERSION=3.11

# Stage 1: build Python environment with cached dependencies
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=0 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Install build deps once in builder
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        git \
        curl \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv $VIRTUAL_ENV

WORKDIR /build
COPY deployment/requirements.txt .

# Cache pip downloads between builds for faster Windows/WSL iterations
ARG PYTORCH_INDEX=https://download.pytorch.org/whl/cpu
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --extra-index-url ${PYTORCH_INDEX} \
    --use-pep517 \
    --prefer-binary \
    -r requirements.txt

# Download spaCy model at build time for faster runtime startup
RUN python -m spacy download en_core_web_sm --quiet || echo "spaCy model download skipped"

# Stage 2: runtime image stays lean
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

WORKDIR /app

# Runtime dependencies only (no compilers)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy prebuilt virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code by module for better caching on code changes
COPY api/ ./api/
COPY ingestion/ ./ingestion/
COPY retrieval/ ./retrieval/
COPY models/ ./models/
COPY graph_processing/ ./graph_processing/
COPY worker/ ./worker/
COPY config/ ./config/
COPY migrations/ ./migrations/

# Required directories for runtime state
RUN mkdir -p /app/data /app/logs /app/uploads

# Security: Run as non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the FastAPI application using uvicorn
# Note: --reload is not used in production for better performance
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
