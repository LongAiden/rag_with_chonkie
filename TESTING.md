# Testing Guide

This guide explains how to run tests both inside Docker and locally on your machine.

## Quick Start

```bash
# See all available test commands
make help

# Run all tests in Docker (recommended)
make test-docker

# Run tests locally (requires setup)
make test
```

---

## Option 1: Testing Inside Docker (Recommended)

**Advantages:**
- ✅ Consistent environment across all machines
- ✅ Automatic database and Redis setup
- ✅ No need to install dependencies locally
- ✅ Mirrors production environment

### Prerequisites

- Docker and Docker Compose installed
- `.env` file configured (copy from `.env.example`)

### Running Tests

#### 1. Run All Tests

```bash
make test-docker
```

Or manually:
```bash
docker-compose --profile test up --build test
```

#### 2. Run Only Unit Tests (Fast, No Database Required)

```bash
make test-docker-unit
```

Unit tests are isolated and don't require external services:
- `tests/unit/test_chunker_factory.py` - Chunking strategies
- `tests/unit/test_pdf_processor.py` - PDF processing
- `tests/unit/test_text_cleaning.py` - Text cleaning pipeline
- `tests/unit/test_embedding_generator.py` - Embedding generation
- `tests/unit/test_file_validator.py` - File validation

#### 3. Run Only Integration Tests (Requires Database)

```bash
make test-docker-integration
```

Integration tests verify:
- Database connectivity and pgvector
- Real embedding models
- Vector similarity search
- End-to-end retrieval pipelines

#### 4. Run Tests with Coverage Report

```bash
make test-docker-coverage
```

This generates:
- Terminal coverage summary
- HTML report in `htmlcov/index.html`

#### 5. Run Specific Test File

```bash
docker-compose --profile test run --rm test pytest tests/unit/test_chunker_factory.py -v
```

#### 6. Interactive Debug Shell

```bash
make test-docker-shell
```

Then inside the container:
```bash
pytest tests/unit/test_chunker_factory.py -v
python -m pytest tests/integration/test_retrieval.py::TestRetrieval::test_basic_similarity_search -v
```

### Viewing Test Results

Coverage reports are saved to `htmlcov/`:
```bash
# Open coverage report in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

---

## Option 2: Testing Outside Docker (Local Development)

**Advantages:**
- ✅ Faster test execution (no container overhead)
- ✅ Better IDE integration
- ✅ Easier debugging with breakpoints

**Disadvantages:**
- ❌ Requires manual dependency installation
- ❌ Need to run PostgreSQL separately for integration tests
- ❌ Environment differences across machines

### Prerequisites

#### 1. Install Python Dependencies

```bash
# Install application dependencies
pip install -r deployment/requirements.txt

# Install test dependencies
make install-dev
```

Or manually:
```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock reportlab
```

#### 2. Setup PostgreSQL with pgvector (For Integration Tests)

You have two options:

**Option A: Use Docker for Database Only**
```bash
# Start only the database
docker-compose up -d postgres

# Your tests will connect to localhost:5432
```

**Option B: Install PostgreSQL Locally**
```bash
# macOS
brew install postgresql@15
brew services start postgresql@15
psql postgres -c "CREATE DATABASE rag_db;"
psql rag_db -c "CREATE EXTENSION vector;"

# Linux (Ubuntu/Debian)
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo -u postgres createdb rag_db
sudo -u postgres psql rag_db -c "CREATE EXTENSION vector;"
```

#### 3. Configure Environment Variables

Ensure your `.env` file has correct connection details:

```bash
# For Docker database
DB_HOST=localhost
DB_PORT=5432
POSTGRES_DB=rag_db
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin

# API keys (required for integration tests)
GOOGLE_API_KEY=your_key_here
```

### Running Tests Locally

#### 1. Run All Tests

```bash
make test
```

Or:
```bash
pytest tests/ -v
```

#### 2. Run Unit Tests Only (No Database Needed)

```bash
make test-unit
```

Or:
```bash
pytest tests/unit -v
```

#### 3. Run Integration Tests (Requires Database)

```bash
make test-integration
```

Or:
```bash
pytest tests/integration -v
```

#### 4. Run Specific Test File

```bash
pytest tests/unit/test_chunker_factory.py -v
```

#### 5. Run Specific Test Class

```bash
pytest tests/unit/test_chunker_factory.py::TestGetChunker -v
```

#### 6. Run Specific Test Method

```bash
pytest tests/unit/test_chunker_factory.py::TestGetChunker::test_get_token_chunker -v
```

#### 7. Run Tests with Coverage

```bash
make coverage
```

Or:
```bash
pytest tests/ --cov=. --cov-report=html --cov-report=term
open htmlcov/index.html
```

#### 8. Run Fast Tests Only (Skip Slow Tests)

```bash
make test-fast
```

#### 9. Watch Mode (Auto-rerun on Changes)

Requires `pytest-watch`:
```bash
pip install pytest-watch
make test-watch
```

---

## Test Structure

```
tests/
├── conftest.py              # Session-level fixtures
├── unit/                    # Unit tests (isolated, fast)
│   ├── conftest.py          # Unit test fixtures (mocks)
│   ├── test_chunker_factory.py
│   ├── test_pdf_processor.py
│   ├── test_text_cleaning.py
│   ├── test_embedding_generator.py
│   └── test_file_validator.py
├── integration/             # Integration tests (real dependencies)
│   ├── conftest.py          # Integration fixtures (real DB, API)
│   ├── test_database_connection.py
│   ├── test_embedding_pipeline.py
│   └── test_retrieval.py
└── fixtures/                # Test data files
```

---

## Understanding Test Types

### Unit Tests
- **Location:** `tests/unit/`
- **Dependencies:** None (uses mocks)
- **Speed:** Fast (< 1 second each)
- **Purpose:** Test individual components in isolation

Example:
```python
def test_get_token_chunker():
    """Test getting a token chunker."""
    chunker = get_chunker(chunker_type="token", chunk_size=512)
    assert chunker is not None
    assert "TokenChunker" in type(chunker).__name__
