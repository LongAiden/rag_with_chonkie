"""
Integration test fixtures.

These fixtures require external dependencies like databases and API connections.
"""
import os
import sys
import pytest
import asyncio
import asyncpg
from pathlib import Path
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
env_path = project_root / '.env'
load_dotenv(env_path)


@pytest.fixture(scope="session")
def db_params():
    """Database connection parameters from environment variables."""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'rag_db'),
        'user': os.getenv('POSTGRES_USER', 'admin'),
        'password': os.getenv('POSTGRES_PASSWORD', 'admin')
    }


@pytest.fixture(scope="session")
def gemini_api_key():
    """Gemini API key from environment variables."""
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key or api_key == 'your-google-api-key-here':
        pytest.skip("GOOGLE_API_KEY not configured in .env file")
    return api_key


@pytest.fixture(scope="session")
def gemini_model():
    """Gemini model name from environment variables."""
    return os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')


@pytest.fixture(scope="session")
def logfire_token():
    """Logfire write token from environment variables."""
    return os.getenv('LOGFIRE_WRITE_TOKEN', '')


@pytest.fixture(scope="session")
def embedding_model():
    """Shared embedding model for tests (loaded once per session)."""
    model_name = os.getenv('ENTITY_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    return SentenceTransformer(model_name)


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


@pytest.fixture
async def test_table_name():
    """Generate a unique test table name."""
    import uuid
    return f"test_chunks_{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def cleanup_test_table(db_connection, test_table_name):
    """Cleanup fixture that drops the test table after the test."""
    yield
    # Cleanup: drop test table
    try:
        await db_connection.execute(f"DROP TABLE IF EXISTS {test_table_name};")
    except Exception as e:
        print(f"Warning: Could not drop test table {test_table_name}: {e}")
