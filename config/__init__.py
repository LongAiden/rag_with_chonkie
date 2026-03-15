"""
Configuration module for the RAG application.
"""

from .graph_config import (
    GraphConfig,
    get_graph_config,
    graph_config,
    is_entity_type_enabled,
    is_relationship_type_enabled,
    get_extraction_config,
)
from .app_config import (
    AppConfig,
    AppSettings,
    DatabaseConfig,
    DEFAULT_TABLE_NAME,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_CHUNKING_SIMILARITY,
    ALLOWED_CONTENT_TYPES,
    get_ollama_model,
)

__all__ = [
    "GraphConfig",
    "get_graph_config",
    "graph_config",
    "is_entity_type_enabled",
    "is_relationship_type_enabled",
    "get_extraction_config",
    "AppConfig",
    "AppSettings",
    "DatabaseConfig",
    "DEFAULT_TABLE_NAME",
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_CHUNKING_SIMILARITY",
    "ALLOWED_CONTENT_TYPES",
    "get_ollama_model",
]
