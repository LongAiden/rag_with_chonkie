# ============================================
# RAG + Knowledge Graph Application Dockerfile
# FAST BUILD VERSION - Uses pre-built base image
# ============================================
#
# FIRST TIME SETUP (run once, ~10 min):
#   docker build -f deployment/Dockerfile.base -t rag_base:latest .
#
# SUBSEQUENT BUILDS (fast, ~30 sec):
#   docker compose build app
# ============================================

# Stage 1: Use pre-built base with ML dependencies
FROM rag_base:latest AS builder

WORKDIR /build

# Install only the lighter dependencies (fast)
COPY deployment/requirements.txt .
RUN pip install --prefer-binary -r requirements.txt

# Stage 2: runtime image stays lean
FROM python:3.11-slim

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
