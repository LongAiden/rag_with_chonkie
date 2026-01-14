# Knowledge Graph Table Interactions & Data Flow

## 1. Entity Relationship Diagram (ERD)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         DOCUMENT CHUNKS (Source Data)                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ document_chunks                                                       │  │
│  │ ─────────────────                                                     │  │
│  │ • id (uuid)                                                           │  │
│  │ • text (text)                                                         │  │
│  │ • document_id (uuid)                                                  │  │
│  │ • entity_ids (uuid[])  ← Stores extracted entity references          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Entity Extraction (Gemini API)
                                      ↓
┌────────────────────────────────────────────────────────────────────────────┐
│                          ENTITIES (Core Entity Data)                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ entities                                                              │  │
│  │ ─────────────────                                                     │  │
│  │ • entity_id (uuid) [PK]                                               │  │
│  │ • entity_name (text)              "BERT", "ResNet", "Attention"      │  │
│  │ • entity_type (text)              MODEL, ALGORITHM, TECHNIQUE         │  │
│  │ • confidence (float 0-1)          LLM confidence score                │  │
│  │ • embedding (vector[384])         Semantic vector for similarity      │  │
│  │ • metadata (jsonb)                {description, properties}           │  │
│  │ • source_chunk_ids (uuid[])       Where this entity was found         │  │
│  │ • created_at, updated_at                                              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
                  │                                            │
                  │                                            │
                  ├────────────────────────────────────────────┤
                  │                                            │
                  ↓                                            ↓
    ┌─────────────────────────────┐          ┌────────────────────────────────┐
    │    entity_nodes              │          │      relationships             │
    │    ──────────────            │          │      ──────────────            │
    │ • entity_id (uuid) [PK,FK]  │          │ • relationship_id (uuid) [PK] │
    │ • node_id (bigint) [UNIQUE] │          │ • source_entity_id (uuid) [FK]│◄──┐
    │                              │          │ • target_entity_id (uuid) [FK]│◄──┤
    │ Maps UUID to integer for     │          │ • relationship_type (text)    │   │
    │ pgRouting algorithms         │          │   ↳ IS_A, USES, TRAINED_ON    │   │
    │                              │          │ • confidence (float 0-1)      │   │
    │ FK: entity_id → entities     │          │ • weight (float)              │   │
    └─────────────────────────────┘          │ • metadata (jsonb)            │   │
                  │                           │ • source_chunk_ids (uuid[])   │   │
                  │                           │                               │   │
                  │                           │ FK: source/target → entities  │   │
                  │                           │                               │   │
                  │                           │ Constraint: no self-reference │   │
                  │                           └───────────────────────────────┘   │
                  │                                         │                     │
                  │                                         │                     │
                  │                         TRIGGER: sync_relationships_to_edges │
                  │                                         │                     │
                  │                                         ↓                     │
                  │                           ┌──────────────────────────────┐   │
                  │                           │      entity_edges            │   │
                  │                           │      ─────────────           │   │
                  │                           │ • id (serial) [PK]           │   │
                  └───────────────────────────┤ • source (bigint)            │   │
                                              │ • target (bigint)            │───┘
                                              │ • cost (float)               │
                                              │ • reverse_cost (float)       │
                                              │ • relationship_id (uuid) [FK]│
                                              │ • relationship_type (text)   │
                                              │                              │
                                              │ Used by pgRouting for:       │
                                              │  - Shortest path             │
                                              │  - PageRank                  │
                                              │  - Community detection       │
                                              │                              │
                                              │ FK: relationship_id → rels   │
                                              └──────────────────────────────┘
