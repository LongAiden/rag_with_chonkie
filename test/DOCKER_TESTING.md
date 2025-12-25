# Docker Testing Quick Reference

This guide shows you how to run tests inside Docker containers, which is the recommended approach since all your application components run in Docker.

## Why Test with Docker?

- ✅ **Isolated Environment**: Tests run in the same environment as your application
- ✅ **All Dependencies Included**: No need to install Python, PostgreSQL, or dependencies locally
- ✅ **Reproducible**: Everyone gets the same test environment
- ✅ **CI/CD Ready**: Same setup works in CI pipelines
- ✅ **No Local Setup**: Works on Windows, Mac, Linux without configuration

## Quick Start

### 1. Ensure `.env` is Configured

Make sure your `.env` file has the required credentials:

```bash
# Database
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_password
POSTGRES_DB=rag_db

# API Keys
GOOGLE_API_KEY=your-google-api-key-here

# Optional
LOGFIRE_WRITE_TOKEN=your-token-or-leave-empty
```

### 2. Run Tests

**Windows:**
```cmd
test\run_tests_docker.bat
```

**Linux/Mac:**
```bash
chmod +x test/run_tests_docker.sh
./test/run_tests_docker.sh
```

That's it! The script will:
1. Check if PostgreSQL is running (start it if needed)
2. Build the test Docker image
3. Run all tests with coverage
4. Generate HTML coverage report in `htmlcov/`

## Common Commands

### Run All Tests
```bash
# Windows
test\run_tests_docker.bat all

# Linux/Mac
./test/run_tests_docker.sh all
```

### Run Specific Test Category
```bash
# Database tests only
test\run_tests_docker.bat database

# Embedding tests only
test\run_tests_docker.bat embedding

# Retrieval tests only
test\run_tests_docker.bat retrieval

# API tests (Gemini + Logfire)
test\run_tests_docker.bat api
```

### Run Tests in Recommended Order
```bash
test\run_tests_docker.bat ordered
```

This runs tests in sequence:
1. Database connection tests
2. Gemini API tests
3. Logfire tests
4. Embedding tests
5. Retrieval tests

### Run Specific Test File
```bash
test\run_tests_docker.bat file test_embedding.py
```

### Filter Tests by Keyword
```bash
# Run only tests with "similarity" in name
test\run_tests_docker.bat filter similarity

# Run only tests with "database" in name
test\run_tests_docker.bat filter database
```

### Generate Coverage Report
```bash
test\run_tests_docker.bat coverage
```

Opens HTML coverage report in browser (Windows) or generates report in `htmlcov/`.

### Interactive Shell
```bash
test\run_tests_docker.bat shell
```

Starts an interactive bash shell inside the test container. Useful for:
- Debugging tests
- Running custom pytest commands
- Inspecting the environment

### Build Test Image
```bash
test\run_tests_docker.bat build
```

Rebuilds the test Docker image. Run this when:
- Dependencies change
- Dockerfile.test changes
- You want to ensure a clean build

### Cleanup
```bash
test\run_tests_docker.bat cleanup
```

Stops and removes test containers.

## Docker Architecture

```
┌─────────────────────────────────────────────┐
│          Your Computer                      │
│                                             │
│  ┌──────────────┐      ┌─────────────────┐ │
│  │   test/      │      │  Docker Network │ │
│  │   - Tests    │      │  (rag_network)  │ │
│  │   - Scripts  │      │                 │ │
│  └──────┬───────┘      │  ┌───────────┐  │ │
│         │              │  │ PostgreSQL│  │ │
│         │              │  │ + pgvector│  │ │
│         ▼              │  └─────┬─────┘  │ │
│  ┌──────────────┐      │        │        │ │
│  │ Test         │      │        │        │ │
│  │ Container    │◄─────┼────────┘        │ │
│  │              │      │                 │ │
│  │ - Python 3.11│      │                 │ │
│  │ - All deps   │      │                 │ │
│  │ - pytest     │      │                 │ │
│  └──────────────┘      └─────────────────┘ │
│         │                                   │
│         ▼                                   │
│  ┌──────────────┐                          │
│  │  htmlcov/    │  (Coverage reports)      │
│  └──────────────┘                          │
└─────────────────────────────────────────────┘
```

## How It Works

### 1. Test Service in docker-compose.yml

The `docker-compose.yml` includes a test service:

```yaml
test:
  build:
    context: .
    dockerfile: Dockerfile.test
  environment:
    DB_HOST: postgres  # Uses service name
    POSTGRES_DB: rag_db
    GOOGLE_API_KEY: ${GOOGLE_API_KEY}
  depends_on:
    postgres:
      condition: service_healthy
  networks:
    - rag_network
  profiles:
    - test  # Only runs when explicitly requested
```

### 2. Dockerfile.test

