# Test Suite for RAG with Llama

This directory contains comprehensive tests for the RAG with Llama project, covering database connections, API integrations, embedding processes, and retrieval operations.

## Test Structure

```
test/
├── conftest.py                    # Pytest configuration and shared fixtures
├── test_database_connection.py    # PostgreSQL + pgvector connection tests
├── test_gemini_api.py            # Gemini API integration tests
├── test_logfire.py               # Logfire monitoring tests
├── test_embedding.py             # Embedding generation tests
├── test_retrieval.py             # Document retrieval tests
├── requirements-test.txt         # Test-specific dependencies
├── run_tests_docker.sh           # Docker test runner (Linux/Mac)
├── run_tests_docker.bat          # Docker test runner (Windows)
└── README.md                     # This file
```

## Prerequisites

1. **Environment Setup**: Ensure your `.env` file is properly configured with:
   - Database credentials (PostgreSQL)
   - `GOOGLE_API_KEY` (for Gemini API tests)
   - `LOGFIRE_WRITE_TOKEN` (optional, for Logfire tests)

2. **Choose Your Testing Approach**:
   - **Docker (Recommended)**: All dependencies included, isolated environment
   - **Local**: Direct Python installation, faster iteration for development

### Docker Prerequisites
- Docker and Docker Compose installed
- `.env` file configured (see `.env.example`)

### Local Prerequisites
- PostgreSQL with pgvector extension running
- Python 3.11+
- Python dependencies installed:
  ```bash
  pip install -r deployment/requirements.txt
  pip install -r test/requirements-test.txt
  ```

---

## Running Tests with Docker (Recommended)

Docker provides an isolated, reproducible test environment with all dependencies pre-installed.

### Quick Start

**Linux/Mac:**
```bash
# Make script executable (first time only)
chmod +x test/run_tests_docker.sh

# Run all tests
./test/run_tests_docker.sh

# Or specific command
./test/run_tests_docker.sh database
```

**Windows:**
```cmd
REM Run all tests
test\run_tests_docker.bat

REM Or specific command
test\run_tests_docker.bat database
```

### Available Docker Commands

| Command | Description |
|---------|-------------|
| `all` | Run all tests with coverage (default) |
| `database` | Run database connection tests only |
| `embedding` | Run embedding tests only |
| `retrieval` | Run retrieval tests only |
| `api` | Run API integration tests (Gemini, Logfire) |
| `ordered` | Run all tests in recommended order |
| `file <name>` | Run specific test file |
| `filter <keyword>` | Run tests matching keyword |
| `coverage` | Generate HTML coverage report |
| `shell` | Start interactive shell in test container |
| `build` | Rebuild test Docker image |
| `cleanup` | Clean up test containers |
| `help` | Show all available commands |

### Docker Test Examples

```bash
# Linux/Mac examples
./test/run_tests_docker.sh all                      # All tests with coverage
./test/run_tests_docker.sh database                 # Database tests only
./test/run_tests_docker.sh file test_embedding.py   # Specific file
./test/run_tests_docker.sh filter "similarity"      # Tests matching keyword
./test/run_tests_docker.sh ordered                  # Tests in recommended order
./test/run_tests_docker.sh shell                    # Interactive shell
./test/run_tests_docker.sh coverage                 # Generate coverage report
```

```cmd
REM Windows examples
test\run_tests_docker.bat all
test\run_tests_docker.bat database
test\run_tests_docker.bat file test_embedding.py
test\run_tests_docker.bat filter "similarity"
test\run_tests_docker.bat ordered
test\run_tests_docker.bat coverage
```

### Manual Docker Commands

If you prefer to use Docker Compose directly:

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Build test image
docker-compose --profile test build test

# Run all tests
docker-compose --profile test run --rm test

# Run specific test file
docker-compose --profile test run --rm test pytest test/test_database_connection.py -v

# Run with filter
docker-compose --profile test run --rm test pytest test/ -v -k "embedding"

# Interactive shell
docker-compose --profile test run --rm test /bin/bash

# Cleanup
docker-compose --profile test down
```

### Docker Test Environment

The test container includes:
- Python 3.11
- All project dependencies
- All test dependencies
- Pre-configured connection to PostgreSQL service
- Embedded environment variables from `.env`

---

## Running Tests Locally

### Run All Tests
```bash
# From project root
pytest test/ -v

# With coverage report
pytest test/ -v --cov=. --cov-report=html
```

### Run Specific Test Files
```bash
# Database connection tests
pytest test/test_database_connection.py -v

# Gemini API tests
pytest test/test_gemini_api.py -v

# Logfire tests
pytest test/test_logfire.py -v

# Embedding tests
pytest test/test_embedding.py -v

# Retrieval tests (run after embedding tests)
pytest test/test_retrieval.py -v
```

### Run Specific Test Classes or Functions
```bash
# Run a specific test class
pytest test/test_database_connection.py::TestDatabaseConnection -v

# Run a specific test function
pytest test/test_embedding.py::TestEmbedding::test_single_text_embedding -v
```

### Run Tests in Parallel
```bash
# Use pytest-xdist for parallel execution
pytest test/ -v -n auto
```

### Run Tests with Coverage
```bash
# Generate HTML coverage report
pytest test/ --cov=. --cov-report=html --cov-report=term