```

## 2. Data Flow: Entity & Relationship Extraction

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EXTRACTION WORKFLOW                                   │
└─────────────────────────────────────────────────────────────────────────────┘

STEP 1: Document Ingestion
───────────────────────────
    User uploads document
            │
            ↓
    ┌──────────────────┐
    │ Text Chunking    │  (Recursive/Semantic chunking)
    └──────────────────┘
            │
            ↓
    ┌──────────────────────────────────┐
    │ INSERT INTO document_chunks      │
    │  - id, text, document_id          │
    │  - entity_ids = [] (empty)        │
    └──────────────────────────────────┘


STEP 2: Entity Extraction (Batch Processing)
─────────────────────────────────────────────
    ┌────────────────────────────────────────┐
    │ ExtractionService.extract_from_chunks  │
    │                                        │
    │ Batch size: 120 chunks                 │
    └────────────────────────────────────────┘
                    │
                    ↓
    ┌────────────────────────────────────────┐
    │ EntityExtractor.extract_for_batch      │
    │                                        │
    │ Sends to Gemini API:                   │
    │  - Chunk texts (up to 120)             │
    │  - Entity type definitions             │
    │  - Extraction prompt                   │
    └────────────────────────────────────────┘
                    │
                    ↓ (JSON response)
    ┌────────────────────────────────────────┐
    │ JSONParser.parse_with_fallback         │
    │                                        │
    │ Robust parsing with 4 strategies:      │
    │  1. Markdown extraction                │
    │  2. Balanced bracket matching          │
    │  3. Regex extraction                   │
    │  4. JSON repair                        │
    └────────────────────────────────────────┘
                    │
                    ↓ (Parsed entities)
    ┌────────────────────────────────────────┐
    │ Filter by confidence threshold (0.6)   │
    │ Validate entity_type                   │
    └────────────────────────────────────────┘
                    │
                    ↓
    ┌────────────────────────────────────────┐
    │ EntityExtractor._store_entity          │
    │                                        │
    │ For each entity:                       │
    │  1. Generate embedding (384-dim)       │
    │  2. Check if exists (name + type)      │
    │     ├─ Exists: UPDATE                  │
    │     │   - Merge chunk_ids              │
    │     │   - Keep max confidence          │
    │     │   - Merge metadata                │
    │     └─ New: INSERT                     │
    │         - New entity_id                │
    │         - Store embedding              │
    │                                        │
    │  3. UPDATE document_chunks             │
    │     SET entity_ids = array_append(...) │
    └────────────────────────────────────────┘
                    │
                    ↓
    ┌────────────────────────────────────────┐
    │ INSERT/UPDATE entities                 │
    │                                        │
    │ Returns: List of entity_id + metadata  │
    └────────────────────────────────────────┘


STEP 3: Relationship Extraction (Batch Processing)
───────────────────────────────────────────────────
    ┌────────────────────────────────────────┐
    │ Filter chunks with >= 2 entities       │
    └────────────────────────────────────────┘
                    │
                    ↓
    ┌────────────────────────────────────────┐
    │ RelationshipExtractor.extract_for_batch│
    │                                        │
    │ Sends to Gemini API:                   │
    │  - Chunk texts                         │
    │  - Entity lists per chunk              │
    │  - Relationship type definitions       │
    │  - Extraction prompt                   │
    └────────────────────────────────────────┘
                    │
                    ↓ (JSON response)
    ┌────────────────────────────────────────┐
    │ JSONParser.parse_with_fallback         │
    │ Parse relationships by chunk_id        │
    └────────────────────────────────────────┘
                    │
                    ↓ (Parsed relationships)
    ┌────────────────────────────────────────┐
    │ Validate:                              │
    │  - Confidence >= 0.6                   │
    │  - Valid relationship_type             │
    │  - Both entities exist in chunk        │
    │  - source_id != target_id              │
    └────────────────────────────────────────┘
                    │
                    ↓
    ┌────────────────────────────────────────┐
    │ RelationshipExtractor._store_relationship│
    │                                        │
    │ For each relationship:                 │
    │  1. Check if exists                    │
    │     (source + target + type)           │
    │     ├─ Exists: UPDATE                  │
    │     │   - Merge chunk_ids              │
    │     │   - Keep max confidence          │
    │     └─ New: INSERT                     │
    │         - New relationship_id          │
    │                                        │
    │  2. TRIGGER fires automatically        │
    │     sync_relationships_to_edges()      │
    └────────────────────────────────────────┘
                    │
                    ↓
    ┌────────────────────────────────────────┐
    │ INSERT/UPDATE relationships            │
    │                                        │
    │ TRIGGER: sync_relationships_to_edges   │
    │  ├─ Get or create node_ids             │
    │  │   (INSERT INTO entity_nodes)        │
    │  └─ INSERT/UPDATE entity_edges         │
    │      - source/target (bigint)          │
    │      - cost, reverse_cost              │
    │      - relationship metadata           │
    └────────────────────────────────────────┘
```

