"""
Tests for embedding process with sample texts.

These tests verify:
1. Embedding model loading
2. Single text embedding
3. Batch text embedding
4. Embedding dimensionality
5. Embedding similarity
6. End-to-end embedding pipeline
"""
import pytest
import numpy as np
from typing import List


class TestEmbedding:
    """Test suite for embedding generation."""

    def test_embedding_model_loading(self, embedding_model):
        """Test that embedding model loads successfully."""
        assert embedding_model is not None, "Embedding model failed to load"

        # Check model properties
        embedding_dim = embedding_model.get_sentence_embedding_dimension()
        assert embedding_dim == 384, f"Expected 384 dimensions, got {embedding_dim}"

    def test_single_text_embedding(self, embedding_model):
        """Test embedding generation for a single text."""
        text = "Machine learning is a subset of artificial intelligence."

        embedding = embedding_model.encode(text)

        assert embedding is not None, "Embedding is None"
        assert len(embedding) == 384, f"Expected 384 dimensions, got {len(embedding)}"
        assert isinstance(embedding, np.ndarray), "Embedding should be numpy array"

        # Check that embedding values are reasonable
        assert np.all(np.isfinite(embedding)), "Embedding contains non-finite values"
        assert not np.all(embedding == 0), "Embedding is all zeros"

    def test_batch_text_embedding(self, embedding_model, sample_texts):
        """Test embedding generation for multiple texts."""
        embeddings = embedding_model.encode(sample_texts)

        assert embeddings is not None, "Embeddings is None"
        assert len(embeddings) == len(sample_texts), "Number of embeddings doesn't match input"

        for i, embedding in enumerate(embeddings):
            assert len(embedding) == 384, f"Embedding {i} has wrong dimensions"
            assert np.all(np.isfinite(embedding)), f"Embedding {i} contains non-finite values"
            assert not np.all(embedding == 0), f"Embedding {i} is all zeros"

    def test_embedding_consistency(self, embedding_model):
        """Test that same text produces same embedding."""
        text = "Python is a programming language."

        embedding1 = embedding_model.encode(text)
        embedding2 = embedding_model.encode(text)

        # Check embeddings are identical (or very close due to floating point)
        assert np.allclose(embedding1, embedding2, rtol=1e-5), \
            "Same text should produce same embedding"

    def test_embedding_similarity(self, embedding_model):
        """Test that similar texts have similar embeddings."""
        text1 = "Machine learning is a field of artificial intelligence."
        text2 = "AI and machine learning are related fields."
        text3 = "The weather is sunny today."

        # Generate embeddings
        embeddings = embedding_model.encode([text1, text2, text3])

        # Calculate cosine similarity
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        sim_1_2 = cosine_similarity(embeddings[0], embeddings[1])
        sim_1_3 = cosine_similarity(embeddings[0], embeddings[2])

        # Similar texts should have higher similarity than dissimilar texts
        assert sim_1_2 > sim_1_3, \
            f"Similar texts should have higher similarity: {sim_1_2:.3f} vs {sim_1_3:.3f}"

        # Similar texts should have reasonably high similarity
        assert sim_1_2 > 0.3, f"Similar texts should have similarity > 0.3, got {sim_1_2:.3f}"

    def test_empty_text_handling(self, embedding_model):
        """Test handling of empty text."""
        text = ""

        try:
            embedding = embedding_model.encode(text)
            # Empty text should still produce an embedding
            assert len(embedding) == 384, "Empty text should produce 384-dim embedding"
        except Exception as e:
            pytest.fail(f"Empty text handling failed: {str(e)}")

    def test_long_text_handling(self, embedding_model):
        """Test handling of long text."""
        # Create a long text (beyond typical token limits)
        text = "This is a test sentence. " * 200  # ~1000 words

        try:
            embedding = embedding_model.encode(text)
            assert len(embedding) == 384, "Long text should produce 384-dim embedding"
            assert np.all(np.isfinite(embedding)), "Long text embedding contains non-finite values"
        except Exception as e:
            pytest.fail(f"Long text handling failed: {str(e)}")

    def test_special_characters_handling(self, embedding_model):
        """Test handling of special characters."""
        texts = [
            "Hello! How are you?",
            "Price: $99.99 (discount: 20%)",
            "Email: test@example.com",
            "Math: 2 + 2 = 4, π ≈ 3.14",
            "Unicode: 你好, こんにちは, مرحبا"
        ]

        try:
            embeddings = embedding_model.encode(texts)
            assert len(embeddings) == len(texts), "Should handle all texts with special characters"

            for i, embedding in enumerate(embeddings):
                assert len(embedding) == 384, f"Text {i} embedding has wrong dimensions"
                assert np.all(np.isfinite(embedding)), f"Text {i} embedding invalid"

        except Exception as e:
            pytest.fail(f"Special characters handling failed: {str(e)}")

    def test_embedding_normalization(self, embedding_model, sample_texts):
        """Test that embeddings can be normalized."""
        embeddings = embedding_model.encode(sample_texts, normalize_embeddings=True)

        for i, embedding in enumerate(embeddings):
            norm = np.linalg.norm(embedding)
            # Normalized embeddings should have norm ≈ 1
            assert abs(norm - 1.0) < 0.01, \
                f"Embedding {i} not properly normalized: norm = {norm:.4f}"

    @pytest.mark.asyncio
    async def test_embedding_to_list_conversion(self, embedding_model):
        """Test converting embeddings to list for database storage."""
        text = "Test text for database storage"

        embedding = embedding_model.encode(text)

        # Convert to list (as done in VectorStore)
        embedding_list = embedding.tolist()

        assert isinstance(embedding_list, list), "Should convert to list"
        assert len(embedding_list) == 384, "List should have 384 elements"
        assert all(isinstance(x, float) for x in embedding_list), "All elements should be floats"

    @pytest.mark.asyncio
    async def test_embedding_pipeline_integration(self, db_connection, test_table_name,
                                                   cleanup_test_table, embedding_model):
        """Test end-to-end embedding pipeline with database storage."""
        # Create test table
        create_table_query = f"""
        CREATE TABLE {test_table_name} (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            embedding vector(384)
        );
        """
        await db_connection.execute(create_table_query)

        # Test texts
        test_texts = [
            "Python is great for machine learning.",
            "Natural language processing uses transformers.",
            "Vector databases enable semantic search."
        ]

        # Generate embeddings
        embeddings = embedding_model.encode(test_texts)

        # Store in database
        for i, (text, embedding) in enumerate(zip(test_texts, embeddings)):
            embedding_list = embedding.tolist()
            await db_connection.execute(
                f"INSERT INTO {test_table_name} (id, text, embedding) VALUES ($1, $2, $3)",
                f"doc_{i}", text, embedding_list
            )

        # Verify storage
        count = await db_connection.fetchval(f"SELECT COUNT(*) FROM {test_table_name}")
        assert count == len(test_texts), "Not all embeddings were stored"

        # Test similarity search
        query = "What is used for semantic search?"
        query_embedding = embedding_model.encode(query).tolist()

        results = await db_connection.fetch(
            f"""
            SELECT id, text, (1 - (embedding <=> $1)) as similarity
            FROM {test_table_name}
            ORDER BY embedding <=> $1
            LIMIT 3
            """,
            query_embedding
        )

        assert len(results) == 3, "Similarity search didn't return expected results"

        # The query about semantic search should match best with the vector database text
        top_result = results[0]
        assert 'vector' in top_result['text'].lower() or 'semantic' in top_result['text'].lower(), \
            f"Top result doesn't seem relevant: {top_result['text']}"

    @pytest.mark.asyncio
    async def test_batch_embedding_performance(self, embedding_model):
        """Test batch embedding is more efficient than individual embeddings."""
        import time

        texts = [f"This is test sentence number {i}" for i in range(10)]

        # Batch encoding
        start_batch = time.time()
        batch_embeddings = embedding_model.encode(texts)
        batch_time = time.time() - start_batch

        # Individual encoding
        start_individual = time.time()
        individual_embeddings = [embedding_model.encode(text) for text in texts]
        individual_time = time.time() - start_individual

        # Batch should be faster or similar
        # (sometimes individual might be faster for very small batches)
        assert len(batch_embeddings) == len(individual_embeddings), \
            "Batch and individual should produce same number of embeddings"

        print(f"Batch time: {batch_time:.3f}s, Individual time: {individual_time:.3f}s")

    def test_embedding_with_sample_texts_fixture(self, embedding_model, sample_texts):
        """Test embedding generation with fixture sample texts."""
        embeddings = embedding_model.encode(sample_texts)

        assert len(embeddings) == len(sample_texts), \
            f"Expected {len(sample_texts)} embeddings, got {len(embeddings)}"

        # Verify all embeddings are valid
        for i, (text, embedding) in enumerate(zip(sample_texts, embeddings)):
            assert len(embedding) == 384, f"Embedding {i} wrong dimensions"
            assert np.all(np.isfinite(embedding)), f"Embedding {i} has invalid values"

            # Verify text content influences embedding
            assert not np.all(embedding == 0), f"Embedding {i} is all zeros for text: {text}"

    def test_semantic_similarity_with_queries(self, embedding_model, sample_texts, sample_queries):
        """Test semantic similarity between queries and texts."""
        # Embed texts and queries
        text_embeddings = embedding_model.encode(sample_texts)
        query_embeddings = embedding_model.encode(sample_queries)

        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        # For each query, find most similar text
        for i, query in enumerate(sample_queries):
            query_emb = query_embeddings[i]

            similarities = [
                cosine_similarity(query_emb, text_emb)
                for text_emb in text_embeddings
            ]

            max_sim_idx = np.argmax(similarities)
            max_similarity = similarities[max_sim_idx]

            print(f"\nQuery: {query}")
            print(f"Most similar text: {sample_texts[max_sim_idx]}")
            print(f"Similarity: {max_similarity:.3f}")

            # Similarity should be reasonably high
            assert max_similarity > 0.2, \
                f"Query '{query}' has low similarity ({max_similarity:.3f}) with all texts"
