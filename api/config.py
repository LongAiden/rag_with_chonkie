"""
Re-export shim - configuration has moved to config/app_config.py.
"""
from config.app_config import (
    AppConfig,
    AppSettings,
    DatabaseConfig,
    DEFAULT_TABLE_NAME,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_CHUNKING_SIMILARITY,
    ALLOWED_CONTENT_TYPES,
    get_gemini_model,
)

__all__ = [
    "AppConfig",
    "AppSettings",
    "DatabaseConfig",
    "DEFAULT_TABLE_NAME",
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_CHUNKING_SIMILARITY",
    "ALLOWED_CONTENT_TYPES",
    "get_gemini_model",
]
