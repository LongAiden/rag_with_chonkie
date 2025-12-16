"""
Relationship extraction between entities using LLM.
"""

import logging
import json
from typing import List, Dict, Any
from uuid import UUID
import asyncpg
from google import generativeai as genai

from .entity_types import RelationshipType, RELATIONSHIP_TYPE_DESCRIPTIONS

logger = logging.getLogger(__name__)


class RelationshipExtractor:
    """Extract relationships between entities using Gemini."""

    def __init__(self, db_pool: asyncpg.Pool, gemini_api_key: str, gemini_model: str):
        self.db_pool = db_pool
        self.gemini_api_key = gemini_api_key
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = gemini_model or "gemini-2.5-flash"
        self.model = genai.GenerativeModel(self.gemini_model)

    async def extract_relationships_from_chunk(
        self,
        chunk_id: UUID,
        chunk_text: str,
        entities: List[Dict[str, Any]],
        confidence_threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Extract relationships between entities in a chunk.

        Args:
            chunk_id: UUID of the source chunk
            chunk_text: Text content
            entities: List of entities found in the chunk
            confidence_threshold: Minimum confidence score

        Returns:
            List of extracted relationships
        """
        if len(entities) < 2:
            logger.info(f"Not enough entities in chunk {chunk_id} for relationship extraction")
            return []

        # Create extraction prompt
        prompt = self._create_extraction_prompt(chunk_text, entities)

        try:
            # Call Gemini to extract relationships
            response = self.model.generate_content(prompt)
            relationships_text = response.text

            # Parse the response
            relationships = self._parse_relationships(
                relationships_text,
                entities,
                confidence_threshold
            )

            # Store relationships in database
            stored_relationships = []
            for rel_data in relationships:
                relationship_id = await self._store_relationship(
                    chunk_id=chunk_id,
                    source_entity_id=rel_data['source_entity_id'],
                    target_entity_id=rel_data['target_entity_id'],
                    relationship_type=rel_data['type'],
                    confidence=rel_data['confidence'],
                    metadata=rel_data.get('metadata', {})
                )
                stored_relationships.append({
                    'relationship_id': relationship_id,
                    **rel_data
                })

            logger.info(f"Extracted {len(stored_relationships)} relationships from chunk {chunk_id}")
            return stored_relationships

        except Exception as e:
            logger.error(f"Error extracting relationships: {e}")
            return []

    def _create_extraction_prompt(self, text: str, entities: List[Dict]) -> str:
        """Create prompt for relationship extraction."""
        relationship_types = "\n".join([
            f"- {rt.value}: {desc}"
            for rt, desc in RELATIONSHIP_TYPE_DESCRIPTIONS.items()
        ])

        # Format entities for the prompt
        entity_list = "\n".join([
            f"- {e['name']} ({e['type']}, ID: {e.get('entity_id', 'N/A')})"
            for e in entities
        ])

        prompt = f"""You are an expert in Machine Learning and Deep Learning. Identify relationships between the given entities based on the text.

RELATIONSHIP TYPES:
{relationship_types}

ENTITIES IN TEXT:
{entity_list}

INSTRUCTIONS:
1. Identify relationships between the entities listed above
2. For each relationship, provide:
   - source: Name of source entity (must match entity list)
   - target: Name of target entity (must match entity list)
   - type: One of the relationship types listed above
   - confidence: Your confidence score (0.0 to 1.0)
   - description: Brief explanation of the relationship

3. Return ONLY valid JSON array format:
[
  {{"source": "ResNet", "target": "ImageNet", "type": "TRAINED_ON", "confidence": 0.9, "description": "ResNet models are commonly trained on ImageNet dataset"}},
  {{"source": "Dropout", "target": "Overfitting", "type": "MITIGATES", "confidence": 0.85, "description": "Dropout technique helps prevent overfitting"}}
]

TEXT TO ANALYZE:
{text}

EXTRACTED RELATIONSHIPS (JSON only):"""

        return prompt

    def _parse_relationships(
        self,
        relationships_text: str,
        entities: List[Dict],
        confidence_threshold: float
    ) -> List[Dict]:
        """Parse relationships from LLM response."""
        import re

        try:
            # Create entity name to ID mapping
            entity_map = {e['name']: e.get('entity_id') for e in entities}

            # Try to extract JSON from response
            json_match = re.search(r'\[.*\]', relationships_text, re.DOTALL)
            if json_match:
                relationships_json = json_match.group(0)
                relationships = json.loads(relationships_json)

                # Filter and validate relationships
                valid_relationships = []
                for rel in relationships:
                    if rel.get('confidence', 0) >= confidence_threshold:
                        # Validate relationship type
                        rel_type = rel.get('type', '').upper()
                        if rel_type in [rt.value for rt in RelationshipType]:
                            source_name = rel.get('source')
                            target_name = rel.get('target')

                            # Check if entities exist
                            if source_name in entity_map and target_name in entity_map:
                                source_id = entity_map[source_name]
                                target_id = entity_map[target_name]

                                if source_id and target_id and source_id != target_id:
                                    valid_relationships.append({
                                        'source_entity_id': source_id,
                                        'target_entity_id': target_id,
                                        'type': rel_type,
                                        'confidence': rel['confidence'],
                                        'metadata': {
                                            'description': rel.get('description', ''),
                                            'source_name': source_name,
                                            'target_name': target_name
                                        }
                                    })

                return valid_relationships

        except Exception as e:
            logger.error(f"Error parsing relationships: {e}")

        return []

    async def _store_relationship(
        self,
        chunk_id: UUID,
        source_entity_id: UUID,
        target_entity_id: UUID,
        relationship_type: str,
        confidence: float,
        metadata: Dict,
        weight: float = 1.0
    ) -> UUID:
        """Store or update relationship in database."""
        async with self.db_pool.acquire() as conn:
            # Check if relationship already exists
            existing = await conn.fetchrow(
                """
                SELECT relationship_id, source_chunk_ids
                FROM relationships
                WHERE source_entity_id = $1
                  AND target_entity_id = $2
                  AND relationship_type = $3
                """,
                source_entity_id, target_entity_id, relationship_type
            )

            if existing:
                # Update existing relationship
                relationship_id = existing['relationship_id']
                chunk_ids = list(existing['source_chunk_ids']) if existing['source_chunk_ids'] else []
                if chunk_id not in chunk_ids:
                    chunk_ids.append(chunk_id)

                await conn.execute(
                    """
                    UPDATE relationships
                    SET confidence = GREATEST(confidence, $1),
                        source_chunk_ids = $2,
                        metadata = metadata || $3::jsonb,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE relationship_id = $4
                    """,
                    confidence, chunk_ids, json.dumps(metadata), relationship_id
                )
            else:
                # Insert new relationship (trigger will auto-create edge)
                relationship_id = await conn.fetchval(
                    """
                    INSERT INTO relationships
                    (source_entity_id, target_entity_id, relationship_type,
                     confidence, weight, metadata, source_chunk_ids)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING relationship_id
                    """,
                    source_entity_id, target_entity_id, relationship_type,
                    confidence, weight, json.dumps(metadata), [chunk_id]
                )

            return relationship_id

    async def get_relationships_by_chunk(self, chunk_id: UUID) -> List[Dict]:
        """Get all relationships from a chunk."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT r.relationship_id, r.source_entity_id, r.target_entity_id,
                       r.relationship_type, r.confidence, r.metadata,
                       e1.entity_name as source_name, e1.entity_type as source_type,
                       e2.entity_name as target_name, e2.entity_type as target_type
                FROM relationships r
                JOIN entities e1 ON r.source_entity_id = e1.entity_id
                JOIN entities e2 ON r.target_entity_id = e2.entity_id
                WHERE $1 = ANY(r.source_chunk_ids)
                ORDER BY r.confidence DESC
                """,
                chunk_id
            )
            return [dict(row) for row in rows]

    async def get_entity_relationships(
        self,
        entity_id: UUID,
        relationship_type: str = None
    ) -> List[Dict]:
        """Get all relationships for an entity."""
        async with self.db_pool.acquire() as conn:
            if relationship_type:
                rows = await conn.fetch(
                    """
                    SELECT r.relationship_id, r.source_entity_id, r.target_entity_id,
                           r.relationship_type, r.confidence,
                           e1.entity_name as source_name,
                           e2.entity_name as target_name
                    FROM relationships r
                    JOIN entities e1 ON r.source_entity_id = e1.entity_id
                    JOIN entities e2 ON r.target_entity_id = e2.entity_id
                    WHERE (r.source_entity_id = $1 OR r.target_entity_id = $1)
                      AND r.relationship_type = $2
                    ORDER BY r.confidence DESC
                    """,
                    entity_id, relationship_type
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT r.relationship_id, r.source_entity_id, r.target_entity_id,
                           r.relationship_type, r.confidence,
                           e1.entity_name as source_name,
                           e2.entity_name as target_name
                    FROM relationships r
                    JOIN entities e1 ON r.source_entity_id = e1.entity_id
                    JOIN entities e2 ON r.target_entity_id = e2.entity_id
                    WHERE r.source_entity_id = $1 OR r.target_entity_id = $1
                    ORDER BY r.confidence DESC
                    """,
                    entity_id
                )

            return [dict(row) for row in rows]
