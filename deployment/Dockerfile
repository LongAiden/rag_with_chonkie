# ============================================
# RAG + Knowledge Graph Application Dockerfile
# Multi-stage build for optimal caching
# ============================================

# Stage 1: Base with heavy ML dependencies (Cached)
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        curl \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv $VIRTUAL_ENV

# Install heavy ML packages (this is the slow part - less frequent changes)
RUN pip install --upgrade pip wheel setuptools && \
    pip install --prefer-binary \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        "torch>=2.3.1,<2.6.0" \
        "sentence-transformers>=3.0.0" \
        "spacy>=3.7.0" \
        "spacy-transformers>=1.3.0" \
        "numpy>=2.0.0,<3.0" \
        "scipy>=1.10.0,<1.15.0"

# Download spaCy model
RUN python -m spacy download en_core_web_sm --quiet || true

# Stage 2: Builder for application dependencies
FROM base AS builder

WORKDIR /build

# Install only the lighter dependencies (fast, changes more often)
COPY deployment/requirements.txt .
RUN pip install --prefer-binary -r requirements.txt

# Stage 3: Runtime image (stays lean)
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

WORKDIR /app

# Runtime dependencies only (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
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
