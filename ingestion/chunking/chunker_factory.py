"""
Chunking Strategy Factory
Provides multiple chunking strategies with a unified interface.

Strategies:
- TokenChunker: Fastest, simple token-based chunking
- RecursiveChunker: Balanced, respects text boundaries (DEFAULT)
- SemanticChunker: Highest quality, AI-powered (slowest)
"""

from enum import Enum
from typing import List, Optional
import os


class ChunkerType(Enum):
    """Available chunking strategies."""
    TOKEN = "token"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"


def get_chunker(
    chunker_type: Optional[str] = None,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    similarity_threshold: float = 0.5,
    embedding_model: Optional[str] = None
):
    """
    Factory function to create the appropriate chunker.

    Args:
        chunker_type: Type of chunker ("token", "recursive", "semantic")
                     If None, uses CHUNKER_TYPE env var or defaults to "recursive"
        chunk_size: Maximum tokens per chunk
        chunk_overlap: Number of overlapping tokens/sentences
        similarity_threshold: For semantic chunker only (0-1)
        embedding_model: For semantic chunker only

    Returns:
        Configured chunker instance

    Examples:
        >>> # Use default (recursive)
        >>> chunker = get_chunker(chunk_size=512)

        >>> # Use token chunker explicitly
        >>> chunker = get_chunker("token", chunk_size=512)

        >>> # Use semantic chunker
        >>> chunker = get_chunker("semantic", chunk_size=512, similarity_threshold=0.3)
    """
    from chonkie import TokenChunker, RecursiveChunker, SemanticChunker

    # Global cache for heavy chunkers
    global _CHUNKER_CACHE
    if not '_CHUNKER_CACHE' in globals():
        _CHUNKER_CACHE = {}

    # Determine chunker type
    if chunker_type is None:
        chunker_type = os.getenv("CHUNKER_TYPE", "recursive").lower()
    else:
        chunker_type = chunker_type.lower()

    # Create appropriate chunker
    if chunker_type == ChunkerType.TOKEN.value:
        # Token chunker is lightweight, no need to cache aggressively but we can consistency
        return TokenChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    elif chunker_type == ChunkerType.RECURSIVE.value:
        # Recursive chunker is also lightweight
        return RecursiveChunker(
            chunk_size=chunk_size
        )

    elif chunker_type == ChunkerType.SEMANTIC.value:
        # Semantic chunker is HEAVY (loads models). Must cache.
        embedding_model_name = embedding_model or "sentence-transformers/all-MiniLM-L6-v2"
        cache_key = f"semantic_{chunk_size}_{similarity_threshold}_{embedding_model_name}"
        
        if cache_key in _CHUNKER_CACHE:
            return _CHUNKER_CACHE[cache_key]
            
        print(f"Initializing SemanticChunker (loading model: {embedding_model_name})...")
        chunker = SemanticChunker(
            chunk_size=chunk_size,
            threshold=similarity_threshold,
            embedding_model=embedding_model_name
        )
        _CHUNKER_CACHE[cache_key] = chunker
        return chunker

    else:
        raise ValueError(
            f"Invalid chunker_type: {chunker_type}. "
            f"Must be one of: {[e.value for e in ChunkerType]}"
        )


def chunk_text(
    text: str,
    chunker_type: Optional[str] = None,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    similarity_threshold: float = 0.5,
    embedding_model: Optional[str] = None
) -> List:
    """
    Convenience function to chunk text with the specified strategy.

    Args:
        text: Text to chunk
        chunker_type: Type of chunker (None = use default/env var)
        chunk_size: Maximum tokens per chunk
        chunk_overlap: Overlap size
        similarity_threshold: For semantic chunker
        embedding_model: For semantic chunker

    Returns:
        List of chunks

    Examples:
        >>> chunks = chunk_text(document_text)  # Uses default (recursive)
        >>> chunks = chunk_text(document_text, chunker_type="token")  # Fast
        >>> chunks = chunk_text(document_text, chunker_type="semantic")  # Quality
    """
    chunker = get_chunker(
        chunker_type=chunker_type,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        similarity_threshold=similarity_threshold,
        embedding_model=embedding_model
    )

    return chunker.chunk(text)
