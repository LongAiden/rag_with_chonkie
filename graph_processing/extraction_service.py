"""
Service for extracting entities and relationships from document chunks.

This module provides functionality to automatically extract knowledge graph
data when documents are uploaded and chunked.
"""

import asyncpg
import os
from typing import List, Dict, Optional, Any
from uuid import UUID
from sentence_transformers import SentenceTransformer

from config.graph_config import get_graph_config
from graph_processing.entity_extraction import EntityExtractor, EntityExtractionError
from graph_processing.relationship_extraction import RelationshipExtractor


class ExtractionService:
    """Service for extracting entities and relationships from chunks."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        gemini_api_key: str,
        gemini_model: str,
        embedding_model: SentenceTransformer,
        entity_threshold: float = 0.6,
        relationship_threshold: float = 0.6,
        table_name: str = "document_chunks",
        batch_size: int = 10
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
        self.entity_extractor = EntityExtractor(pool, gemini_api_key, gemini_model, embedding_model)
        self.rel_extractor = RelationshipExtractor(pool, gemini_api_key, gemini_model)
        self.entity_threshold = entity_threshold
        self.relationship_threshold = relationship_threshold
        self.table_name = table_name
        self.batch_size = max(1, batch_size)

    async def extract_from_chunk(
        self,
        chunk_id: UUID,
        chunk_text: str
    ) -> Dict[str, Any]:
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
            entities = await self.entity_extractor.extract_entities_from_chunk(
                chunk_id=chunk_id,
                chunk_text=chunk_text,
                confidence_threshold=self.entity_threshold
            )

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

        except EntityExtractionError as exc:
            return {
                'success': False,
                'entities_count': 0,
                'relationships_count': 0,
                'error': str(exc)
            }
        except Exception as exc:
            return {
                'success': False,
                'entities_count': 0,
                'relationships_count': 0,
                'error': str(exc)
            }

    async def extract_from_chunks(
        self,
        chunk_ids: List[UUID],
        verbose: bool = False
    ) -> Dict[str, Any]:
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
        total_chunks = len(chunk_ids)
        if total_chunks == 0:
            return {
                'total_chunks': 0,
                'successful': 0,
                'failed': 0,
                'total_entities': 0,
                'total_relationships': 0
            }

        total_entities = 0
        total_relationships = 0
        successful = 0
        failed = 0

        if verbose:
            print(f"Extracting entities from {total_chunks} chunks (batch size={self.batch_size})...")

        # Fetch all chunk texts at once
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT id, text FROM {self.table_name} WHERE id = ANY($1::text[])",
                chunk_ids
            )

        # Preserve requested order and note missing chunks
        chunk_lookup = {
            str(row['id']): {'id': row['id'], 'text': row['text']}
            for row in rows
        }

        ordered_chunks: List[Dict[str, Any]] = []
        for requested_id in chunk_ids:
            chunk_data = chunk_lookup.get(str(requested_id))
            if chunk_data:
                ordered_chunks.append(chunk_data)
            else:
                failed += 1
                if verbose:
                    print(f"  [!] Chunk {requested_id} not found in table {self.table_name}")

        total_available = len(ordered_chunks)
        if total_available == 0:
            return {
                'total_chunks': total_chunks,
                'successful': successful,
                'failed': failed,
                'total_entities': total_entities,
                'total_relationships': total_relationships
            }

        processed_count = 0
        for start in range(0, total_available, self.batch_size):
            batch = ordered_chunks[start:start + self.batch_size]
            chunk_payloads = [
                {'chunk_id': chunk['id'], 'chunk_text': chunk['text']}
                for chunk in batch
            ]

            try:
                batch_results = await self.entity_extractor.extract_entities_for_batch(
                    chunk_payloads=chunk_payloads,
                    confidence_threshold=self.entity_threshold
                )
            except EntityExtractionError:
                # Propagate Gemini quota/rate limit errors to caller
                raise

            for chunk in batch:
                processed_count += 1
                chunk_id = chunk['id']
                chunk_text = chunk['text']
                entities = batch_results.get(chunk_id, [])
                total_entities += len(entities)

                try:
                    relationships = []
                    if len(entities) >= 2:
                        relationships = await self.rel_extractor.extract_relationships_from_chunk(
                            chunk_id=chunk_id,
                            chunk_text=chunk_text,
                            entities=entities,
                            confidence_threshold=self.relationship_threshold
                        )

                    total_relationships += len(relationships)
                    successful += 1

                    if verbose:
                        print(f"  [{processed_count}/{total_available}] "
                              f"✓ {len(entities)} entities, {len(relationships)} relationships")
                except Exception as exc:
                    failed += 1
                    if verbose:
                        print(f"  [{processed_count}/{total_available}] ✗ Relationship extraction failed: {exc}")

        return {
            'total_chunks': total_chunks,
            'successful': successful,
            'failed': failed,
            'total_entities': total_entities,
            'total_relationships': total_relationships
        }

    async def extract_from_document(
        self,
        document_id: UUID,
        verbose: bool = False
    ) -> Dict[str, Any]:
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
    config = get_graph_config()

    gemini_api_key = config.gemini_api_key or os.getenv("GOOGLE_API_KEY")
    if not gemini_api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")

    gemini_model = config.gemini_model
    entity_threshold = entity_threshold or config.entity_confidence_threshold
    relationship_threshold = relationship_threshold or config.relationship_confidence_threshold
    batch_size = config.batch_size

    embedding_model_name = config.entity_embedding_model
    embedding_model = SentenceTransformer(embedding_model_name)

    return ExtractionService(
        pool=pool,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
        embedding_model=embedding_model,
        entity_threshold=entity_threshold,
        relationship_threshold=relationship_threshold,
        table_name=table_name,
        batch_size=batch_size
    )
