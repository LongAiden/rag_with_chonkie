# ============================================
# RAG + Knowledge Graph Application Dockerfile
# ============================================

# Stage 1: build Python environment with cached dependencies
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Install build deps once in builder
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
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
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Stage 2: runtime image stays lean
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Runtime dependencies only (no compilers)
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy prebuilt virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code last to maximize cache hits
COPY . .

# Required directories for runtime state
RUN mkdir -p /app/data /app/logs /app/uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use reload only in dev-compose; production image stays leaner
CMD ["uvicorn", "document_processing.full_pipeline_pgvector:app", "--host", "0.0.0.0", "--port", "8000"]
