# Pytest Structure Guide

This guide explains the structure of pytest tests using examples from this project.

## Table of Contents
- [Basic Test Structure](#basic-test-structure)
- [Test Organization](#test-organization)
- [Fixtures](#fixtures)
- [Async Tests](#async-tests)
- [Assertions](#assertions)
- [Test Markers](#test-markers)
- [Best Practices](#best-practices)

---

## Basic Test Structure

### 1. Simple Synchronous Test

```python
import pytest

def test_simple_addition():
    """Test basic addition operation."""
    result = 2 + 2
    assert result == 4, "Addition failed"
```

**Key Components:**
- Function name starts with `test_`
- Docstring describes what is being tested
- `assert` statements verify behavior
- Optional message after assertion for clarity

### 2. Test with Fixture (Dependency Injection)

```python
def test_embedding_model_loading(self, embedding_model):
    """Test that embedding model loads successfully."""
    assert embedding_model is not None, "Embedding model failed to load"

    # Check model properties
    embedding_dim = embedding_model.get_sentence_embedding_dimension()
    assert embedding_dim == 384, f"Expected 384 dimensions, got {embedding_dim}"
```

**Key Components:**
- `embedding_model` is a fixture (defined in [conftest.py](conftest.py:58-61))
- Pytest automatically injects the fixture
- No manual setup/teardown needed

---

## Test Organization

### 1. Test Classes (Recommended)

Group related tests into classes:

```python
class TestEmbedding:
    """Test suite for embedding generation."""

    def test_single_text_embedding(self, embedding_model):
        """Test embedding generation for a single text."""
        text = "Machine learning is a subset of artificial intelligence."

        embedding = embedding_model.encode(text)

        assert embedding is not None, "Embedding is None"
        assert len(embedding) == 384, f"Expected 384 dimensions, got {len(embedding)}"
        assert isinstance(embedding, np.ndarray), "Embedding should be numpy array"

    def test_batch_text_embedding(self, embedding_model, sample_texts):
        """Test embedding generation for multiple texts."""
        embeddings = embedding_model.encode(sample_texts)

        assert embeddings is not None, "Embeddings is None"
        assert len(embeddings) == len(sample_texts), "Number doesn't match"
```

**Benefits:**
- Logical grouping of related tests
- Shared context in docstring
- Easy to run specific test groups: `pytest test_embedding.py::TestEmbedding`

### 2. File Organization

```
test/
├── conftest.py                    # Shared fixtures and configuration
├── test_database_connection.py    # Database-related tests
├── test_embedding.py              # Embedding-related tests
├── test_retrieval.py              # Retrieval-related tests
└── test_gemini_api.py            # API integration tests
```

**Convention:**
- One test file per module/feature
- File names start with `test_`
- Related tests in same file

---

## Fixtures

Fixtures provide reusable setup code. Defined in [conftest.py](conftest.py).

### 1. Session-Scoped Fixture (Setup Once)

```python
@pytest.fixture(scope="session")
def embedding_model():
    """Shared embedding model for tests (loaded once per session)."""
    model_name = os.getenv('ENTITY_EMBEDDING_MODEL',
                           'sentence-transformers/all-MiniLM-L6-v2')
    return SentenceTransformer(model_name)
```

**Scope Options:**
- `function` - New instance per test (default)
- `class` - New instance per test class
- `module` - New instance per test file
- `session` - One instance for entire test run

### 2. Function-Scoped Fixture (Setup Per Test)

```python
@pytest.fixture
async def db_connection(db_params):
    """Create a database connection for a single test."""
    conn = await asyncpg.connect(**db_params)
    try:
        # Ensure pgvector extension is enabled
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        yield conn
    finally:
        await conn.close()
```

**Key Features:**
- `yield` provides the resource
- Code after `yield` runs for cleanup (teardown)
- Automatic cleanup even if test fails

### 3. Cleanup Fixture

```python
@pytest.fixture
async def cleanup_test_table(db_connection, test_table_name):
    """Cleanup fixture that drops the test table after the test."""
    yield
    # Cleanup: drop test table
    try:
        await db_connection.execute(f"DROP TABLE IF EXISTS {test_table_name};")
    except Exception as e:
        print(f"Warning: Could not drop test table {test_table_name}: {e}")
```

**Usage:**
```python
@pytest.mark.asyncio
async def test_create_vector_table(self, db_connection,
                                   test_table_name, cleanup_test_table):
    """Test creating a table with vector column."""
    # Create table
    await db_connection.execute(f"CREATE TABLE {test_table_name} ...")
    # Test logic here
    # Table automatically dropped after test
```

### 4. Data Fixtures

```python
@pytest.fixture
def sample_texts():
    """Sample texts for embedding and retrieval tests."""
    return [
        "Machine learning is a subset of artificial intelligence.",
        "Python is popular for data science and machine learning.",
        "Neural networks are inspired by the human brain.",
    ]
```

**Usage:**
```python
def test_batch_embedding(self, embedding_model, sample_texts):
    embeddings = embedding_model.encode(sample_texts)
    assert len(embeddings) == len(sample_texts)
```

---

## Async Tests

For testing async functions (database, API calls):

### 1. Basic Async Test

```python
@pytest.mark.asyncio
async def test_database_connection(self, db_params):
    """Test basic database connectivity."""
    conn = None
    try:
        conn = await asyncpg.connect(**db_params)
        assert conn is not None, "Failed to establish database connection"

        # Verify connection is active
        result = await conn.fetchval("SELECT 1")
        assert result == 1, "Database connection not responding correctly"

    finally:
        if conn:
            await conn.close()
```

**Key Components:**
- `@pytest.mark.asyncio` decorator
- `async def` function definition
- `await` for async operations
- Try/finally for cleanup

### 2. Async Test with Async Fixture

```python
@pytest.mark.asyncio
async def test_pgvector_extension(self, db_connection):
    """Test that pgvector extension is installed and available."""
    # db_connection is an async fixture
    await db_connection.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Verify extension exists
    result = await db_connection.fetchval(
        "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'"
    )
    assert result == 1, "pgvector extension is not installed"
```

### 3. Async Test with Multiple Fixtures

```python
@pytest.mark.asyncio
async def test_insert_and_query_vectors(self, db_connection,
                                       test_table_name, cleanup_test_table):
    """Test inserting vectors and performing similarity search."""
    # Create test table
    create_table_query = f"""
    CREATE TABLE {test_table_name} (
        id TEXT PRIMARY KEY,
        text TEXT NOT NULL,
        embedding vector(384)
    );
    """
    await db_connection.execute(create_table_query)

    # Insert test data
    await db_connection.execute(
        f"INSERT INTO {test_table_name} (id, text, embedding) VALUES ($1, $2, $3)",
        "doc1", "Test text", [0.1] * 384
    )

    # Verify insertion
    count = await db_connection.fetchval(f"SELECT COUNT(*) FROM {test_table_name}")
    assert count == 1, "Data not inserted"
```

---

## Assertions

### 1. Basic Assertions

```python
# Equality
assert result == 5, "Result should be 5"

# Inequality
assert result != 0, "Result should not be zero"

# Comparison
assert similarity > 0.5, f"Similarity too low: {similarity}"
assert len(items) >= 3, "Should have at least 3 items"
```

### 2. Boolean Assertions

```python
# Truthiness
assert embedding is not None, "Embedding is None"
assert results, "Results list is empty"

# Type checking
assert isinstance(embedding, np.ndarray), "Should be numpy array"
```

### 3. Collection Assertions

```python
# Length
assert len(embeddings) == 5, f"Expected 5 embeddings, got {len(embeddings)}"

# Membership
assert 'id' in result, "Result missing 'id' field"
assert 'python' in text.lower(), "Text should mention Python"

# All/Any
assert all(x > 0 for x in scores), "All scores should be positive"
assert any('error' in msg for msg in logs), "Should have error message"
```

### 4. Numpy Assertions

```python
import numpy as np

# Array equality
assert np.allclose(embedding1, embedding2, rtol=1e-5), \
    "Same text should produce same embedding"

# Finite values
assert np.all(np.isfinite(embedding)), "Embedding contains non-finite values"

# Not all zeros
assert not np.all(embedding == 0), "Embedding is all zeros"
```

### 5. Exception Assertions

```python
# Expect exception
import pytest

def test_invalid_input():
    with pytest.raises(ValueError):
        process_data(invalid_data)

# Expect exception with message
def test_error_message():
    with pytest.raises(ValueError, match="Invalid format"):
        parse_data("bad format")

# Expect no exception
def test_valid_input():
    try:
        result = process_data(valid_data)
        assert result is not None
    except Exception as e:
        pytest.fail(f"Unexpected exception: {str(e)}")
```

---

## Test Markers

### 1. Asyncio Marker

```python
@pytest.mark.asyncio
async def test_async_operation(self):
    """Test asynchronous operation."""
    result = await async_function()
    assert result is not None
```

### 2. Skip Marker

```python
@pytest.mark.skip(reason="Feature not implemented yet")
def test_future_feature(self):
    """This test will be skipped."""
    pass

@pytest.mark.skipif(sys.version_info < (3, 10),
                    reason="Requires Python 3.10+")
def test_new_syntax(self):
    """Only runs on Python 3.10+"""
    pass
```

### 3. Custom Markers

```python
# Mark slow tests
@pytest.mark.slow
def test_large_dataset(self):
    """This is a slow test."""
    pass

# Mark integration tests
@pytest.mark.integration
async def test_full_pipeline(self):
    """Integration test."""
    pass

# Run with: pytest -m "not slow"  # Skip slow tests
#           pytest -m integration  # Only integration tests
```

### 4. Parametrize Marker

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", 5),
    ("world", 5),
    ("", 0),
])
def test_string_length(input, expected):
    """Test with multiple inputs."""
    assert len(input) == expected

# Same test runs 3 times with different inputs
```

---

## Best Practices

### 1. Descriptive Test Names

```python
# Good
def test_embedding_returns_384_dimensional_vector(self):
    """Test that embedding model returns 384-dimensional vectors."""
    pass

# Bad
def test_embed(self):
    pass
```

### 2. One Concept Per Test

```python
# Good - Test one thing
def test_database_connection(self):
    """Test basic database connectivity."""
    conn = await connect()
    assert conn is not None

def test_database_query(self):
    """Test database query execution."""
    result = await conn.fetchval("SELECT 1")
    assert result == 1

# Bad - Testing multiple things
def test_database(self):
    """Test database."""
    conn = await connect()
    assert conn is not None
    result = await conn.fetchval("SELECT 1")
    assert result == 1
    # ... many more assertions
```

### 3. Arrange-Act-Assert (AAA) Pattern

```python
def test_similarity_search(self, db_connection, test_table_name):
    """Test vector similarity search."""
    # Arrange - Setup test data
    query_vector = [0.1] * 384
    await db_connection.execute(
        f"INSERT INTO {test_table_name} ...",
        "doc1", "test", query_vector
    )

    # Act - Perform the operation
    results = await db_connection.fetch(
        f"SELECT * FROM {test_table_name} WHERE ..."
    )

    # Assert - Verify results
    assert len(results) > 0
    assert results[0]['id'] == 'doc1'
```

### 4. Use Fixtures for Setup/Teardown

```python
# Good - Use fixtures
def test_with_fixture(self, db_connection):
    """Test using fixture for connection."""
    result = await db_connection.fetchval("SELECT 1")
    assert result == 1
    # Connection automatically closed

# Bad - Manual setup/teardown
def test_manual_setup(self):
    """Test with manual setup."""
    conn = await asyncpg.connect(...)
    try:
        result = await conn.fetchval("SELECT 1")
        assert result == 1
    finally:
        await conn.close()
```

### 5. Clear Assertion Messages

```python
# Good - Clear message
assert len(embeddings) == 5, \
    f"Expected 5 embeddings, got {len(embeddings)}"

# Good - Show actual values
assert similarity > 0.5, \
    f"Similarity too low: {similarity:.3f} (threshold: 0.5)"

# Bad - No message
assert len(embeddings) == 5
```

### 6. Test Edge Cases

```python
def test_empty_input(self, embedding_model):
    """Test handling of empty text."""
    try:
        embedding = embedding_model.encode("")
        assert len(embedding) == 384
    except Exception as e:
        pytest.fail(f"Should handle empty text: {str(e)}")

def test_long_input(self, embedding_model):
    """Test handling of very long text."""
    text = "word " * 10000  # Very long text
    embedding = embedding_model.encode(text)
    assert len(embedding) == 384
```

---

## Complete Test Example

Here's a complete, well-structured test:

```python
"""
Tests for embedding process with sample texts.

These tests verify:
1. Embedding model loading
2. Single text embedding
3. Batch text embedding
4. Embedding consistency
"""
import pytest
import numpy as np
from typing import List


class TestEmbedding:
    """Test suite for embedding generation."""

    def test_single_text_embedding(self, embedding_model):
        """Test embedding generation for a single text.

        Verifies that:
        - Model can encode text
        - Output is correct dimensionality (384)
        - Output is numpy array
        - Values are finite and non-zero
        """
        # Arrange
        text = "Machine learning is a subset of artificial intelligence."

        # Act
        embedding = embedding_model.encode(text)

        # Assert - Check basic properties
        assert embedding is not None, "Embedding is None"
        assert len(embedding) == 384, \
            f"Expected 384 dimensions, got {len(embedding)}"
        assert isinstance(embedding, np.ndarray), \
            "Embedding should be numpy array"

        # Assert - Check values are valid
        assert np.all(np.isfinite(embedding)), \
            "Embedding contains non-finite values"
        assert not np.all(embedding == 0), \
            "Embedding is all zeros"

    @pytest.mark.asyncio
    async def test_embedding_pipeline_integration(self, db_connection,
                                                  test_table_name,
                                                  cleanup_test_table,
                                                  embedding_model):
        """Test end-to-end embedding pipeline with database storage.

        Tests the complete workflow:
        1. Create test table
        2. Generate embeddings
        3. Store in database
        4. Verify storage
        5. Test similarity search
        """
        # Arrange - Create test table
        create_table_query = f"""
        CREATE TABLE {test_table_name} (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            embedding vector(384)
        );
        """
        await db_connection.execute(create_table_query)

        # Arrange - Prepare test data
        test_texts = [
            "Python is great for machine learning.",
            "Vector databases enable semantic search."
        ]

        # Act - Generate embeddings
        embeddings = embedding_model.encode(test_texts)

        # Act - Store in database
        for i, (text, embedding) in enumerate(zip(test_texts, embeddings)):
            embedding_list = embedding.tolist()
            await db_connection.execute(
                f"INSERT INTO {test_table_name} (id, text, embedding) VALUES ($1, $2, $3)",
                f"doc_{i}", text, embedding_list
            )

        # Assert - Verify storage
        count = await db_connection.fetchval(
            f"SELECT COUNT(*) FROM {test_table_name}"
        )
        assert count == len(test_texts), \
            f"Expected {len(test_texts)} rows, found {count}"

        # Act - Test similarity search
        query = "What is used for semantic search?"
        query_embedding = embedding_model.encode(query).tolist()

        results = await db_connection.fetch(
            f"""
            SELECT id, text, (1 - (embedding <=> $1)) as similarity
            FROM {test_table_name}
            ORDER BY embedding <=> $1
            LIMIT 3
            """,
            query_embedding
        )

        # Assert - Verify search results
        assert len(results) > 0, "Similarity search returned no results"

        top_result = results[0]
        assert 'vector' in top_result['text'].lower() or \
               'semantic' in top_result['text'].lower(), \
            f"Top result not relevant: {top_result['text']}"
```

---

## Running Tests

### Run All Tests
```bash
pytest test/ -v
```

### Run Specific File
```bash
pytest test/test_embedding.py -v
```

### Run Specific Class
```bash
pytest test/test_embedding.py::TestEmbedding -v
```

### Run Specific Test
```bash
pytest test/test_embedding.py::TestEmbedding::test_single_text_embedding -v
```

### Run with Coverage
```bash
pytest test/ --cov=. --cov-report=html
```

### Run Tests Matching Pattern
```bash
pytest test/ -k "embedding" -v
pytest test/ -k "not slow" -v
```

---

## Summary

**Key Pytest Concepts:**

1. **Test Discovery**: Files and functions starting with `test_`
2. **Fixtures**: Reusable setup code with automatic cleanup
3. **Assertions**: Use `assert` statements with clear messages
4. **Markers**: Categorize tests (`@pytest.mark.asyncio`, custom markers)
5. **Organization**: Group related tests in classes and files
6. **AAA Pattern**: Arrange, Act, Assert for clear test structure

**Test Structure Checklist:**

- ✅ Descriptive test name
- ✅ Docstring explaining what is tested
- ✅ Clear setup (Arrange)
- ✅ Single action being tested (Act)
- ✅ Clear assertions (Assert)
- ✅ Informative assertion messages
- ✅ Proper cleanup (via fixtures)
- ✅ Edge cases covered

For more examples, see:
- [test_embedding.py](test_embedding.py) - Synchronous tests with fixtures
- [test_database_connection.py](test_database_connection.py) - Async tests
- [test_retrieval.py](test_retrieval.py) - Complex integration tests
- [conftest.py](conftest.py) - Fixture definitions
