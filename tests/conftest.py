"""
Pytest configuration and fixtures for RAG with Llama testing.

This file provides shared fixtures and configuration for all tests.
"""
import os
import pytest
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def project_root_path():
    """Return the project root path."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def fixtures_path():
    """Return the path to test fixtures."""
    return Path(__file__).parent / "fixtures"


# Sample test data
@pytest.fixture
def sample_texts():
    """Sample texts for embedding and retrieval tests."""
    return [
        "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
        "Python is a popular programming language for data science and machine learning applications.",
        "Neural networks are computational models inspired by the human brain structure.",
        "Natural language processing allows computers to understand and generate human language.",
        "The quick brown fox jumps over the lazy dog."
    ]


@pytest.fixture
def sample_queries():
    """Sample queries for retrieval tests."""
    return [
        "What is machine learning?",
        "Tell me about Python programming",
        "How do neural networks work?"
    ]
