"""
Service for extracting entities and relationships from document chunks.

This module provides functionality to automatically extract knowledge graph
data when documents are uploaded and chunked.
"""

import asyncio
import asyncpg
import os
from typing import List, Dict, Optional
from uuid import UUID
from sentence_transformers import SentenceTransformer

from graph_processing.entity_extraction import EntityExtractor
from graph_processing.relationship_extraction import RelationshipExtractor


class ExtractionService:
    """Service for extracting entities and relationships from chunks."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        gemini_api_key: str,
        embedding_model: SentenceTransformer,
        entity_threshold: float = 0.6,
        relationship_threshold: float = 0.6,
        table_name: str = "document_chunks"
    ):
        """
        Initialize extraction service.

        Args:
            pool: Database connection pool
            gemini_api_key: Google Gemini API key for LLM
            embedding_model: SentenceTransformer model for embeddings
            entity_threshold: Minimum confidence for entity extraction
            relationship_threshold: Minimum confidence for relationship extraction
            table_name: Name of the chunks table (default: document_chunks)
        """
        self.pool = pool
        self.entity_extractor = EntityExtractor(pool, gemini_api_key, embedding_model)
        self.rel_extractor = RelationshipExtractor(pool, gemini_api_key)
        self.entity_threshold = entity_threshold
        self.relationship_threshold = relationship_threshold
        self.table_name = table_name

    async def extract_from_chunk(
        self,
        chunk_id: UUID,
        chunk_text: str
    ) -> Dict[str, any]:
        """
        Extract entities and relationships from a single chunk.

        Args:
            chunk_id: UUID of the chunk
            chunk_text: Text content of the chunk

        Returns:
            Dict with extraction results: {
                'success': bool,
                'entities_count': int,
                'relationships_count': int,
                'error': Optional[str]
            }
        """
        try:
            # Extract entities
            entities = await self.entity_extractor.extract_entities_from_chunk(
                chunk_id=chunk_id,
                chunk_text=chunk_text,
                confidence_threshold=self.entity_threshold
            )

            # Extract relationships (only if we have 2+ entities)
            relationships = []
            if len(entities) >= 2:
                relationships = await self.rel_extractor.extract_relationships_from_chunk(
                    chunk_id=chunk_id,
                    chunk_text=chunk_text,
                    entities=entities,
                    confidence_threshold=self.relationship_threshold
                )

            return {
                'success': True,
                'entities_count': len(entities),
                'relationships_count': len(relationships),
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'entities_count': 0,
                'relationships_count': 0,
                'error': str(e)
            }

    async def extract_from_chunks(
        self,
        chunk_ids: List[UUID],
        verbose: bool = False
    ) -> Dict[str, any]:
        """
        Extract entities and relationships from multiple chunks.

        Args:
            chunk_ids: List of chunk UUIDs to process
            verbose: If True, print progress information

        Returns:
            Dict with summary: {
                'total_chunks': int,
                'successful': int,
                'failed': int,
                'total_entities': int,
                'total_relationships': int
            }
        """
        total_entities = 0
        total_relationships = 0
        successful = 0
        failed = 0

        if verbose:
            print(f"Extracting entities from {len(chunk_ids)} chunks...")

        # Fetch all chunk texts at once
        async with self.pool.acquire() as conn:
            chunks = await conn.fetch(
                f"SELECT id, text FROM {self.table_name} WHERE id = ANY($1::text[])",
                chunk_ids
            )

        # Process each chunk
        for i, chunk in enumerate(chunks, 1):
            result = await self.extract_from_chunk(
                chunk_id=chunk['id'],
                chunk_text=chunk['text']
            )

            if result['success']:
                successful += 1
                total_entities += result['entities_count']
                total_relationships += result['relationships_count']

                if verbose:
                    print(f"  [{i}/{len(chunks)}] ✓ {result['entities_count']} entities, "
                          f"{result['relationships_count']} relationships")
            else:
                failed += 1
                if verbose:
                    print(f"  [{i}/{len(chunks)}] ✗ Error: {result['error'][:50]}")

        return {
            'total_chunks': len(chunk_ids),
            'successful': successful,
            'failed': failed,
            'total_entities': total_entities,
            'total_relationships': total_relationships
        }

    async def extract_from_document(
        self,
        document_id: UUID,
        verbose: bool = False
    ) -> Dict[str, any]:
        """
        Extract entities from all chunks of a document.

        Args:
            document_id: UUID of the document
            verbose: If True, print progress information

        Returns:
            Extraction summary dict
        """
        # Get all chunk IDs for this document
        async with self.pool.acquire() as conn:
            chunks = await conn.fetch(
                f"SELECT id FROM {self.table_name} WHERE document_id = $1",
                str(document_id)
            )
            chunk_ids = [row['id'] for row in chunks]

        if not chunk_ids:
            return {
                'total_chunks': 0,
                'successful': 0,
                'failed': 0,
                'total_entities': 0,
                'total_relationships': 0
            }

        return await self.extract_from_chunks(chunk_ids, verbose=verbose)


async def create_extraction_service(
    pool: asyncpg.Pool,
    entity_threshold: Optional[float] = None,
    relationship_threshold: Optional[float] = None,
    table_name: str = "document_chunks"
) -> ExtractionService:
    """
    Factory function to create ExtractionService with default config.

    Args:
        pool: Database connection pool
        entity_threshold: Override default entity confidence threshold
        relationship_threshold: Override default relationship confidence threshold
        table_name: Name of the chunks table (default: document_chunks)

    Returns:
        Configured ExtractionService instance
    """
    # Get configuration from environment
    gemini_api_key = os.getenv("GOOGLE_API_KEY")
    if not gemini_api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")

    # Use env config or provided values
    entity_threshold = entity_threshold or float(os.getenv("ENTITY_CONFIDENCE_THRESHOLD", "0.6"))
    relationship_threshold = relationship_threshold or float(os.getenv("RELATIONSHIP_CONFIDENCE_THRESHOLD", "0.6"))

    # Initialize embedding model
    embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    return ExtractionService(
        pool=pool,
        gemini_api_key=gemini_api_key,
        embedding_model=embedding_model,
        entity_threshold=entity_threshold,
        relationship_threshold=relationship_threshold,
        table_name=table_name
    )
