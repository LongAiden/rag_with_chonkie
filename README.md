# RAG with pgvector

A Retrieval-Augmented Generation (RAG) system built with FastAPI, PostgreSQL + pgvector, and Chonkie for markdown-aware chunking.

## How It Works

```
PDF file  →  PDFToMarkdownConverter  →  MarkdownChunker  →  pgvector  →  Query + Rerank  →  Gemini Answer
input/pdf/       (ingestion)            (chonkie)           (PostgreSQL)   (BM25)            (pydantic-ai)
```

1. **Upload a PDF** - the app converts it to Markdown and stores in `input/markdown/`
2. **Chunk** - the Markdown is split into chunks using a structure-aware MarkdownChunker
3. **Embed** - each chunk is embedded with `all-MiniLM-L6-v2` and stored in pgvector
4. **Query** - a question triggers vector similarity search + BM25 reranking
5. **Answer** - top chunks are passed to Gemini which returns a structured answer

---

## Quick Start

### 1. Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) (8 GB+ RAM allocated)
- A [Google Gemini API key](https://makersuite.google.com/app/apikey)

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env - minimum required:
#   GOOGLE_API_KEY=your-key-here
#   POSTGRES_PASSWORD=a-secure-password
```

### 3. Build and run

The Dockerfile uses a two-stage build. The first stage (`Dockerfile.base`) installs heavy ML
dependencies and only needs to run once. Subsequent builds are fast.

```bash
# Step 1 - build the base image (first time only, ~8–10 min)
docker build -f deployment/Dockerfile.base -t rag-base:latest .

# Step 2 - build and start all services (~1–2 min)
docker compose up --build
```

The app is ready when you see:
```
rag_app  | INFO:     Application startup complete.
```

Open **http://localhost:8000**

| URL | Description |
|-----|-------------|
| http://localhost:8000 | Web UI (upload + search) |
| http://localhost:8000/docs | **Swagger UI - interactive API docs** |
| http://localhost:8000/redoc | ReDoc - readable API reference |
| http://localhost:8000/health | Health check |

> **Swagger UI** (`/docs`) lets you call every endpoint directly from the browser - no curl or Postman needed. Click an endpoint → **Try it out** → fill in params → **Execute**.

### 4. Stop services

```bash
docker compose down
```

---

## Services

| Service | Port | Description |
|---------|------|-------------|
| `app` | 8000 | FastAPI application |
| `postgres` | 5432 | PostgreSQL + pgvector |
| `redis` | 6379 | Celery broker |
| `celery_worker` | - | Background task worker |
| `pgadmin` | 5050 | DB admin UI *(dev profile only)* |

```bash
# Start pgAdmin (optional database UI)
docker compose --profile dev up -d pgadmin
# Then open http://localhost:5050
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web UI |
| `POST` | `/upload` | Upload and process a document |
| `POST` | `/query` | Ask a question, get a RAG answer |
| `GET` | `/stats` | Database statistics |
| `GET` | `/health` | Health check |
| `GET` | `/supported-types` | Accepted file formats |
| `DELETE` | `/table/{name}` | Delete a document table |
| `GET` | `/docs` | FastAPI Swagger UI |

### Examples

**Upload a PDF:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@input/pdf/llama2.pdf" \
  -F "chunk_size=512" \
  -F "table_name=documents"
```

**Ask a question:**
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What safety measures does Llama 2 have?", "limit": 5}'
```

---

## Project Structure

```
rag_with_llama/
│
├── input/                        # Runtime I/O
│   ├── pdf/                      # Drop PDFs here (e.g. llama2.pdf)
│   └── markdown/                 # Auto-generated Markdown output
│
├── ingestion/                    # Document ingestion pipeline
│   ├── processors/
│   │   ├── pdf_to_markdown.py    # PDFToMarkdownConverter (PDF → Markdown)
│   │   ├── pdf_processor.py      # Raw text extraction fallback
│   │   ├── docx_processor.py
│   │   ├── txt_processor.py
│   │   └── processor_factory.py  # Picks processor by file type
│   ├── chunking/
│   │   └── chunker_factory.py    # token / recursive / markdown / semantic
│   ├── embedding/
│   │   └── vector_store.py       # ChunkEmbeddingPipeline + pgvector
│   ├── text_cleaning/
│   │   └── cleaners.py
│   └── validation/
│       └── file_validator.py
│
├── retrieval/
│   ├── search.py                 # Vector search → BM25 rerank → LLM
│   ├── llm_operations.py         # Gemini answer generation
│   └── utils.py                  # BM25 scorer
│
├── api/
│   ├── app.py                    # FastAPI app, route registration
│   ├── config.py                 # Re-export shim (config lives in config/)
│   ├── validators.py
│   ├── templates.py              # Inline HTML templates
│   └── routes/
│       └── document_routes.py    # All active endpoints
│
├── config/
│   └── app_config.py             # AppConfig, AppSettings, DatabaseConfig
│
├── models/
│   └── models.py                 # Pydantic request/response models
│
├── worker/
│   ├── celery_app.py
│   └── tasks.py                  # Async upload task
│
├── graph_processing/             # Knowledge graph - DISABLED (code preserved)
│
├── tests/
│   ├── unit/                     # No DB required
│   └── integration/              # Requires running postgres
│
├── docs/                         # Developer documentation
│   ├── CHUNKING_STRATEGIES.md
│   ├── PROJECT_ARCHITECTURE_SUMMARY.md
│   └── TESTING.md
│
├── deployment/
│   ├── Dockerfile                # App image (uses Dockerfile.base)
│   ├── Dockerfile.base           # Heavy ML deps (build once)
│   ├── Dockerfile.postgres       # Postgres + pgvector
│   ├── Dockerfile.test           # Test runner
│   ├── requirements.txt
│   └── Makefile                  # Test + dev shortcuts
│
├── docker-compose.yml
└── .env.example
```

---

## Configuration

Copy `.env.example` to `.env` and set these values:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | Yes | - | Gemini API key |
| `POSTGRES_PASSWORD` | Yes | `admin` | Change in production |
| `POSTGRES_DB` | No | `rag_db` | Database name |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model to use |
| `CHUNKER_TYPE` | No | `markdown` | `markdown` / `recursive` / `token` / `semantic` |
| `APP_ACCESS_PASSWORD` | No | *(disabled)* | Password-protect the web UI |
| `LOGFIRE_WRITE_TOKEN` | No | - | [Logfire](https://logfire.pydantic.dev/) monitoring |

---

## Running Tests

The Makefile is in `deployment/`. Use it with:

```bash
make -f deployment/Makefile <target>
```

| Command | Description |
|---------|-------------|
| `make -f deployment/Makefile test-unit` | Unit tests locally (no DB) |
| `make -f deployment/Makefile test-integration` | Integration tests locally |
| `make -f deployment/Makefile test-docker-unit` | Unit tests in Docker |
| `make -f deployment/Makefile test-docker` | All tests in Docker |
| `make -f deployment/Makefile coverage` | HTML coverage report |

Or run pytest directly:
```bash
pytest tests/unit -v           # fast, no database needed
pytest tests/integration -v    # requires running postgres
```

---

## Screenshots

**Web UI:**

<img src="./images/home_screen.png" alt="Home Screen" width="600">

**Query + Results:**

<img src="./images/query.png" alt="Query Interface" width="600">

<img src="./images/rerank_result.png" alt="Reranked Results" width="600">

<img src="./images/metadata_rerank.png" alt="Source Metadata" width="400">

**Health + Stats:**

<img src="./images/health_status.png" alt="Health Status" width="600">

<img src="./images/database.png" alt="Database Statistics" width="600">

**Logfire monitoring:**

<img src="./images/logfire_example.png" alt="Logfire" width="600">

<img src="./images/rerank_logfire.png" alt="Logfire Rerank Step" width="600">

---

## Rebuilding After Changes

```bash
# Code changes only (fast, ~30 seconds)
docker compose restart app celery_worker

# Dependency changes (slower, ~1–2 min)
docker compose up --build
```

---

## Troubleshooting

**Services not starting:**
```bash
docker compose ps
docker compose logs app
docker compose logs postgres
```

**Port 8000 already in use:**
```bash
# Change in docker-compose.yml: "8001:8000"
```

**Reset the database (deletes all data):**
```bash
docker compose down -v
docker compose up --build
```

**Full clean rebuild:**
```bash
docker compose down -v
docker system prune -a
docker build -f deployment/Dockerfile.base -t rag-base:latest .
docker compose up --build
```

---

## Known Issue - Gemini `additionalProperties` Warning

```
UserWarning: `additionalProperties` is not supported by Gemini; it will be removed from the tool JSON schema.
```

This is a known Gemini API limitation. It does not break functionality - responses work correctly, but the `metadata` field in LLM responses will be empty. See [pydantic-ai #1469](https://github.com/pydantic/pydantic-ai/issues/1469).

---

## Further Reading

- [Chunking Strategies](docs/CHUNKING_STRATEGIES.md)
- [Project Architecture](docs/PROJECT_ARCHITECTURE_SUMMARY.md)
- [Testing Guide](docs/TESTING.md)
