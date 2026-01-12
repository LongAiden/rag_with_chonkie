"""
Text chunking and semantic processing.
"""

from .chunker_factory import (
    get_chunker,
    chunk_text,
    ChunkerType,
    LARGE_DOCUMENT_THRESHOLD_CHARS,
)

__all__ = [
    'get_chunker',
    'chunk_text',
    'ChunkerType',
    'LARGE_DOCUMENT_THRESHOLD_CHARS',
]
