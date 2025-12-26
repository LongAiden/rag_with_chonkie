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

    # Determine chunker type
    if chunker_type is None:
        chunker_type = os.getenv("CHUNKER_TYPE", "recursive").lower()
    else:
        chunker_type = chunker_type.lower()

    # Create appropriate chunker
    if chunker_type == ChunkerType.TOKEN.value:
        print(f"Using TokenChunker (fastest, simple token-based)")
        return TokenChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    elif chunker_type == ChunkerType.RECURSIVE.value:
        print(f"Using RecursiveChunker (balanced, respects boundaries)")
        return RecursiveChunker(
            chunk_size=chunk_size
        )

    elif chunker_type == ChunkerType.SEMANTIC.value:
        print(f"Using SemanticChunker (highest quality, slowest)")
        return SemanticChunker(
            chunk_size=chunk_size,
            threshold=similarity_threshold,
            embedding_model=embedding_model or "sentence-transformers/all-MiniLM-L6-v2"
        )

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
