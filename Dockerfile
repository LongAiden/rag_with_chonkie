# ============================================
# RAG + Knowledge Graph Application Dockerfile
# ============================================

# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY deployment/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Download spaCy model (optional, uncomment if using spaCy NER)
# RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/uploads

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "document_processing.full_pipeline_pgvector:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
