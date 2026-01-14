# 🚀 RAG LlamaIndex with pgvector

A production-ready Retrieval-Augmented Generation (RAG) system built with FastAPI, PostgreSQL + pgvector, and Chonkie for semantic chunking.

## 📋 Installation & Setup

### 1. Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) installed
- 8GB+ available RAM
- Git

### 2. Quick Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd rag_with_llama

# 2. Create environment file
cp .env.example .env

# 3. Edit .env with your API keys
# Required: GOOGLE_API_KEY
# Optional: LOGFIRE_WRITE_TOKEN, APP_ACCESS_PASSWORD
nano .env  # or use your preferred editor

# 4. Build and run all services
docker compose up --build

# Access the application at:
# - API: http://localhost:8000
# - Health Check: http://localhost:8000/health
# - pgAdmin (optional): http://localhost:5050
```

**Platform-Specific Notes:**
- **Mac**: Works on both Intel and Apple Silicon (M1/M2/M3). Ensure Docker Desktop has 8GB+ memory allocated in Settings → Resources
- **Windows**: WSL2 backend recommended. Use `build.bat` for optimized builds
- **Linux**: Native performance (fastest). Use `./build.sh` for optimized builds

**Stopping Services:**
```bash
docker compose down
```

**Rebuilding After Changes:**
```bash
# Code changes only (fast - ~30 seconds)
docker compose restart app celery_worker

# Dependency changes (slower - ~3-5 minutes)
docker compose up --build
```

## 📁 Project Structure

```
rag_llama_index/
├── api/                          # FastAPI application
│   ├── app.py                   # Main entry point
│   ├── routes/                  # API routes
│   └── templates.py             # Web UI templates
│
├── deployment/                   # Setup & configuration
│   ├── .env.example             # Environment template
│   └── setup.sh                 # Automated setup script
│
├── docs/                         # Sample documents
│   └── llama2.pdf               # Test PDF file
│
├── ingestion/                    # Data ingestion pipeline
│   ├── chunking/                # Chunking strategies (Token, Recursive, Semantic)
│   │   └── chunker_factory.py
│   ├── embedding/               # Vector embedding generation
│   ├── processors/              # File processors (PDF, etc.)
│   └── pipeline.py              # Ingestion pipeline orchestration
│
├── models/                       # Data schemas
│   └── models.py                # Pydantic models
│
└── tests/                        # Comprehensive testing suite
    ├── unit/                    # Unit tests
    └── integration/             # Integration tests
```

## 🔧 Main Components

### `ingestion/chunking/chunker_factory.py`
**Purpose**: Centralized factory for creating text chunkers
- Supports **Token**, **Recursive**, and **Semantic** chunking strategies
- **Adaptive Selection**: Automatically uses simpler strategies for large valid files to ensure performance
- **Validation**: Enforces `chunk_size > chunk_overlap` constraints

### `ingestion/embedding`
**Purpose**: Vector embedding generation and database storage
- **Classes**:
  - `EmbeddingGenerator`: Creates embeddings using SentenceTransformers
  - `VectorStore`: Manages pgvector database operations
  - `ChunkEmbeddingPipeline`: End-to-end document processing

### `api/app.py`
**Purpose**: Main FastAPI application with web interface

<img src="./images/fastapi.png" alt="FastAPI Interface" width="600">

- **Key Endpoints**:
  - `GET /` - Web UI for upload/search
  - `POST /upload` - Document processing
  - `POST /query` - Document search API
  - `GET /stats` - Database statistics
- **Features**:
  - Multi-table support
  - LLM integration (Gemini)
  - Parameter validation
  - Error handling

### `models/models.py`
**Purpose**: Data models and API schemas
- `SupportedFileType` - File type enum
- `FileValidationResult` - Validation response
- `QueryRequest` - Search parameters
- `UploadResponse` - Upload response

## 🚀 Usage

### 1. Access the Application

After running `docker compose up`, access:
- Web UI: `http://localhost:8000`
- FastAPI Swagger UI: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`
- pgAdmin (optional): `http://localhost:5050` (start with `docker compose --profile dev up`)

### 2. Web Interface Usage
1. **Upload Documents**: Select PDF/TXT files, configure chunking parameters
    <img src="./images/home_screen.png" alt="Home Screen" width="600">

2. **Search Documents**: Enter queries, adjust similarity thresholds
    <img src="./images/query.png" alt="Query Interface" width="600">

