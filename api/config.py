"""
Configuration management for the RAG application.
Handles environment setup, database configuration, and service initialization.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv, dotenv_values

import logfire
import google.generativeai as genai
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from ingestion.validation.file_validator import FileValidator, FileValidationConfig
from models.models import SimpleRAGResponse

# Disable tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Constants
DEFAULT_TABLE_NAME = "document_chunks"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_CHUNKING_SIMILARITY = 0.5
ALLOWED_CONTENT_TYPES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain'
]


class AppConfig:
    """Global application configuration and service initialization."""

    def __init__(self):
        # Initialize logfire with token from environment
        logfire_token = os.getenv('LOGFIRE_WRITE_TOKEN')
        if logfire_token:
            logfire.configure(token=logfire_token)
            print("✓ Logfire configured successfully")
        else:
            print("⚠️ LOGFIRE_WRITE_TOKEN not found, using default configuration")
            logfire.configure()

        # Database configuration
        db_host = os.getenv('DB_HOST') or os.getenv('POSTGRES_HOST') or 'localhost'
        db_port = os.getenv('DB_PORT') or os.getenv('POSTGRES_PORT') or '5432'
        self.db_params = {
            'host': db_host,
            'port': db_port,
            'dbname': os.getenv('POSTGRES_DB', 'rag_db'),
            'user': os.getenv('POSTGRES_USER', 'admin'),
            'password': os.getenv('POSTGRES_PASSWORD', 'admin')
        }

        # Service initialization (lazy loading for performance)
        self.file_validator = FileValidator(FileValidationConfig())
        self.agent = self._configure_pydantic_ai()
        self.pipeline = None  # Lazy initialization
        self.reranker = None  # Lazy initialization
        self.graph_pool = None  # Lazy initialization

    def _configure_pydantic_ai(self) -> Optional[Agent]:
        """Configure Pydantic AI Agent with Google Gemini."""
        gemini_key = os.getenv('GOOGLE_API_KEY')
        gemini_model = os.getenv('GEMINI_MODEL')

        if gemini_key:
            try:
                # Configure Pydantic AI Agent with GoogleProvider
                provider = GoogleProvider(api_key=gemini_key)
                model = GoogleModel(gemini_model, provider=provider)

                # Create agent with system prompt and output type
                agent = Agent(
                    model,
                    output_type=SimpleRAGResponse,
                    system_prompt="""You are a helpful RAG (Retrieval-Augmented Generation) assistant.
                    Based on the provided context from document search, provide comprehensive answers to user questions.

                    Instructions:
                    - Answer directly and accurately based on the provided context
                    - If the context doesn't fully answer the question, clearly state what information is available
                    - Cite specific sources when making claims, including page numbers when available (e.g., "according to Source 1, Page 5")
                    - Be concise but thorough
                    - Provide a confidence score (0-1) based on how well the context answers the question

                    Respond with:
                    - answer: Your comprehensive response with page references
                    - confidence: Float between 0-1 indicating confidence in the answer
                    - word_count: Number of words in your answer
                    - sources_used: Number of sources used (will be provided)
                    - metadata: Any additional relevant information"""
                )

                print("✓ Pydantic AI Agent configured successfully")
                return agent
            except Exception as e:
                print(f"❌ Pydantic AI configuration failed: {e}")
                # Fallback to direct genai for backward compatibility
                try:
                    genai.configure(api_key=gemini_key)
                    print("✓ Fallback to direct Gemini API")
                except Exception as fallback_error:
                    print(f"❌ Gemini fallback also failed: {fallback_error}")
        return None


def load_environment():
    """Load environment variables from .env file."""
    # Load from project root .env file
    project_root = Path(__file__).parent.parent
    env_path = project_root / '.env'
    load_dotenv(env_path)

    # Docker compose injects empty strings when variables aren't defined, so reapply
    # values from the env file for any unset/blank environment variables.
    if env_path.exists():
        for key, value in dotenv_values(str(env_path)).items():
            if (os.getenv(key) in (None, "")) and value is not None:
                os.environ[key] = value


def get_gemini_model() -> str:
    """Get the configured Gemini model name."""
    return os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')


# Initialize environment on module import
load_environment()

# Add project root to path for models
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))