## 3. Database Trigger: Auto-Sync to Graph Edges

```sql
┌────────────────────────────────────────────────────────────────┐
│ TRIGGER: sync_relationships_to_edges                           │
│ FIRES: AFTER INSERT OR UPDATE OR DELETE ON relationships       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ ON INSERT/UPDATE:                                              │
│ ─────────────────                                              │
│   1. Get or create source node_id:                             │
│      INSERT INTO entity_nodes (entity_id, node_id)             │
│      VALUES (NEW.source_entity_id, nextval('node_id_seq'))     │
│      ON CONFLICT DO NOTHING                                    │
│      RETURNING node_id                                         │
│                                                                │
│   2. Get or create target node_id:                             │
│      (same as above for target_entity_id)                      │
│                                                                │
│   3. Calculate cost from confidence:                           │
│      cost = 1.0 / NEW.confidence                               │
│      (higher confidence = lower cost = shorter path)           │
│                                                                │
│   4. Upsert into entity_edges:                                 │
│      INSERT INTO entity_edges                                  │
│        (source, target, cost, reverse_cost,                    │
│         relationship_id, relationship_type)                    │
│      VALUES (source_node, target_node, cost, cost,             │
│              NEW.relationship_id, NEW.relationship_type)       │
│      ON CONFLICT (relationship_id) DO UPDATE                   │
│        SET cost = EXCLUDED.cost,                               │
│            reverse_cost = EXCLUDED.reverse_cost                │
│                                                                │
│ ON DELETE:                                                     │
│ ──────────                                                     │
│   DELETE FROM entity_edges                                     │
│   WHERE relationship_id = OLD.relationship_id                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## 4. Query Patterns & Table Usage

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         QUERY PATTERNS                                   │
└─────────────────────────────────────────────────────────────────────────┘

Pattern 1: Semantic Entity Search
──────────────────────────────────
    Query embedding (384-dim vector)
                │
                ↓
    ┌───────────────────────────────────┐
    │ SELECT * FROM entities            │
    │ ORDER BY embedding <=> $query_vec │  ← Cosine similarity (IVFFlat index)
    │ LIMIT 10                          │
    └───────────────────────────────────┘
                │
                ↓
    Returns: Most semantically similar entities


Pattern 2: Find Entity Relationships
─────────────────────────────────────
    Entity ID or Name
                │
                ↓
    ┌────────────────────────────────────────────┐
    │ SELECT e1.entity_name, r.relationship_type,│
    │        e2.entity_name                       │
    │ FROM relationships r                        │
    │ JOIN entities e1 ON r.source_entity_id = e1.entity_id│
    │ JOIN entities e2 ON r.target_entity_id = e2.entity_id│
    │ WHERE e1.entity_id = $entity_id             │
    └────────────────────────────────────────────┘
                │
                ↓
    Returns: All relationships FROM this entity


Pattern 3: Shortest Path Between Entities
──────────────────────────────────────────
    Two entity IDs
                │
                ↓
    ┌────────────────────────────────────────────┐
    │ 1. Get node_ids from entity_nodes          │
    │    WHERE entity_id IN ($id1, $id2)         │
    └────────────────────────────────────────────┘
                │
                ↓
    ┌────────────────────────────────────────────┐
    │ 2. pgRouting shortest path query:          │
    │                                            │
    │ SELECT * FROM pgr_dijkstra(                │
    │   'SELECT id, source, target, cost,        │
    │           reverse_cost                     │
    │    FROM entity_edges',                     │
    │   $source_node, $target_node,              │
    │   directed := true                         │
    │ )                                          │
    └────────────────────────────────────────────┘
                │
                ↓
    ┌────────────────────────────────────────────┐
    │ 3. Enrich with entity names:               │
    │    JOIN entity_nodes to get entity_ids     │
    │    JOIN entities to get names/types        │
    │    JOIN relationships for edge details     │
    └────────────────────────────────────────────┘
                │
                ↓
    Returns: Path with entity names and relationship types


Pattern 4: PageRank (Most Important Entities)
──────────────────────────────────────────────
    ┌────────────────────────────────────────────┐
    │ SELECT * FROM pgr_pageRank(                │
    │   'SELECT id, source, target, cost         │
    │    FROM entity_edges'                      │
    │ )                                          │
    └────────────────────────────────────────────┘
                │
                ↓
    ┌────────────────────────────────────────────┐
    │ JOIN entity_nodes to map node → entity     │
    │ JOIN entities to get names/types           │
    │ ORDER BY pagerank DESC                     │
    └────────────────────────────────────────────┘
                │
                ↓
    Returns: Most connected/important entities


Pattern 5: K-Hop Neighborhood
──────────────────────────────
    Entity ID + hop count (k)
                │
                ↓
    ┌────────────────────────────────────────────┐
    │ 1. Get node_id from entity_nodes           │
    └────────────────────────────────────────────┘
                │
                ↓
    ┌────────────────────────────────────────────┐
    │ 2. pgRouting k-hop query:                  │
    │                                            │
    │ SELECT * FROM pgr_drivingDistance(         │
    │   'SELECT id, source, target, cost         │
    │    FROM entity_edges',                     │
    │   $start_node,                             │
    │   distance := $k,                          │
    │   directed := true                         │
    │ )                                          │
    └────────────────────────────────────────────┘
                │
                ↓
    Returns: All entities within k hops
```