```

### Integration Tests
- **Location:** `tests/integration/`
- **Dependencies:** PostgreSQL + pgvector, Redis, API keys
- **Speed:** Slower (2-10 seconds each)
- **Purpose:** Test system components working together

Example:
```python
@pytest.mark.asyncio
async def test_basic_similarity_search(self, db_connection, embedding_model):
    """Test vector similarity search."""
    query_embedding = embedding_model.encode(query).tolist()
    results = await db_connection.fetch(...)
    assert len(results) > 0
```

---

## Troubleshooting

### Tests Fail with Database Connection Error

**Problem:**
```
asyncpg.exceptions.ConnectionRefusedError: connection refused
```

**Solution:**
```bash
# Check if database is running
docker-compose ps postgres

# Start database if not running
docker-compose up -d postgres

# Wait for database to be ready
sleep 5

# Verify connection
docker-compose exec postgres psql -U admin -d rag_db -c "SELECT 1"
```

### Tests Fail with "No module named..."

**Problem:**
```
ModuleNotFoundError: No module named 'chonkie'
```

**Solution (Docker):**
```bash
# Rebuild test image
docker-compose build --no-cache test
```

**Solution (Local):**
```bash
# Reinstall dependencies
pip install -r deployment/requirements.txt
```

### Integration Tests Skip with "GOOGLE_API_KEY not configured"

**Problem:**
```
SKIPPED [1] tests/integration/conftest.py:40: GOOGLE_API_KEY not configured
```

**Solution:**
Add your API key to `.env`:
```bash
GOOGLE_API_KEY=your_actual_api_key_here
```

### pgvector Extension Not Found

**Problem:**
```
asyncpg.exceptions.UndefinedFileError: could not open extension control file
```

**Solution:**
```bash
# Using Docker (automatic)
docker-compose down -v
docker-compose up -d postgres

# Using local PostgreSQL
psql rag_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Permission Denied on htmlcov/

**Problem:**
```
PermissionError: [Errno 13] Permission denied: 'htmlcov'
```

**Solution:**
```bash
sudo chown -R $USER:$USER htmlcov/
# Or delete and recreate
rm -rf htmlcov/
```

---

## Best Practices

### 1. Run Unit Tests First
Always run unit tests before integration tests:
```bash
make test-docker-unit  # Fast feedback
make test-docker-integration  # If unit tests pass
```

### 2. Use Coverage to Find Gaps
```bash
make test-docker-coverage
open htmlcov/index.html
```

Look for:
- Red lines (not covered)
- Branches not taken
- Functions never called

### 3. Write Tests Following AAA Pattern
```python
def test_example():
    # Arrange: Setup test data
    chunker = get_chunker(chunker_type="token")

    # Act: Perform action
    result = chunker.chunk("test text")

    # Assert: Verify result
    assert len(result) > 0
```

### 4. Clean Up After Tests
```bash
make clean-test  # Remove cache and coverage files
```

### 5. Use Markers for Test Organization
```python
@pytest.mark.slow
def test_large_document_processing():
    # Long-running test
    pass
```

Run with:
```bash
pytest -m "not slow"  # Skip slow tests
pytest -m "integration"  # Run only integration tests
```

---

## CI/CD Integration

For automated testing in CI/CD pipelines:

```yaml
# Example: GitHub Actions
- name: Run Tests
  run: |
    docker-compose --profile test up --build test

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `make test-docker` | All tests in Docker |
| `make test-docker-unit` | Unit tests in Docker |
| `make test-docker-integration` | Integration tests in Docker |
| `make test` | All tests locally |
| `make test-unit` | Unit tests locally |
| `make coverage` | Generate coverage report |
| `make clean-test` | Clean test artifacts |
| `make docker-up` | Start all services |
| `make docker-down` | Stop all services |

---

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [Docker Compose documentation](https://docs.docker.com/compose/)
- [pgvector documentation](https://github.com/pgvector/pgvector)
