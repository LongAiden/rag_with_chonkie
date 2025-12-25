# Quick Start - Running Tests in 2 Minutes

This guide gets you running tests in Docker in under 2 minutes.

## Step 1: Check Prerequisites (30 seconds)

Make sure you have:
- [ ] Docker installed and running
- [ ] `.env` file configured with `GOOGLE_API_KEY`

```cmd
REM Windows - Check Docker
docker --version

REM Check .env exists
type .env
```

```bash
# Linux/Mac - Check Docker
docker --version

# Check .env exists
cat .env
```

## Step 2: Run Tests (30 seconds)

**Windows:**
```cmd
test\run_tests_docker.bat
```

**Linux/Mac:**
```bash
chmod +x test/run_tests_docker.sh
./test/run_tests_docker.sh
```

That's it! 🎉

## What Happens?

The script will:
1. ✅ Start PostgreSQL if needed (automatic)
2. ✅ Build test Docker image (first time only, ~2-3 min)
3. ✅ Run all 58 tests (~30-60 sec)
4. ✅ Generate coverage report in `htmlcov/`

## First Run vs. Subsequent Runs

**First Run** (~3-5 minutes total):
- Downloads Docker images
- Builds test image
- Runs tests

**Subsequent Runs** (~30-60 seconds):
- Reuses existing images
- Only runs tests

## Sample Output

```
[INFO] Checking PostgreSQL container...
[INFO] Running all tests with coverage...

test/test_database_connection.py::test_database_connection PASSED    [ 1%]
test/test_database_connection.py::test_pgvector_extension PASSED     [ 3%]
test/test_gemini_api.py::test_basic_text_generation PASSED          [ 5%]
test/test_embedding.py::test_single_text_embedding PASSED           [ 8%]
test/test_retrieval.py::test_basic_similarity_search PASSED         [10%]
...

========================= 58 passed in 45.23s =========================

[SUCCESS] All tests completed! Coverage report available in htmlcov/
```

## Quick Commands Reference

| What you want | Windows Command | Linux/Mac Command |
|---------------|----------------|-------------------|
| Run all tests | `test\run_tests_docker.bat` | `./test/run_tests_docker.sh` |
| Just database tests | `test\run_tests_docker.bat database` | `./test/run_tests_docker.sh database` |
| Just embedding tests | `test\run_tests_docker.bat embedding` | `./test/run_tests_docker.sh embedding` |
| See coverage report | `test\run_tests_docker.bat coverage` | `./test/run_tests_docker.sh coverage` |
| Debug in shell | `test\run_tests_docker.bat shell` | `./test/run_tests_docker.sh shell` |
| See all commands | `test\run_tests_docker.bat help` | `./test/run_tests_docker.sh help` |

## Common First-Time Issues

### "GOOGLE_API_KEY not configured"
**Fix**: Add to `.env` file:
```
GOOGLE_API_KEY=your-actual-api-key-here
```

### "Docker is not running"
**Fix**: Start Docker Desktop

### "Permission denied" (Linux/Mac only)
**Fix**:
```bash
chmod +x test/run_tests_docker.sh
```

### PostgreSQL container fails to start
**Fix**:
```bash
# Stop all containers
docker-compose down

# Start fresh
docker-compose up -d postgres

# Wait 10 seconds, then try tests again
```

## Skip Tests You Don't Need

**Skip Gemini API tests** (if no API key):
```cmd
test\run_tests_docker.bat filter "not gemini"
```

**Skip Logfire tests** (if no token):
```cmd
test\run_tests_docker.bat filter "not logfire"
```

**Run only database tests**:
```cmd
test\run_tests_docker.bat database
```

## What's Being Tested?

✅ **Database** (8 tests)
- PostgreSQL connection
- pgvector extension
- Vector operations

✅ **Gemini API** (8 tests)
- API authentication
- Text generation
- Entity extraction

✅ **Logfire** (13 tests)
- Logging and tracing
- Span creation

✅ **Embedding** (15 tests)
- Text to vectors
- Similarity calculations
- Database storage

✅ **Retrieval** (14 tests)
- Semantic search
- Result ranking
- End-to-end pipeline

**Total: 58 tests**

## Next Steps

After tests pass:

1. **View Coverage Report**
   - Open `htmlcov/index.html` in browser
   - See which code is tested

2. **Run Specific Tests**
   - Use `database`, `embedding`, etc.
   - Faster feedback during development

3. **Read Full Documentation**
   - [test/README.md](README.md) - Complete guide
   - [test/DOCKER_TESTING.md](DOCKER_TESTING.md) - Docker details

## Need Help?

**View all commands:**
```cmd
test\run_tests_docker.bat help
```

**Debug in container:**
```cmd
test\run_tests_docker.bat shell

# Inside container:
pytest test/test_embedding.py -v  # Run specific test
pytest test/ --lf                 # Re-run last failed
exit                              # Exit shell
```

**Check what's running:**
```cmd
docker-compose ps
```

**See logs:**
```cmd
docker-compose logs postgres
docker-compose logs test
```

## That's It!

You now have a comprehensive test suite running in Docker.

For more details, see:
- [Full Documentation](README.md)
- [Docker Testing Guide](DOCKER_TESTING.md)
- [Testing Summary](../TESTING_SUMMARY.md)
