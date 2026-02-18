"""
Document retrieval and search logic.
Handles vector search, BM25 reranking, and response generation.
"""

import logfire
from typing import List, Optional

from retrieval.utils import rerank_bm25
from retrieval.llm_operations import generate_llm_response
from models.models import RAGResponse, RAGSource, RAGResponseMetadata


async def perform_document_search(
    query: str,
    limit: int,
    threshold: float,
    pipeline,
    config,
    document_ids: Optional[List[str]] = None,
    table_name: str = "document_chunks"
) -> RAGResponse:
    """
    Common document search logic with optional reranking.

    Args:
        query: Search query string
        limit: Maximum number of results to return
        threshold: Similarity threshold for filtering results
        pipeline: ChunkEmbeddingPipeline instance
        config: Application configuration object
        document_ids: Optional list of document IDs to filter by
        table_name: Database table name

    Returns:
        RAGResponse with answer, sources, and metadata
    """
    with logfire.span("document_search",
                     query=query[:100],  # Truncate long queries for logging
                     limit=limit,
                     threshold=threshold,
                     table_name=table_name):

        # Step 1: pgvector similarity search
        with logfire.span("embedding_generation_for_search"):
            logfire.info("Generating embeddings for search query",
                        query_length=len(query),
                        embedding_model=pipeline.embedding_generator.model_name)

            results = await pipeline.search_documents(
                query=query,
                limit=limit,
                threshold=threshold,
                document_ids=document_ids
            )

            logfire.info("Initial search completed",
                        results_found=len(results),
                        avg_similarity=sum(r['similarity'] for r in results) / len(results) if results else 0)

        # Step 1.5: Apply BM25 reranking if we have enough results
        avg_rerank_score = None
        reranking_enabled = False

        if len(results) > 5:
            reranking_enabled = True
            with logfire.span("bm25_reranking"):
                # Rerank using BM25
                reranked_results = rerank_bm25(query=query, sources=results, top_k=5)

                # Add BM25 scores to results
                results = [{
                    'chunk_id': r['chunk_id'],
                    'text': r['text'],
                    'document_id': r['document_id'],
                    'metadata': r['metadata'],
                    'similarity': r['similarity'],
                    'rerank_score': r['bm25_score']
                } for r in reranked_results]

                avg_rerank_score = sum(r['rerank_score'] for r in results) / len(results) if results else None

                logfire.info("BM25 reranking completed",
                           final_results=len(results),
                           avg_rerank_score=avg_rerank_score)

        if not results:
            return RAGResponse(
                query=query,
                answer="No relevant documents found with the specified similarity threshold.",
                sources=[],
                search_stats=RAGResponseMetadata(
                    chunks_found=0,
                    avg_similarity=0.0,
                    search_method="pgvector_cosine" + ("_bm25" if reranking_enabled else ""),
                    threshold_used=threshold,
                    word_count=9,  # word count of the no-results message
                    confidence=0.0,
                    reranking_enabled=reranking_enabled,
                    avg_rerank_score=avg_rerank_score
                ),
                table_used=table_name
            )

        # Step 2: Build context from retrieved chunks with page numbers
        with logfire.span("context_building"):
            context_parts = []
            for i, result in enumerate(results):
                page_info = ""
                if result.get('metadata') and result['metadata'].get('page_number'):
                    page_info = f" (Page {result['metadata']['page_number']})"
                context_parts.append(
                    f"[Source {i+1}{page_info}]: {result['text']}")

            context = "\n\n".join(context_parts)

            logfire.info("Context built",
                        total_context_parts=len(context_parts),
                        context_length=len(context))

        # Step 3: Generate response with LLM
        llm_response = await generate_llm_response(query, context, results, config.agent)

        # Calculate search statistics
        avg_similarity = sum(r['similarity'] for r in results) / len(results)

        # Create structured response
        return RAGResponse(
            query=query,
            answer=llm_response.answer,
            sources=[
                RAGSource(
                    chunk_id=r['chunk_id'],
                    text=r['text'],
                    similarity=round(r['similarity'], 3),
                    document_id=r['document_id'],
                    page_number=r.get('metadata', {}).get('page_number'),
                    metadata=r.get('metadata', {}),
                    rerank_score=round(r['rerank_score'], 3) if 'rerank_score' in r else None,
                ) for r in results
            ],
            search_stats=RAGResponseMetadata(
                chunks_found=len(results),
                avg_similarity=round(avg_similarity, 3),
                search_method="pgvector_cosine" + ("_bm25" if reranking_enabled else ""),
                threshold_used=threshold,
                word_count=llm_response.word_count,
                confidence=llm_response.confidence,
                reranking_enabled=reranking_enabled,
                avg_rerank_score=round(avg_rerank_score, 3) if avg_rerank_score else None,
            ),
            table_used=table_name
        )
