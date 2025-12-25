"""
Tests for retrieval process.

These tests verify:
1. Vector similarity search
2. Retrieval with various thresholds
3. Retrieval ordering by similarity
4. End-to-end retrieval pipeline

NOTE: These tests must be run AFTER embedding tests as they depend on data being embedded first.
"""
import pytest
import numpy as np
from typing import List, Dict


class TestRetrieval:
    """Test suite for document retrieval process."""

    @pytest.fixture
    async def populated_test_table(self, db_connection, test_table_name,
                                   embedding_model, sample_texts):
        """Fixture that creates and populates a test table with embeddings."""
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

        # Generate and store embeddings
        embeddings = embedding_model.encode(sample_texts)

        for i, (text, embedding) in enumerate(zip(sample_texts, embeddings)):
            import json
            metadata = {
                "source": f"test_doc_{i}.txt",
                "index": i
            }

            await db_connection.execute(
                f"""
                INSERT INTO {test_table_name} (id, text, embedding, metadata)
                VALUES ($1, $2, $3, $4)
                """,
                f"chunk_{i}", text, embedding.tolist(), json.dumps(metadata)
            )

        yield test_table_name

        # Cleanup
        try:
            await db_connection.execute(f"DROP TABLE IF EXISTS {test_table_name};")
        except Exception as e:
            print(f"Cleanup warning: {e}")

    @pytest.mark.asyncio
    async def test_basic_similarity_search(self, db_connection, populated_test_table,
                                          embedding_model):
        """Test basic vector similarity search."""
        query = "What is machine learning?"
        query_embedding = embedding_model.encode(query).tolist()

        # Perform similarity search
        results = await db_connection.fetch(
            f"""
            SELECT id, text, (1 - (embedding <=> $1)) as similarity
            FROM {populated_test_table}
            ORDER BY embedding <=> $1
            LIMIT 5
            """,
            query_embedding
        )

        assert len(results) > 0, "No results returned from similarity search"
        assert len(results) <= 5, "Too many results returned"

        # Verify results have required fields
        for result in results:
            assert 'id' in dict(result), "Result missing 'id'"
            assert 'text' in dict(result), "Result missing 'text'"
            assert 'similarity' in dict(result), "Result missing 'similarity'"

        # Verify results are ordered by similarity (descending)
        similarities = [r['similarity'] for r in results]
        assert similarities == sorted(similarities, reverse=True), \
            "Results not properly ordered by similarity"

    @pytest.mark.asyncio
    async def test_similarity_threshold_filtering(self, db_connection, populated_test_table,
                                                  embedding_model):
        """Test retrieval with similarity threshold."""
        query = "Python programming language"
        query_embedding = embedding_model.encode(query).tolist()
        threshold = 0.3

        # Search with threshold
        results = await db_connection.fetch(
            f"""
            SELECT id, text, (1 - (embedding <=> $1)) as similarity
            FROM {populated_test_table}
            WHERE (1 - (embedding <=> $1)) >= $2
            ORDER BY embedding <=> $1
            LIMIT 10
            """,
            query_embedding, threshold
        )

        # Verify all results meet threshold
        for result in results:
            assert result['similarity'] >= threshold, \
                f"Result has similarity {result['similarity']:.3f} below threshold {threshold}"

    @pytest.mark.asyncio
    async def test_retrieval_with_limit(self, db_connection, populated_test_table,
                                       embedding_model):
        """Test that limit parameter works correctly."""
        query = "artificial intelligence"
        query_embedding = embedding_model.encode(query).tolist()

        for limit in [1, 2, 3]:
            results = await db_connection.fetch(
                f"""
                SELECT id, text, (1 - (embedding <=> $1)) as similarity
                FROM {populated_test_table}
                ORDER BY embedding <=> $1
                LIMIT $2
                """,
                query_embedding, limit
            )

            assert len(results) == limit, f"Expected {limit} results, got {len(results)}"

    @pytest.mark.asyncio
    async def test_semantic_relevance(self, db_connection, populated_test_table,
                                      embedding_model, sample_texts):
        """Test that semantically relevant documents are retrieved."""
        # Query about machine learning
        query = "Tell me about machine learning and AI"
        query_embedding = embedding_model.encode(query).tolist()

        results = await db_connection.fetch(
            f"""
            SELECT id, text, (1 - (embedding <=> $1)) as similarity
            FROM {populated_test_table}
            ORDER BY embedding <=> $1
            LIMIT 3
            """,
            query_embedding
        )

        assert len(results) > 0, "No results returned"

        # Top result should be semantically relevant
        top_text = results[0]['text'].lower()

        # Check if top result contains relevant keywords
        relevant_keywords = ['machine learning', 'artificial intelligence', 'ai', 'learn', 'data']
        has_relevant_keyword = any(keyword in top_text for keyword in relevant_keywords)

        assert has_relevant_keyword, \
            f"Top result doesn't seem semantically relevant: {results[0]['text']}"

    @pytest.mark.asyncio
    async def test_retrieval_with_metadata(self, db_connection, populated_test_table,
                                          embedding_model):
        """Test retrieval includes metadata."""
        query = "programming"
        query_embedding = embedding_model.encode(query).tolist()

        results = await db_connection.fetch(
            f"""
            SELECT id, text, metadata, (1 - (embedding <=> $1)) as similarity
            FROM {populated_test_table}
            ORDER BY embedding <=> $1
            LIMIT 3
            """,
            query_embedding
        )

        assert len(results) > 0, "No results returned"

        # Verify metadata is included
        for result in results:
            assert 'metadata' in dict(result), "Result missing metadata"
            metadata = result['metadata']
            assert 'source' in metadata, "Metadata missing 'source'"
            assert 'index' in metadata, "Metadata missing 'index'"

    @pytest.mark.asyncio
    async def test_multiple_query_retrieval(self, db_connection, populated_test_table,
                                           embedding_model, sample_queries):
        """Test retrieval for multiple different queries."""
        for query in sample_queries:
            query_embedding = embedding_model.encode(query).tolist()

            results = await db_connection.fetch(
                f"""
                SELECT id, text, (1 - (embedding <=> $1)) as similarity
                FROM {populated_test_table}
                ORDER BY embedding <=> $1
                LIMIT 3
                """,
                query_embedding
            )

            assert len(results) > 0, f"No results for query: {query}"

            # Verify similarity decreases
            similarities = [r['similarity'] for r in results]
            assert similarities == sorted(similarities, reverse=True), \
                f"Results not ordered for query: {query}"

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, db_connection, populated_test_table,
                                       embedding_model):
        """Test handling of empty query."""
        query = ""
        query_embedding = embedding_model.encode(query).tolist()

        try:
            results = await db_connection.fetch(
                f"""
                SELECT id, text, (1 - (embedding <=> $1)) as similarity
                FROM {populated_test_table}
                ORDER BY embedding <=> $1
                LIMIT 3
                """,
                query_embedding
            )

            # Should return results even for empty query
            assert isinstance(results, list), "Should return list for empty query"

        except Exception as e:
            pytest.fail(f"Empty query handling failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_retrieval_consistency(self, db_connection, populated_test_table,
                                        embedding_model):
        """Test that same query returns consistent results."""
        query = "neural networks and deep learning"
        query_embedding = embedding_model.encode(query).tolist()

        # Perform search twice
        results1 = await db_connection.fetch(
            f"""
            SELECT id, text, (1 - (embedding <=> $1)) as similarity
            FROM {populated_test_table}
            ORDER BY embedding <=> $1
            LIMIT 5
            """,
            query_embedding
        )

        results2 = await db_connection.fetch(
            f"""
            SELECT id, text, (1 - (embedding <=> $1)) as similarity
            FROM {populated_test_table}
            ORDER BY embedding <=> $1
            LIMIT 5
            """,
            query_embedding
        )

        # Results should be identical
        assert len(results1) == len(results2), "Result counts differ"

        for r1, r2 in zip(results1, results2):
            assert r1['id'] == r2['id'], "Result IDs differ"
            assert abs(r1['similarity'] - r2['similarity']) < 1e-6, \
                "Similarity scores differ"

    @pytest.mark.asyncio
    async def test_retrieval_with_ivfflat_index(self, db_connection, populated_test_table,
                                               embedding_model):
        """Test retrieval performance with IVFFLAT index."""
        # Create IVFFLAT index
        index_name = f"{populated_test_table}_idx"

        try:
            await db_connection.execute(
                f"""
                CREATE INDEX {index_name} ON {populated_test_table}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 5);
                """
            )

            # Perform search with index
            query = "machine learning algorithms"
            query_embedding = embedding_model.encode(query).tolist()

            results = await db_connection.fetch(
                f"""
                SELECT id, text, (1 - (embedding <=> $1)) as similarity
                FROM {populated_test_table}
                ORDER BY embedding <=> $1
                LIMIT 3
                """,
                query_embedding
            )

            assert len(results) > 0, "No results with IVFFLAT index"

            # Results should still be ordered by similarity
            similarities = [r['similarity'] for r in results]
            assert similarities == sorted(similarities, reverse=True), \
                "Results not ordered with IVFFLAT index"

        finally:
            # Cleanup index
            try:
                await db_connection.execute(f"DROP INDEX IF EXISTS {index_name};")
            except Exception as e:
                print(f"Index cleanup warning: {e}")

    @pytest.mark.asyncio
    async def test_retrieval_similarity_scores(self, db_connection, populated_test_table,
                                              embedding_model):
        """Test that similarity scores are in valid range."""
        query = "data science and analytics"
        query_embedding = embedding_model.encode(query).tolist()

        results = await db_connection.fetch(
            f"""
            SELECT id, text, (1 - (embedding <=> $1)) as similarity
            FROM {populated_test_table}
            ORDER BY embedding <=> $1
            LIMIT 10
            """,
            query_embedding
        )

        for result in results:
            similarity = result['similarity']

            # Cosine similarity should be in range [-1, 1]
            # With normalized vectors, typically [0, 1]
            assert -1.0 <= similarity <= 1.0, \
                f"Similarity score {similarity} out of valid range"

    @pytest.mark.asyncio
    async def test_end_to_end_retrieval_pipeline(self, db_connection, test_table_name,
                                                 cleanup_test_table, embedding_model):
        """Test complete end-to-end retrieval pipeline: embed -> store -> retrieve."""
        # Step 1: Create table
        create_table_query = f"""
        CREATE TABLE {test_table_name} (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            embedding vector(384),
            metadata JSONB
        );
        """
        await db_connection.execute(create_table_query)

        # Step 2: Prepare documents
        documents = [
            {
                "id": "doc1",
                "text": "Python is widely used in machine learning and data science.",
                "metadata": {"category": "programming"}
            },
            {
                "id": "doc2",
                "text": "Neural networks are inspired by biological neurons in the brain.",
                "metadata": {"category": "ai"}
            },
            {
                "id": "doc3",
                "text": "The quick brown fox jumps over the lazy dog.",
                "metadata": {"category": "example"}
            }
        ]

        # Step 3: Embed and store
        import json

        for doc in documents:
            embedding = embedding_model.encode(doc["text"]).tolist()
            await db_connection.execute(
                f"""
                INSERT INTO {test_table_name} (id, text, embedding, metadata)
                VALUES ($1, $2, $3, $4)
                """,
                doc["id"], doc["text"], embedding, json.dumps(doc["metadata"])
            )

        # Step 4: Retrieve
        query = "What programming language is used for machine learning?"
        query_embedding = embedding_model.encode(query).tolist()

        results = await db_connection.fetch(
            f"""
            SELECT id, text, metadata, (1 - (embedding <=> $1)) as similarity
            FROM {test_table_name}
            WHERE (1 - (embedding <=> $1)) >= 0.2
            ORDER BY embedding <=> $1
            LIMIT 3
            """,
            query_embedding
        )

        # Step 5: Verify results
        assert len(results) > 0, "End-to-end pipeline returned no results"

        # Top result should be about Python/programming
        top_result = results[0]
        assert 'python' in top_result['text'].lower() or \
               'programming' in top_result['text'].lower(), \
            f"Top result not relevant: {top_result['text']}"

        # Verify metadata is preserved
        assert top_result['metadata']['category'] == 'programming', \
            "Metadata not correctly preserved"

    @pytest.mark.asyncio
    async def test_retrieval_with_different_similarity_functions(self, db_connection,
                                                                 populated_test_table,
                                                                 embedding_model):
        """Test retrieval with different similarity/distance functions."""
        query = "machine learning"
        query_embedding = embedding_model.encode(query).tolist()

        # Test cosine distance (<=>)
        cosine_results = await db_connection.fetch(
            f"""
            SELECT id, (1 - (embedding <=> $1)) as similarity
            FROM {populated_test_table}
            ORDER BY embedding <=> $1
            LIMIT 3
            """,
            query_embedding
        )

        assert len(cosine_results) > 0, "Cosine distance search failed"

        # Test L2 distance (<->)
        l2_results = await db_connection.fetch(
            f"""
            SELECT id, embedding <-> $1 as distance
            FROM {populated_test_table}
            ORDER BY embedding <-> $1
            LIMIT 3
            """,
            query_embedding
        )

        assert len(l2_results) > 0, "L2 distance search failed"

        # Both should return results (order might differ)
        assert len(cosine_results) == len(l2_results), \
            "Different distance functions returned different result counts"