# View coverage report
# Open htmlcov/index.html in browser
```

## Test Categories

### 1. Database Connection Tests (`test_database_connection.py`)
- Basic PostgreSQL connectivity
- pgvector extension installation
- Table creation with vector columns
- Vector similarity operations
- IVFFLAT index creation
- Connection pooling
- JSONB metadata storage

**Run these first** to ensure database is properly configured.

### 2. Gemini API Tests (`test_gemini_api.py`)
- API key configuration
- Authentication
- Basic text generation
- JSON structured responses
- Entity extraction
- Context understanding
- Rate limiting handling
- Error handling

**Note**: Requires valid `GOOGLE_API_KEY` in `.env` file.

### 3. Logfire Tests (`test_logfire.py`)
- Logfire configuration
- Info and error logging
- Span/trace creation
- Async span support
- Structured data logging
- Exception logging
- Workflow tracking (embedding, search)

**Note**: Works in local mode without token, but full features require `LOGFIRE_WRITE_TOKEN`.

### 4. Embedding Tests (`test_embedding.py`)
- Model loading
- Single and batch text embedding
- Embedding consistency
- Similarity calculations
- Special character handling
- Normalization
- Database integration
- Performance testing

**Run before retrieval tests** as retrieval depends on embeddings.

### 5. Retrieval Tests (`test_retrieval.py`)
- Vector similarity search
- Threshold filtering
- Result limiting
- Semantic relevance
- Metadata retrieval
- Query consistency
- IVFFLAT index performance
- End-to-end pipeline

**Run after embedding tests** as these tests require embedded data.

## Test Execution Order

For best results, run tests in this order:

1. **Database Connection Tests** - Verify infrastructure
2. **Gemini API Tests** - Verify external API access
3. **Logfire Tests** - Verify monitoring setup
4. **Embedding Tests** - Verify embedding generation
5. **Retrieval Tests** - Verify end-to-end retrieval (depends on embeddings)

```bash
# Run in recommended order
pytest test/test_database_connection.py -v && \
pytest test/test_gemini_api.py -v && \
pytest test/test_logfire.py -v && \
pytest test/test_embedding.py -v && \
pytest test/test_retrieval.py -v
```

## Configuration

### Environment Variables Required

```bash
# Database (Required)
DB_HOST=localhost
DB_PORT=5432
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_password
POSTGRES_DB=rag_db

# Gemini API (Required for Gemini tests)
GOOGLE_API_KEY=your-google-api-key-here
GEMINI_MODEL=gemini-2.5-flash

# Logfire (Optional)
LOGFIRE_WRITE_TOKEN=your-token-or-leave-empty

# Embedding Model (Optional - has defaults)
ENTITY_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Pytest Configuration

The `conftest.py` file provides shared fixtures:
- `db_params` - Database connection parameters
- `db_connection` - Active database connection
- `gemini_api_key` - Gemini API key
- `embedding_model` - Loaded embedding model (session-scoped)
- `sample_texts` - Sample texts for testing
- `sample_queries` - Sample queries for retrieval tests
- `test_table_name` - Unique test table names
- `cleanup_test_table` - Automatic table cleanup

## Skipping Tests

### Skip Tests Without API Keys
Tests will automatically skip if required API keys are not configured:

```python
# test_gemini_api.py
@pytest.mark.asyncio
async def test_gemini_api_authentication(self, gemini_api_key):
    # Skips if GOOGLE_API_KEY not configured
    ...
```

### Skip Specific Tests
```bash
# Skip Gemini tests
pytest test/ -v -k "not gemini"

# Skip slow tests
pytest test/ -v -m "not slow"
```

## Troubleshooting

### Database Connection Errors
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection manually
psql -h localhost -U admin -d rag_db

# Restart PostgreSQL
docker-compose restart postgres
```

### Gemini API Errors
```bash
# Verify API key is set
echo $GOOGLE_API_KEY

# Test API key manually
python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY'); print(list(genai.list_models())[:1])"
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r deployment/requirements.txt
pip install -r test/requirements-test.txt

# Add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Test Table Cleanup Issues
```bash
# Manually drop test tables
psql -h localhost -U admin -d rag_db -c "DROP TABLE IF EXISTS test_chunks_*;"
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: admin
          POSTGRES_USER: admin
          POSTGRES_DB: rag_db
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r deployment/requirements.txt
          pip install -r test/requirements-test.txt

      - name: Run tests
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
        run: pytest test/ -v --cov
```

## Coverage Goals

Target test coverage:
- Database operations: 90%+
- Embedding generation: 85%+
- Retrieval operations: 85%+
- API integrations: 75%+

Generate coverage report:
```bash
pytest test/ --cov=. --cov-report=term-missing
```

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain or improve coverage
4. Update this README if needed

## Sample Test Output

```
test/test_database_connection.py::TestDatabaseConnection::test_database_connection PASSED
test/test_database_connection.py::TestDatabaseConnection::test_pgvector_extension PASSED
test/test_embedding.py::TestEmbedding::test_embedding_model_loading PASSED
test/test_embedding.py::TestEmbedding::test_single_text_embedding PASSED
test/test_retrieval.py::TestRetrieval::test_basic_similarity_search PASSED

========================= 35 passed in 12.34s =========================
```

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Logfire Documentation](https://logfire.pydantic.dev/)
