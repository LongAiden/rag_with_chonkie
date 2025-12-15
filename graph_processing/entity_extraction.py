"""
Entity extraction from text chunks using LLM-based extraction.
"""

import logging
from typing import List, Dict, Any
from uuid import UUID
import asyncpg
from google import generativeai as genai

from .entity_types import EntityType, ENTITY_TYPE_DESCRIPTIONS

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extract entities from text chunks using Gemini."""

    def __init__(self, db_pool: asyncpg.Pool, gemini_api_key: str, embedding_model):
        self.db_pool = db_pool
        self.gemini_api_key = gemini_api_key
        self.embedding_model = embedding_model
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    async def extract_entities_from_chunk(
        self,
        chunk_id: UUID,
        chunk_text: str,
        confidence_threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Extract entities from a text chunk using Gemini.

        Args:
            chunk_id: UUID of the source chunk
            chunk_text: Text content to extract entities from
            confidence_threshold: Minimum confidence score (0-1)

        Returns:
            List of extracted entities with metadata
        """
        # Create extraction prompt
        prompt = self._create_extraction_prompt(chunk_text)

        try:
            # Call Gemini to extract entities
            response = self.model.generate_content(prompt)
            entities_text = response.text

            # Parse the response (expecting JSON-like format)
            entities = self._parse_entities(entities_text, confidence_threshold)

            # Store entities in database
            stored_entities = []
            for entity_data in entities:
                entity_id = await self._store_entity(
                    chunk_id=chunk_id,
                    entity_name=entity_data['name'],
                    entity_type=entity_data['type'],
                    confidence=entity_data['confidence'],
                    metadata=entity_data.get('metadata', {})
                )
                stored_entities.append({
                    'entity_id': entity_id,
                    **entity_data
                })

            logger.info(f"Extracted {len(stored_entities)} entities from chunk {chunk_id}")
            return stored_entities

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []

    def _create_extraction_prompt(self, text: str) -> str:
        """Create prompt for entity extraction."""
        entity_types = "\n".join([
            f"- {et.value}: {desc}"
            for et, desc in ENTITY_TYPE_DESCRIPTIONS.items()
        ])

        prompt = f"""You are an expert in Machine Learning and Deep Learning. Extract key entities from the following text.

ENTITY TYPES:
{entity_types}

INSTRUCTIONS:
1. Identify all important ML/DL entities in the text
2. For each entity, provide:
   - name: The entity name (as it appears in text)
   - type: One of the entity types listed above
   - confidence: Your confidence score (0.0 to 1.0)
   - description: Brief description of the entity

3. Return ONLY valid JSON array format:
[
  {{"name": "ResNet", "type": "MODEL", "confidence": 0.95, "description": "Residual neural network"}},
  {{"name": "ImageNet", "type": "DATASET", "confidence": 0.9, "description": "Large-scale image dataset"}}
]

TEXT TO ANALYZE:
{text}

EXTRACTED ENTITIES (JSON only):"""

        return prompt

    def _parse_entities(self, entities_text: str, confidence_threshold: float) -> List[Dict]:
        """Parse entities from LLM response."""
        import json
        import re

        try:
            # Try to extract JSON from response
            json_match = re.search(r'\[.*\]', entities_text, re.DOTALL)
            if json_match:
                entities_json = json_match.group(0)
                entities = json.loads(entities_json)

                # Filter by confidence and validate entity types
                valid_entities = []
                for entity in entities:
                    if entity.get('confidence', 0) >= confidence_threshold:
                        # Validate entity type
                        entity_type = entity.get('type', '').upper()
                        if entity_type in [et.value for et in EntityType]:
                            valid_entities.append({
                                'name': entity['name'],
                                'type': entity_type,
                                'confidence': entity['confidence'],
                                'metadata': {
                                    'description': entity.get('description', '')
                                }
                            })

                return valid_entities

        except Exception as e:
            logger.error(f"Error parsing entities: {e}")

        return []

    async def _store_entity(
        self,
        chunk_id: UUID,
        entity_name: str,
        entity_type: str,
        confidence: float,
        metadata: Dict
    ) -> UUID:
        """Store or update entity in database."""
        async with self.db_pool.acquire() as conn:
            # Generate embedding for entity name
            embedding = self.embedding_model.encode(entity_name).tolist()

            # Check if entity already exists (by name and type)
            existing = await conn.fetchrow(
                """
                SELECT entity_id, source_chunk_ids
                FROM entities
                WHERE entity_name = $1 AND entity_type = $2
                """,
                entity_name, entity_type
            )

            if existing:
                # Update existing entity (add chunk reference, update confidence if higher)
                entity_id = existing['entity_id']
                chunk_ids = list(existing['source_chunk_ids']) if existing['source_chunk_ids'] else []
                if chunk_id not in chunk_ids:
                    chunk_ids.append(chunk_id)

                await conn.execute(
                    """
                    UPDATE entities
                    SET confidence = GREATEST(confidence, $1),
                        source_chunk_ids = $2,
                        metadata = metadata || $3::jsonb,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE entity_id = $4
                    """,
                    confidence, chunk_ids, json.dumps(metadata), entity_id
                )
            else:
                # Insert new entity
                entity_id = await conn.fetchval(
                    """
                    INSERT INTO entities
                    (entity_name, entity_type, confidence, embedding, metadata, source_chunk_ids)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING entity_id
                    """,
                    entity_name, entity_type, confidence, embedding,
                    json.dumps(metadata), [chunk_id]
                )

            # Update chunk with entity reference
            await conn.execute(
                """
                UPDATE chunks
                SET entity_ids = array_append(entity_ids, $1)
                WHERE chunk_id = $2 AND NOT ($1 = ANY(entity_ids))
                """,
                entity_id, chunk_id
            )

            return entity_id

    async def get_entities_by_chunk(self, chunk_id: UUID) -> List[Dict]:
        """Get all entities extracted from a chunk."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT entity_id, entity_name, entity_type, confidence, metadata
                FROM entities
                WHERE $1 = ANY(source_chunk_ids)
                ORDER BY confidence DESC
                """,
                chunk_id
            )
            return [dict(row) for row in rows]

    async def get_entity_by_id(self, entity_id: UUID) -> Dict:
        """Get entity details by ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM entities WHERE entity_id = $1
                """,
                entity_id
            )
            return dict(row) if row else None

    async def search_entities(
        self,
        query: str,
        entity_type: str = None,
        limit: int = 20
    ) -> List[Dict]:
        """Search entities by name or embedding similarity."""
        async with self.db_pool.acquire() as conn:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()

            # Search by embedding similarity
            if entity_type:
                rows = await conn.fetch(
                    """
                    SELECT entity_id, entity_name, entity_type, confidence,
                           1 - (embedding <=> $1::vector) as similarity
                    FROM entities
                    WHERE entity_type = $2
                    ORDER BY embedding <=> $1::vector
                    LIMIT $3
                    """,
                    query_embedding, entity_type, limit
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT entity_id, entity_name, entity_type, confidence,
                           1 - (embedding <=> $1::vector) as similarity
                    FROM entities
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                    """,
                    query_embedding, limit
                )

            return [dict(row) for row in rows]