## 5. Table Interaction Summary

| From Table | To Table | Interaction Type | Purpose |
|------------|----------|------------------|---------|
| `document_chunks` | `entities` | **Reference** (entity_ids array) | Link chunks to extracted entities |
| `entities` | `entity_nodes` | **1:1 Mapping** (FK) | Map UUID to integer for pgRouting |
| `entities` | `relationships` | **Source** (FK) | Entity as relationship source |
| `entities` | `relationships` | **Target** (FK) | Entity as relationship target |
| `relationships` | `entity_edges` | **Auto-sync** (Trigger) | Create graph edges from relationships |
| `entity_nodes` | `entity_edges` | **Reference** (node_id) | Connect edges to entities |

## 6. Key Design Patterns

### Deduplication Strategy
```
When extracting entities:
├─ Same name + type → UPDATE existing
│  ├─ Merge source_chunk_ids (union)
│  ├─ Keep MAX(confidence)
│  └─ Merge metadata (JSON merge)
└─ Different name or type → INSERT new

When extracting relationships:
├─ Same source + target + type → UPDATE existing
│  ├─ Merge source_chunk_ids
│  ├─ Keep MAX(confidence)
│  └─ Merge metadata
└─ Different combination → INSERT new
```

### Cascade Deletion
```
DELETE entity
    │
    ├─► DELETE from entity_nodes (CASCADE)
    │
    ├─► DELETE from relationships (CASCADE)
    │   └─► TRIGGER deletes from entity_edges
    │
    └─► Chunks keep entity_id (orphaned, but safe)
```

### Vector Similarity + Graph Traversal
```
Hybrid Query Flow:
1. Semantic Search (entities.embedding)
   └─► Find top K similar entities

2. Graph Expansion (entity_edges)
   └─► Find connected entities via relationships

3. Chunk Retrieval (source_chunk_ids)
   └─► Get source text for context
```

## 7. Performance Considerations

| Operation | Table(s) | Index Used | Complexity |
|-----------|----------|------------|------------|
| Entity by name | `entities` | `idx_entities_entity_name` | O(log n) |
| Semantic search | `entities` | `idx_entities_embedding` (IVFFlat) | O(log n) approx |
| Find relationships | `relationships` | `idx_relationships_source/target` | O(log n) |
| Shortest path | `entity_edges` | `idx_entity_edges_source/target` | O(E log V) |
| PageRank | `entity_edges` | Full scan + algorithm | O(E × iterations) |
| Entity by chunk | `entities` | `source_chunk_ids` GIN index | O(log n) |

