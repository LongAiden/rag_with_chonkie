"""
Unit tests for EmbeddingGenerator.

Tests:
1. Model initialization
2. Single text embedding (embed_text)
3. Batch embedding (embed_batch)
4. Empty text handling
5. Embedding dimensions
6. Batch size handling
"""
import sys
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import directly from module to avoid cascade through __init__.py
from ingestion.embedding.vector_store import EmbeddingGenerator


class TestEmbeddingGeneratorInitialization:
    """Tests for EmbeddingGenerator initialization."""

    def test_default_model_initialization(self):
        """Test that default model is loaded correctly."""
        generator = EmbeddingGenerator()
        
        assert generator is not None
        assert generator.model is not None

    def test_custom_model_initialization(self):
        """Test initialization with custom model name."""
        generator = EmbeddingGenerator(model_name='all-MiniLM-L6-v2')
        
        assert generator is not None
        # Model dimension for all-MiniLM-L6-v2 is 384
        assert generator.embedding_dim == 384

    def test_embedding_dimension_attribute(self):
        """Test that embedding dimension is correctly set."""
        generator = EmbeddingGenerator()
        
        assert hasattr(generator, 'embedding_dim')
        assert isinstance(generator.embedding_dim, int)
        assert generator.embedding_dim > 0


class TestEmbedText:
    """Tests for embed_text method."""

    @pytest.fixture
    def generator(self):
        """Create an EmbeddingGenerator instance."""
        return EmbeddingGenerator()

    def test_embed_single_text(self, generator):
        """Test embedding a single text."""
        text = "This is a test sentence."
        
        embedding = generator.embed_text(text)
        
        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) == generator.embedding_dim

    def test_embed_text_returns_floats(self, generator):
        """Test that embedding values are floats."""
        text = "Test text"
        
        embedding = generator.embed_text(text)
        
        assert all(isinstance(x, float) for x in embedding)

    def test_embed_same_text_produces_same_embedding(self, generator):
        """Test that same text produces same embedding."""
        text = "Consistent embedding test"
        
        embedding1 = generator.embed_text(text)
        embedding2 = generator.embed_text(text)
        
        # Should be identical (or very close due to floating point)
        np.testing.assert_array_almost_equal(embedding1, embedding2)

    def test_embed_different_texts_produce_different_embeddings(self, generator):
        """Test that different texts produce different embeddings."""
        text1 = "Machine learning is amazing"
        text2 = "The weather is sunny today"
        
        embedding1 = generator.embed_text(text1)
        embedding2 = generator.embed_text(text2)
        
        # Should not be identical
        assert not np.allclose(embedding1, embedding2)


class TestEmbedBatch:
    """Tests for embed_batch method."""

    @pytest.fixture
    def generator(self):
        """Create an EmbeddingGenerator instance."""
        return EmbeddingGenerator()

    def test_embed_batch_returns_list(self, generator, sample_chunk_texts):
        """Test that embed_batch returns a list of embeddings."""
        embeddings = generator.embed_batch(sample_chunk_texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == len(sample_chunk_texts)

    def test_embed_batch_correct_dimensions(self, generator, sample_chunk_texts):
        """Test that each embedding in batch has correct dimensions."""
        embeddings = generator.embed_batch(sample_chunk_texts)
        
        for embedding in embeddings:
            assert len(embedding) == generator.embedding_dim

    def test_embed_batch_single_text(self, generator):
        """Test embed_batch with single text in list."""
        texts = ["Single text"]
        
        embeddings = generator.embed_batch(texts)
        
        assert len(embeddings) == 1
        assert len(embeddings[0]) == generator.embedding_dim

    def test_embed_batch_empty_list(self, generator):
        """Test embed_batch with empty list."""
        embeddings = generator.embed_batch([])
        
        assert embeddings == [] or len(embeddings) == 0


class TestEmptyAndEdgeCases:
    """Tests for empty and edge case inputs."""

    @pytest.fixture
    def generator(self):
        """Create an EmbeddingGenerator instance."""
        return EmbeddingGenerator()

    def test_embed_empty_string(self, generator):
        """Test embedding empty string."""
        embedding = generator.embed_text("")
        
        # Should still return an embedding (model handles empty strings)
        assert embedding is not None
        assert len(embedding) == generator.embedding_dim

    def test_embed_whitespace_only(self, generator):
        """Test embedding whitespace-only string."""
        embedding = generator.embed_text("   ")
        
        assert embedding is not None
        assert len(embedding) == generator.embedding_dim

    def test_embed_very_long_text(self, generator):
        """Test embedding very long text."""
        long_text = "word " * 1000  # ~5000 characters
        
        embedding = generator.embed_text(long_text)
        
        # Should handle gracefully (model truncates if needed)
        assert embedding is not None
        assert len(embedding) == generator.embedding_dim

    def test_embed_special_characters(self, generator):
        """Test embedding text with special characters."""
        special_text = "α β γ δ ε → ← ∑ ∫ © ® ™ € £ ¥"
        
        embedding = generator.embed_text(special_text)
        
        assert embedding is not None
        assert len(embedding) == generator.embedding_dim

    def test_embed_unicode_text(self, generator):
        """Test embedding Unicode text."""
        unicode_text = "日本語テスト 中文测试 한국어 테스트"
        
        embedding = generator.embed_text(unicode_text)
        
        assert embedding is not None
        assert len(embedding) == generator.embedding_dim


class TestEmbeddingNormalization:
    """Tests for embedding normalization properties."""

    @pytest.fixture
    def generator(self):
        """Create an EmbeddingGenerator instance."""
        return EmbeddingGenerator()

    def test_embeddings_are_normalized(self, generator):
        """Test that embeddings are normalized (L2 norm ≈ 1)."""
        text = "Test text for normalization"
        
        embedding = generator.embed_text(text)
        
        # Calculate L2 norm
        norm = np.linalg.norm(embedding)
        
        # Sentence transformers typically return normalized embeddings
        # Allow some tolerance
        assert np.isclose(norm, 1.0, atol=0.1), f"L2 norm is {norm}, expected ~1.0"


class TestBatchProcessingPerformance:
    """Tests for batch processing efficiency."""

    @pytest.fixture
    def generator(self):
        """Create an EmbeddingGenerator instance."""
        return EmbeddingGenerator()

    def test_batch_processing_returns_correct_count(self, generator):
        """Test that batch processing returns correct number of embeddings."""
        batch_sizes = [1, 5, 10, 20]
        
        for size in batch_sizes:
            texts = [f"Text number {i}" for i in range(size)]
            embeddings = generator.embed_batch(texts)
            
            assert len(embeddings) == size, f"Expected {size} embeddings, got {len(embeddings)}"

    def test_batch_vs_individual_consistency(self, generator):
        """Test that batch and individual embeddings are consistent."""
        texts = ["First text", "Second text", "Third text"]
        
        # Get batch embeddings
        batch_embeddings = generator.embed_batch(texts)
        
        # Get individual embeddings
        individual_embeddings = [generator.embed_text(text) for text in texts]
        
        # Should be identical
        for batch_emb, ind_emb in zip(batch_embeddings, individual_embeddings):
            np.testing.assert_array_almost_equal(batch_emb, ind_emb)
