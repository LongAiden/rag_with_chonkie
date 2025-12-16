"""
Configuration for Graph and Entity Extraction.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class GraphConfig(BaseSettings):
    """Graph and entity extraction configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ============================================
    # LLM Configuration
    # ============================================
    gemini_api_key: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""),
        description="Gemini API key for entity/relationship extraction"
    )
    gemini_model: str = Field(
        default=os.getenv("GEMINI_MODEL", ""),
        description="Gemini model to use for extraction"
    )

    # ============================================
    # Entity Extraction Configuration
    # ============================================
    entity_confidence_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for entity extraction (0-1)"
    )
    entity_extraction_enabled: bool = Field(
        default=True,
        description="Enable automatic entity extraction"
    )
    max_entities_per_chunk: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of entities to extract per chunk"
    )

    # ============================================
    # Relationship Extraction Configuration
    # ============================================
    relationship_confidence_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for relationship extraction (0-1)"
    )
    relationship_extraction_enabled: bool = Field(
        default=True,
        description="Enable automatic relationship extraction"
    )
    max_relationships_per_chunk: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of relationships to extract per chunk"
    )

    # ============================================
    # Graph Algorithm Configuration
    # ============================================
    default_max_hops: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Default maximum hops for connected entity queries"
    )
    pagerank_damping_factor: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Damping factor for PageRank algorithm"
    )
    pagerank_max_iterations: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum iterations for PageRank algorithm"
    )

    # ============================================
    # Vector Embedding Configuration
    # ============================================
    entity_embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="SentenceTransformer model for entity embeddings"
    )
    entity_embedding_dimension: int = Field(
        default=384,
        description="Dimension of entity embeddings (must match model)"
    )

    # ============================================
    # Batch Processing Configuration
    # ============================================
    batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of chunks to process in batch extraction"
    )
    enable_parallel_extraction: bool = Field(
        default=True,
        description="Enable parallel processing for batch extraction"
    )

    # ============================================
    # Entity Type Filtering
    # ============================================
    enabled_entity_types: List[str] = Field(
        default=[
            "ALGORITHM", "MODEL", "ARCHITECTURE", "TECHNIQUE",
            "DATASET", "METRIC", "TASK", "FRAMEWORK",
            "LAYER", "ACTIVATION", "LOSS_FUNCTION", "OPTIMIZER",
            "CONCEPT", "PAPER", "RESEARCHER", "ORGANIZATION"
        ],
        description="Enabled entity types for extraction (empty = all enabled)"
    )

    # ============================================
    # Relationship Type Filtering
    # ============================================
    enabled_relationship_types: List[str] = Field(
        default=[
            "USES", "TRAINED_ON", "IMPROVES", "OUTPERFORMS",
            "PART_OF", "BASED_ON", "IS_A", "EXTENDS",
            "SOLVES", "ADDRESSES", "EVALUATED_ON", "IMPLEMENTS"
        ],
        description="Enabled relationship types (empty = all enabled)"
    )

    # ============================================
    # Database Configuration
    # ============================================
    db_pool_min_size: int = Field(
        default=2,
        ge=1,
        description="Minimum database connection pool size"
    )
    db_pool_max_size: int = Field(
        default=10,
        ge=2,
        description="Maximum database connection pool size"
    )
    db_pool_timeout: float = Field(
        default=30.0,
        ge=1.0,
        description="Database connection timeout in seconds"
    )

    # ============================================
    # Performance Configuration
    # ============================================
    enable_entity_caching: bool = Field(
        default=True,
        description="Enable caching for entity lookups"
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        description="Cache time-to-live in seconds (1 hour default)"
    )

    # ============================================
    # Logging Configuration
    # ============================================
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_entity_extraction: bool = Field(
        default=True,
        description="Log entity extraction details"
    )
    log_relationship_extraction: bool = Field(
        default=True,
        description="Log relationship extraction details"
    )

    # (rest unchanged)


_graph_config: Optional[GraphConfig] = None


def get_graph_config() -> GraphConfig:
    """Get the graph configuration singleton."""
    global _graph_config
    if _graph_config is None:
        _graph_config = GraphConfig()
    return _graph_config


# Export the config instance
graph_config = get_graph_config()


# ============================================
# Helper Functions
# ============================================

def is_entity_type_enabled(entity_type: str) -> bool:
    """Check if an entity type is enabled."""
    config = get_graph_config()
    if not config.enabled_entity_types:
        return True  # All enabled if list is empty
    return entity_type.upper() in [t.upper() for t in config.enabled_entity_types]


def is_relationship_type_enabled(relationship_type: str) -> bool:
    """Check if a relationship type is enabled."""
    config = get_graph_config()
    if not config.enabled_relationship_types:
        return True  # All enabled if list is empty
    return relationship_type.upper() in [t.upper() for t in config.enabled_relationship_types]


def get_extraction_config() -> dict:
    """Get extraction configuration as dictionary."""
    config = get_graph_config()
    return {
        "entity_confidence_threshold": config.entity_confidence_threshold,
        "relationship_confidence_threshold": config.relationship_confidence_threshold,
        "max_entities_per_chunk": config.max_entities_per_chunk,
        "max_relationships_per_chunk": config.max_relationships_per_chunk,
        "enabled_entity_types": config.enabled_entity_types,
        "enabled_relationship_types": config.enabled_relationship_types,
    }


# ============================================
# Environment Variables Reference
# ============================================
"""
Add these to your .env file:

# Graph Configuration
ENTITY_CONFIDENCE_THRESHOLD=0.6
RELATIONSHIP_CONFIDENCE_THRESHOLD=0.6
MAX_ENTITIES_PER_CHUNK=50
MAX_RELATIONSHIPS_PER_CHUNK=100
DEFAULT_MAX_HOPS=2

# LLM Configuration
GOOGLE_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash

# Performance
BATCH_SIZE=10
ENABLE_PARALLEL_EXTRACTION=true
ENABLE_ENTITY_CACHING=true
CACHE_TTL_SECONDS=3600

# Logging
LOG_LEVEL=INFO
LOG_ENTITY_EXTRACTION=true
LOG_RELATIONSHIP_EXTRACTION=true
"""
