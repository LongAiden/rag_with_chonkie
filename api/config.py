"""
Configuration management for the RAG application.
Handles environment setup, database configuration, and service initialization.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

import logfire
import google.generativeai as genai
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from ingestion.validation.file_validator import FileValidator, FileValidationConfig
from models.models import SimpleRAGResponse

# Constants
DEFAULT_TABLE_NAME = "document_chunks"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_CHUNKING_SIMILARITY = 0.5
ALLOWED_CONTENT_TYPES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain'
]


class DatabaseConfig(BaseSettings):
    """Database configuration using pydantic-settings."""
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # Database settings with fallback aliases
    host: str = Field(default='localhost', validation_alias='POSTGRES_HOST')
    port: str = Field(default='5432', validation_alias='POSTGRES_PORT')
    dbname: str = Field(default='rag_db', validation_alias='POSTGRES_DB')
    user: str = Field(default='admin', validation_alias='POSTGRES_USER')
    password: str = Field(default='admin', validation_alias='POSTGRES_PASSWORD')

    def to_dict(self):
        """Convert to dictionary format for psycopg2/asyncpg."""
        return {
            'host': self.host,
            'port': self.port,
            'dbname': self.dbname,
            'user': self.user,
            'password': self.password
        }


class AppSettings(BaseSettings):
    """Application settings using pydantic-settings."""
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # Logfire
    logfire_write_token: Optional[str] = Field(default=None, validation_alias='LOGFIRE_WRITE_TOKEN')

    # Gemini/Google AI
    google_api_key: Optional[str] = Field(default=None, validation_alias='GOOGLE_API_KEY')
    gemini_model: str = Field(default='gemini-1.5-flash', validation_alias='GEMINI_MODEL')

    # Embedding
    embedding_model: str = Field(default=DEFAULT_EMBEDDING_MODEL)

    # Table
    table_name: str = Field(default=DEFAULT_TABLE_NAME)


class AppConfig:
    """Global application configuration and service initialization."""

    def __init__(self, settings: Optional[AppSettings] = None, db_config: Optional[DatabaseConfig] = None):
        # Disable tokenizers parallelism warning
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

        # Load settings
        self.settings = settings or AppSettings()
        self.db_config = db_config or DatabaseConfig()

        # Initialize logfire
        self._configure_logfire()

        # Database configuration (backward compatible dict format)
        self.db_params = self.db_config.to_dict()

        # Service initialization (lazy loading for performance)
        self.file_validator = FileValidator(FileValidationConfig())
        self.agent = self._configure_pydantic_ai()
        self.pipeline = None  # Lazy initialization
        self.reranker = None  # Lazy initialization
        self.graph_pool = None  # Lazy initialization

    def _configure_logfire(self):
        """Configure logfire with token from settings."""
        if self.settings.logfire_write_token:
            logfire.configure(token=self.settings.logfire_write_token)
            print("✓ Logfire configured successfully")
        else:
            print("⚠️ LOGFIRE_WRITE_TOKEN not found, using default configuration")
            logfire.configure()

    def _configure_pydantic_ai(self) -> Optional[Agent]:
        """Configure Pydantic AI Agent with Google Gemini."""
        if self.settings.google_api_key:
            try:
                # Configure Pydantic AI Agent with GoogleProvider
                provider = GoogleProvider(api_key=self.settings.google_api_key)
                model = GoogleModel(self.settings.gemini_model, provider=provider)

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

                    Use Graph Entities for Enhanced Understanding:
                    - Graph entities are structured concepts extracted from each source (e.g., "BERT (MODEL)", "LoRA (FINE_TUNING_METHOD)")
                    - These entities provide semantic understanding of technical terms, models, methods, and concepts
                    - Leverage entity types (MODEL, ARCHITECTURE, TOKENIZER, etc.) to provide more accurate, contextual answers
                    - When discussing technical concepts, reference their entity type to clarify what they are

                    - Be concise but thorough
                    - Provide a confidence score (0-1) based on how well the context answers the question

                    Respond with:
                    - answer: Your comprehensive response with page references and entity-aware explanations
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
                    genai.configure(api_key=self.settings.google_api_key)
                    print("✓ Fallback to direct Gemini API")
                except Exception as fallback_error:
                    print(f"❌ Gemini fallback also failed: {fallback_error}")
        return None


def get_gemini_model() -> str:
    """Get the configured Gemini model name."""
    settings = AppSettings()
    return settings.gemini_model
