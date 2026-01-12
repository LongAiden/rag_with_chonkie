"""
Integration tests for the embedding pipeline.

These tests verify:
1. End-to-end embedding pipeline with database storage
2. ChunkEmbeddingPipeline integration
3. Embedding generation and storage
"""
import sys
import pytest
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestEmbeddingPipeline:
    """Integration tests for the embedding pipeline."""

    @pytest.mark.asyncio
    async def test_embedding_pipeline_integration(self, db_connection, test_table_name,
                                                   cleanup_test_table, embedding_model):
        """Test end-to-end embedding pipeline with database storage."""
        # Create test table
        create_table_query = f"""
        CREATE TABLE {test_table_name} (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            embedding vector(384),
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        await db_connection.execute(create_table_query)

        # Sample texts to embed
        texts = [
            "Machine learning is a subset of artificial intelligence.",
            "Python is widely used for data science.",
            "Neural networks are inspired by the brain."
        ]

        # Generate embeddings
        embeddings = embedding_model.encode(texts)

        # Store in database
        import json
        import uuid
        
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            chunk_id = str(uuid.uuid4())
            metadata = {"source": "test", "index": i}
            
            await db_connection.execute(
                f"""
                INSERT INTO {test_table_name} (id, text, embedding, metadata)
                VALUES ($1, $2, $3, $4)
                """,
                chunk_id, text, embedding.tolist(), json.dumps(metadata)
            )

        # Verify storage
        count = await db_connection.fetchval(f"SELECT COUNT(*) FROM {test_table_name}")
        assert count == 3, f"Expected 3 rows, got {count}"

        # Test retrieval
        query = "What is machine learning?"
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

        assert len(results) > 0, "No results from pipeline"
        assert 'machine learning' in results[0]['text'].lower(), \
            f"Most similar result not relevant: {results[0]['text']}"

    @pytest.mark.asyncio
    async def test_batch_embedding_storage(self, db_connection, test_table_name,
                                           cleanup_test_table, embedding_model):
        """Test batch embedding and storage."""
        # Create test table
        await db_connection.execute(f"""
        CREATE TABLE {test_table_name} (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            embedding vector(384)
        );
        """)

        # Generate batch of texts
        texts = [f"Document number {i} with some content." for i in range(50)]
        
        # Batch embed
        embeddings = embedding_model.encode(texts)

        # Batch insert
        import uuid
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            await db_connection.execute(
                f"INSERT INTO {test_table_name} (id, text, embedding) VALUES ($1, $2, $3)",
                str(uuid.uuid4()), text, embedding.tolist()
            )

        # Verify count
        count = await db_connection.fetchval(f"SELECT COUNT(*) FROM {test_table_name}")
        assert count == 50, f"Expected 50 rows, got {count}"

    @pytest.mark.asyncio
    async def test_similarity_search_accuracy(self, db_connection, test_table_name,
                                              cleanup_test_table, embedding_model):
        """Test that similarity search returns semantically relevant results."""
        # Create table
        await db_connection.execute(f"""
        CREATE TABLE {test_table_name} (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            embedding vector(384),
            category TEXT
        );
        """)

        # Documents with clear categories
        documents = [
            ("Python is great for machine learning", "tech"),
            ("JavaScript is used for web development", "tech"),
            ("Dogs are loyal pets", "animals"),
            ("Cats are independent animals", "animals"),
            ("The stock market crashed today", "finance"),
        ]

        # Store documents
        for i, (text, category) in enumerate(documents):
            embedding = embedding_model.encode(text).tolist()
            await db_connection.execute(
                f"INSERT INTO {test_table_name} (id, text, embedding, category) VALUES ($1, $2, $3, $4)",
                f"doc_{i}", text, embedding, category
            )

        # Query about programming
        query = "What programming language is best for AI?"
        query_embedding = embedding_model.encode(query).tolist()

        results = await db_connection.fetch(
            f"""
            SELECT text, category, (1 - (embedding <=> $1)) as similarity
            FROM {test_table_name}
            ORDER BY embedding <=> $1
            LIMIT 2
            """,
            query_embedding
        )

        # Top results should be tech-related
        top_categories = [r['category'] for r in results]
        assert 'tech' in top_categories, f"Expected tech results, got: {top_categories}"
