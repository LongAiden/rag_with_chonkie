"""
Unit tests for ChunkerFactory.

Tests:
1. Chunker type validation (token, recursive, semantic)
2. Invalid chunker type handling
3. Text length with numeric values (adaptive selection)
4. Text length with non-numeric/None values
5. Chunker caching behavior
"""
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import directly from the module to avoid cascade through __init__.py
from ingestion.chunking.chunker_factory import (
    get_chunker,
    chunk_text,
    ChunkerType,
    LARGE_DOCUMENT_THRESHOLD_CHARS,
    _CHUNKER_CACHE
)


class TestChunkerType:
    """Tests for ChunkerType enum."""

    def test_chunker_type_values(self):
        """Test that ChunkerType enum has correct values."""
        assert ChunkerType.TOKEN.value == "token"
        assert ChunkerType.RECURSIVE.value == "recursive"
        assert ChunkerType.SEMANTIC.value == "semantic"

    def test_chunker_type_count(self):
        """Test that ChunkerType has exactly 3 types."""
        assert len(ChunkerType) == 3


class TestGetChunker:
    """Tests for get_chunker factory function."""

    def test_get_token_chunker(self):
        """Test getting a token chunker."""
        chunker = get_chunker(chunker_type="token", chunk_size=512)
        assert chunker is not None
        # Verify it's a TokenChunker by checking class name
        assert "TokenChunker" in type(chunker).__name__

    def test_get_recursive_chunker(self):
        """Test getting a recursive chunker."""
        chunker = get_chunker(chunker_type="recursive", chunk_size=512)
        assert chunker is not None
        assert "RecursiveChunker" in type(chunker).__name__

    def test_get_semantic_chunker(self):
        """Test getting a semantic chunker."""
        chunker = get_chunker(chunker_type="semantic", chunk_size=512)
        assert chunker is not None
        assert "SemanticChunker" in type(chunker).__name__

    def test_invalid_chunker_type_raises_error(self):
        """Test that invalid chunker type raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            get_chunker(chunker_type="invalid_type")
        assert "Invalid chunker_type" in str(excinfo.value)

    def test_default_chunker_is_recursive(self):
        """Test that default chunker (when not specified) is recursive."""
        # Clear any env var that might override this
        with patch.dict(os.environ, {"CHUNKER_TYPE": "recursive"}, clear=False):
            chunker = get_chunker(chunk_size=512)
            assert "RecursiveChunker" in type(chunker).__name__

    def test_chunker_type_case_insensitive(self):
        """Test that chunker type is case insensitive."""
        chunker_upper = get_chunker(chunker_type="TOKEN")
        chunker_lower = get_chunker(chunker_type="token")
        chunker_mixed = get_chunker(chunker_type="ToKeN")
        
        assert type(chunker_upper).__name__ == type(chunker_lower).__name__
        assert type(chunker_upper).__name__ == type(chunker_mixed).__name__


class TestTextLengthAdaptiveSelection:
    """Tests for text length-based adaptive chunker selection."""

    def test_large_document_forces_recursive(self):
        """Test that large documents force RecursiveChunker even when semantic is requested."""
        large_text_length = LARGE_DOCUMENT_THRESHOLD_CHARS + 1  # > 100KB
        
        chunker = get_chunker(
            chunker_type="semantic",
            text_length=large_text_length
        )
        # Should switch to RecursiveChunker for performance
        assert "RecursiveChunker" in type(chunker).__name__

    def test_small_document_allows_semantic(self):
        """Test that small documents can use SemanticChunker."""
        small_text_length = LARGE_DOCUMENT_THRESHOLD_CHARS - 1  # < 100KB
        
        chunker = get_chunker(
            chunker_type="semantic",
            text_length=small_text_length
        )
        assert "SemanticChunker" in type(chunker).__name__

    def test_none_text_length_no_error(self):
        """Test that None text_length doesn't cause errors."""
        chunker = get_chunker(chunker_type="recursive", text_length=None)
        assert chunker is not None

    def test_zero_text_length_no_error(self):
        """Test that zero text_length doesn't cause errors."""
        chunker = get_chunker(chunker_type="recursive", text_length=0)
        assert chunker is not None

    def test_negative_text_length_no_error(self):
        """Test that negative text_length doesn't cause errors."""
        chunker = get_chunker(chunker_type="recursive", text_length=-100)
        assert chunker is not None

    def test_boundary_text_length(self):
        """Test behavior at exactly the threshold."""
        # At exactly threshold, should NOT switch (uses <= comparison)
        chunker = get_chunker(
            chunker_type="semantic",
            text_length=LARGE_DOCUMENT_THRESHOLD_CHARS
        )
        # At exactly threshold, should still use semantic
        assert "SemanticChunker" in type(chunker).__name__


class TestChunkerCaching:
    """Tests for chunker caching behavior."""

    def test_same_params_return_cached_chunker(self):
        """Test that same parameters return the same cached chunker instance."""
        chunker1 = get_chunker(chunker_type="token", chunk_size=256, chunk_overlap=25)
        chunker2 = get_chunker(chunker_type="token", chunk_size=256, chunk_overlap=25)
        
        # Should be the exact same instance
        assert chunker1 is chunker2

    def test_different_params_return_different_chunker(self):
        """Test that different parameters return different chunker instances."""
        chunker1 = get_chunker(chunker_type="token", chunk_size=256)
        chunker2 = get_chunker(chunker_type="token", chunk_size=512)
        
        # Should NOT be the same instance (different chunk_size)
        assert chunker1 is not chunker2


class TestChunkText:
    """Tests for chunk_text convenience function."""

    def test_chunk_text_returns_list(self, small_text):
        """Test that chunk_text returns a list of chunks."""
        chunks = chunk_text(small_text, chunker_type="recursive", chunk_size=128)
        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_chunk_text_with_token_chunker(self, small_text):
        """Test chunk_text with token chunker."""
        chunks = chunk_text(small_text, chunker_type="token", chunk_size=50)
        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_chunk_text_empty_string(self):
        """Test chunk_text with empty string."""
        chunks = chunk_text("", chunker_type="recursive")
        assert isinstance(chunks, list)

    def test_chunk_text_single_word(self):
        """Test chunk_text with a single word."""
        chunks = chunk_text("Hello", chunker_type="recursive", chunk_size=512)
        assert isinstance(chunks, list)
        assert len(chunks) >= 1
