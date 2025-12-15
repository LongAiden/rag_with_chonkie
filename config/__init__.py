"""
Configuration module for RAG + Knowledge Graph.
"""

from .graph_config import (
    GraphConfig,
    get_graph_config,
    graph_config,
    is_entity_type_enabled,
    is_relationship_type_enabled,
    get_extraction_config,
)

__all__ = [
    "GraphConfig",
    "get_graph_config",
    "graph_config",
    "is_entity_type_enabled",
    "is_relationship_type_enabled",
    "get_extraction_config",
]