3. **Search Results**: Show answers and relevant sources + score with rerank
    <img src="./images/nltk_question.png" alt="Search Results" width="600">

    <img src="./images/rerank_result.png" alt="Sources" width="600"> 

    <img src="./images/metadata_rerank.png" alt="Document Metadata" width="400">

4. **Monitor System**: View stats and health status

    <img src="./images/health_status.png" alt="Health Status" width="600">
    <img src="./images/database.png" alt="Database Statistics" width="600">

### 3. API Usage Examples

**Upload Document:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@document.pdf" \
  -F "chunk_size=512" \
  -F "table_name=documents"
```

**Search Documents:**
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "limit": 5}'
```

### 4. View Logs

**Application logs:**
```bash
docker compose logs -f app
```

**Celery worker logs:**
```bash
docker compose logs -f celery_worker
```

**All services:**
```bash
docker compose logs -f
```

### 5. Logfire Usage:
- Use Logfire to log steps from end to end
    <img src="./images/logfire_example.png" alt="Logfire" width="600">

- Add Step for logging ReRank if the number of references >= 5
    <img src="./images/rerank_logfire.png" alt="Logfire Rerank" width="600">

## ⚙️ Configuration

### Environment Variables
- `POSTGRES_USER/PASSWORD/DB` - Database credentials
- `GOOGLE_API_KEY` - For Gemini LLM integration
- `DB_HOST/PORT` - Database connection

### Parameters
- **Chunk Size**: 128-2048 tokens (default: 512)
- **Similarity Threshold**: 0.1-0.9 (default: 0.5)
- **Embedding Model**: all-MiniLM-L6-v2 (384 dimensions)

## 🔍 System Features

- **Semantic Chunking**: Intelligent text splitting with Chonkie
- **Vector Search**: High-performance pgvector similarity search
- **Hybrid Retrieval**: Combines vector embeddings with BM25 keyword matching for superior accuracy
- **Reranking Pipeline**: Advanced relevance scoring to surface the most pertinent results
- **File Validation**: Security checks and size limits
- **Multi-table Support**: Organize documents by categories
- **LLM Integration**: Smart responses with Gemini
- **Web Interface**: Modern, responsive UI
- **API Access**: RESTful endpoints for automation
- **Logfire Intergration**: Uisng Logfire for logging and monitoring

## 🛠️ Development Status

✅ **Completed**:
- Chunking and embedding pipeline
- Vector storage with PostgreSQL
- Using BM25 to rerank retrieve documents
- Gemini integration for retrieval
- FastAPI web interface
- Logfire setup
- Organized modular structure
- Comprehensive testing suite

📋 **Todo**:
- Advanced chunking strategies
- Multi-modal document support
- Caching and performance optimization

## 🐛 Troubleshooting

**Services Not Starting:**
```bash
# Check service status
docker compose ps

# View logs for specific service
docker compose logs postgres
docker compose logs app

# Restart all services
docker compose down
docker compose up
```

**Port Conflicts:**
```bash
# Check what's using port 8000
lsof -i :8000

# Change port in docker-compose.yml
# Edit ports section: "8001:8000" instead of "8000:8000"
```

**Database Issues:**
```bash
# Reset database
docker compose down -v  # Warning: This deletes all data
docker compose up --build
```

**Clean Rebuild:**
```bash
# Remove all containers, volumes, and images
docker compose down -v
docker system prune -a
docker compose up --build
```

## ⚠️ Known Issues

### Pydantic AI + Google Gemini `additionalProperties` Warning

**Warning Message:**
```
UserWarning: `additionalProperties` is not supported by Gemini; it will be removed from the tool JSON schema.
```

**What it means:**
- Google's Gemini API doesn't support `additionalProperties` in JSON schemas
- This affects Pydantic models with `dict[str, Any]` or `Dict[str, Any]` fields (like the `metadata` field in `SimpleRAGResponse`)
- Pydantic AI automatically removes these properties and warns you

**Impact on your application:**
- ✅ **Functionality works** - No breaking issues
- ⚠️ **Metadata fields will be empty** when returned from Gemini LLM
- 📝 **Fallback responses still populate metadata** in error scenarios

**Related Models Affected:**
- `SimpleRAGResponse.metadata` field (used for LLM responses)
- Any custom Pydantic models with `dict` type fields

**Status:**
- This is a known limitation of Google's Gemini API
- Pydantic AI team has implemented automatic schema transformation
- Safe to ignore for PoC projects, but consider specific fields instead of generic dicts for production

**More Info:** [Pydantic AI Issue #1469](https://github.com/pydantic/pydantic-ai/issues/1469)