Builds a test-specific image with:
- All application code
- All test files
- pytest and test dependencies
- Pre-configured environment

### 3. Test Runner Scripts

Bash (Linux/Mac) and Batch (Windows) scripts that:
- Check PostgreSQL status
- Run docker-compose with test profile
- Pass arguments to pytest
- Handle cleanup

## Environment Variables

Tests use environment variables from `.env`:

### Required
- `POSTGRES_USER` - Database username
- `POSTGRES_PASSWORD` - Database password
- `POSTGRES_DB` - Database name
- `GOOGLE_API_KEY` - Gemini API key

### Optional
- `LOGFIRE_WRITE_TOKEN` - Logfire monitoring token
- `GEMINI_MODEL` - Gemini model name (default: gemini-2.5-flash)
- `ENTITY_EMBEDDING_MODEL` - Embedding model (default: all-MiniLM-L6-v2)

### Docker-Specific
- `DB_HOST` - Set to `postgres` (service name) automatically
- `DB_PORT` - Set to `5432` automatically

## Troubleshooting

### PostgreSQL Not Starting

```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres

# Fresh start
docker-compose down
docker-compose up -d postgres
```

### Test Image Build Fails

```bash
# Clean build
docker-compose --profile test build --no-cache test

# Check Dockerfile.test
# Ensure requirements files exist
```

### Tests Can't Connect to Database

```bash
# Check if PostgreSQL is healthy
docker-compose ps postgres

# Check network
docker network ls | grep rag_network

# Try manual connection
docker-compose exec postgres psql -U admin -d rag_db
```

### Permission Errors (Linux/Mac)

```bash
# Make script executable
chmod +x test/run_tests_docker.sh

# If coverage reports have permission issues
sudo chown -R $USER:$USER htmlcov/
```

### API Key Errors

```bash
# Verify .env file
cat .env | grep GOOGLE_API_KEY

# Test API key manually
docker-compose --profile test run --rm test python -c "import os; print(os.getenv('GOOGLE_API_KEY'))"
```

## Advanced Usage

### Custom pytest Arguments

```bash
# Windows
test\run_tests_docker.bat custom test/test_embedding.py::TestEmbedding::test_single_text_embedding -v

# Linux/Mac
./test/run_tests_docker.sh custom test/test_embedding.py::TestEmbedding::test_single_text_embedding -v
```

### Debugging Inside Container

```bash
# Start shell
test\run_tests_docker.bat shell

# Inside container:
pytest test/test_database_connection.py -v --pdb  # Drop into debugger on failure
pytest test/ -v --lf  # Re-run last failed test
pytest test/ -v --trace  # Trace execution
```

### Run Tests with Different Python Version

Edit `Dockerfile.test`:
```dockerfile
ARG PYTHON_VERSION=3.12  # Change from 3.11
```

Rebuild:
```bash
test\run_tests_docker.bat build
```

### Parallel Test Execution

```bash
# Inside container shell
pytest test/ -v -n auto  # Use all CPU cores
pytest test/ -v -n 4     # Use 4 workers
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Docker Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Create .env file
        run: |
          echo "GOOGLE_API_KEY=${{ secrets.GOOGLE_API_KEY }}" >> .env
          echo "POSTGRES_USER=admin" >> .env
          echo "POSTGRES_PASSWORD=admin" >> .env
          echo "POSTGRES_DB=rag_db" >> .env

      - name: Run tests
        run: |
          chmod +x test/run_tests_docker.sh
          ./test/run_tests_docker.sh all

      - name: Upload coverage
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: htmlcov/
```

### GitLab CI

```yaml
test:
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - docker-compose --version
  script:
    - chmod +x test/run_tests_docker.sh
    - ./test/run_tests_docker.sh all
  artifacts:
    paths:
      - htmlcov/
```

## Performance Tips

1. **Keep PostgreSQL Running**: The test scripts automatically start PostgreSQL if needed, but keeping it running between test runs is faster.

2. **Use Specific Test Commands**: Running `database` or `embedding` is faster than `all` when you only need specific tests.

3. **Build Once**: Build the test image once, then run tests multiple times without rebuilding.

4. **Use Filter**: `filter` command is faster than running all tests.

5. **Parallel Execution**: Use `custom test/ -n auto` for parallel execution (inside shell).

## Best Practices

1. ✅ Run `ordered` when adding new features to ensure all components work
2. ✅ Run specific test categories during development for faster feedback
3. ✅ Generate `coverage` reports before committing
4. ✅ Use `shell` for debugging failing tests
5. ✅ Run `cleanup` periodically to free up disk space
6. ✅ Keep `.env` file updated with valid credentials

## Getting Help

View all available commands:
```bash
test\run_tests_docker.bat help
```

For more detailed information, see [test/README.md](README.md).
