# Knowledge Graph Integration Guide

This guide explains how to integrate the knowledge graph functionality with pgRouting into your RAG system.

## Overview

The knowledge graph enhancement adds the ability to:
- **Extract entities** from documents (ML/DL concepts, models, algorithms, datasets, etc.)
- **Extract relationships** between entities (USES, IMPROVES, TRAINED_ON, etc.)
- **Find paths** between concepts using graph algorithms
- **Discover related concepts** within N hops
- **Rank entity importance** using PageRank
- **Enhance search** with graph-based context

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     RAG + Knowledge Graph                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Document → Chunks → Vector Embeddings → PostgreSQL         │
│                ↓                                             │
│         Entity Extraction (LLM)                              │
│                ↓                                             │
│    Entities Table + Vector Embeddings                        │
│                ↓                                             │
│      Relationship Extraction (LLM)                           │
│                ↓                                             │
│  Relationships → Auto-sync → pgRouting Edges                 │
│                                                              │
│  ┌──────────────────────────────────────────────┐           │
│  │  Graph Operations (pgRouting)                │           │
│  │  - Shortest Path (Dijkstra)                  │           │
│  │  - Connected Entities (Driving Distance)     │           │
│  │  - PageRank (Importance Scoring)             │           │
│  └──────────────────────────────────────────────┘           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Installation Steps

### 1. Install Python Dependencies

```bash
cd /Users/longnv/Coding/rag_llama_index
pip install -r deployment/requirements.txt

# Download spaCy model (optional, for advanced NER)
python -m spacy download en_core_web_sm
```

### 2. Install PostgreSQL Extensions

Connect to your PostgreSQL database and run:

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";      -- Already installed
CREATE EXTENSION IF NOT EXISTS "pgrouting";   -- NEW: Install this
```

**Note**: If `pgrouting` is not available, install it on your system first:

**Ubuntu/Debian:**
```bash
sudo apt-get install postgresql-16-pgrouting
```

**macOS (Homebrew):**
```bash
brew install pgrouting
```

**Docker:** Use the provided Dockerfile or update your docker-compose.yml:
```yaml
services:
  postgres:
    image: pgrouting/pgrouting:16-3.6
    # ... other config
```

### 3. Run Database Migration

```bash
# Connect to your database
psql -h localhost -U your_user -d your_database -f migrations/001_create_graph_tables.sql

# Or using psycopg2 in Python
python -c "
import asyncpg
import asyncio

async def run_migration():
    conn = await asyncpg.connect('postgresql://user:pass@localhost/dbname')
    with open('migrations/001_create_graph_tables.sql') as f:
        await conn.execute(f.read())
    await conn.close()

asyncio.run(run_migration())
"
```

### 4. Verify Installation

```python
import asyncpg
import asyncio

async def verify():
    conn = await asyncpg.connect('your_connection_string')

    # Check pgRouting
    result = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'pgr_dijkstra')"
    )
    print(f"pgRouting installed: {result}")

    # Check tables
    tables = await conn.fetch("""
        SELECT table_name FROM information_schema.tables
        WHERE table_name IN ('entities', 'relationships', 'entity_nodes', 'entity_edges')
    """)
    print(f"Graph tables: {[t['table_name'] for t in tables]}")

    await conn.close()

asyncio.run(verify())
```

## Usage

### Step 1: Upload and Process Document

```python
# Upload document (existing flow)
POST /upload_document
{
    "file": "ml_paper.pdf",
    "collection_name": "ml_papers"
}
```

### Step 2: Extract Entities from Chunks

```python
# Extract entities from a specific chunk
POST /graph/extract/entities
{
    "chunk_id": "uuid-of-chunk",
    "confidence_threshold": 0.6
}

# Or batch process all chunks from a document
POST /graph/extract/batch
{
    "chunk_ids": ["chunk-uuid-1", "chunk-uuid-2", ...],
    "entity_confidence_threshold": 0.6,
    "relationship_confidence_threshold": 0.6
}
```

> 💡 **Batched Gemini Calls**
>
> The backend automatically groups chunk IDs using the `BATCH_SIZE` value from
> [`GraphConfig`](config/graph_config.py). Even if you pass hundreds of chunk
> IDs, Gemini only receives ~`len(chunk_ids) / BATCH_SIZE` requests, which keeps
> Free Tier quotas happy. Tune `BATCH_SIZE` and `GEMINI_MODEL` in `.env`
> to control the balance between throughput and token usage.

**Response:**
```json
{
    "results": [
        {
            "chunk_id": "...",
            "entities_extracted": 5,
            "relationships_extracted": 3,
            "success": true
        }
    ],
    "total_entities_extracted": 50,
    "total_relationships_extracted": 30
}
```

### Step 3: Query the Knowledge Graph

#### Search for Entities
```python
POST /graph/entities/search
{
    "query": "BERT",
    "entity_type": "MODEL",  # Optional filter
    "limit": 20
}
```

#### Find Path Between Concepts
```python
GET /graph/path/{bert_entity_id}/{imagenet_entity_id}
```

**Response:**
```json
{
    "source_entity_id": "...",
    "target_entity_id": "...",
    "path_found": true,
    "path_length": 3,
    "path_cost": 1.25,
    "path_entities": [
        {"entity_id": "...", "entity_name": "BERT", "entity_type": "MODEL"},
        {"entity_id": "...", "entity_name": "Transformer", "entity_type": "ARCHITECTURE"},
        {"entity_id": "...", "entity_name": "Attention", "entity_type": "TECHNIQUE"},
        {"entity_id": "...", "entity_name": "CNN", "entity_type": "ARCHITECTURE"}
    ],
    "path_relationships": [
        {"relationship_type": "USES", "confidence": 0.9},
        {"relationship_type": "PART_OF", "confidence": 0.85},
        {"relationship_type": "RELATED_TO", "confidence": 0.75}
    ]
}
```

#### Get Related Concepts
```python
GET /graph/connected/{entity_id}?max_hops=2
```

#### Get Graph Statistics
```python
GET /graph/stats
```

#### Find Important Concepts (PageRank)
```python
GET /graph/pagerank
```

## Integration with Existing RAG Pipeline

### Enhanced Search with Graph Context

Modify your search function to include graph-based context:

```python
async def enhanced_search(query: str, collection_name: str, top_k: int = 5):
    # 1. Traditional vector search
    vector_results = await vector_search(query, collection_name, top_k)

    # 2. Extract entities from query
    query_entities = await entity_extractor.extract_entities_from_chunk(
        chunk_id=None,  # No chunk for queries
        chunk_text=query,
        confidence_threshold=0.7
    )

    # 3. Get connected entities (expand context)
    related_entities = []
    for entity in query_entities:
        connected = await graph_service.get_connected_entities(
            entity_id=entity['entity_id'],
            max_hops=2
        )
        related_entities.extend(connected)

    # 4. Get chunks that contain related entities
    graph_chunks = await get_chunks_by_entities(related_entities)

    # 5. Merge and rerank
    combined_results = merge_results(vector_results, graph_chunks)
    reranked = await reranker.rerank(query, combined_results)

    return reranked
```

### Automatic Extraction Pipeline

Add graph extraction to your document processing pipeline:

```python
# In full_pipeline_pgvector.py
async def process_document_with_graph(file, collection_name):
    # 1. Existing: Upload and chunk
    chunk_ids = await chunk_and_upload(file, collection_name)

    # 2. NEW: Extract entities and relationships
    extraction_result = await extract_knowledge_graph(chunk_ids)

    return {
        "chunks_created": len(chunk_ids),
        "entities_extracted": extraction_result['total_entities'],
        "relationships_extracted": extraction_result['total_relationships']
    }

async def extract_knowledge_graph(chunk_ids):
    # Batch extract entities and relationships
    result = await batch_extract_api(chunk_ids)
    return result
```

## Entity and Relationship Types

### Entity Types (ML/DL Domain)
- **ALGORITHM**: Neural networks, gradient descent, backpropagation
- **MODEL**: BERT, GPT, ResNet, VGG, YOLO
- **ARCHITECTURE**: Transformer, CNN, RNN, LSTM, GAN
- **TECHNIQUE**: Dropout, batch normalization, attention
- **DATASET**: ImageNet, COCO, MNIST, WikiText
- **METRIC**: Accuracy, F1-score, BLEU, perplexity
- **TASK**: Classification, detection, segmentation, translation
- **FRAMEWORK**: PyTorch, TensorFlow, JAX
- And 30+ more types...

### Relationship Types
- **USES**: Model USES optimizer
- **TRAINED_ON**: Model TRAINED_ON dataset
- **IMPROVES**: Technique IMPROVES metric
- **OUTPERFORMS**: Model A OUTPERFORMS Model B
- **PART_OF**: Layer PART_OF architecture
- **BASED_ON**: Model BASED_ON prior work
- And 20+ more types...

## API Endpoints Reference

### Entity Extraction
- `POST /graph/extract/entities` - Extract entities from chunk
- `POST /graph/extract/relationships` - Extract relationships from chunk
- `POST /graph/extract/batch` - Batch extraction from multiple chunks

### Entity Queries
- `GET /graph/entities/{entity_id}` - Get entity details
- `POST /graph/entities/search` - Search entities by name/embedding
- `GET /graph/entities/chunk/{chunk_id}` - Get entities from chunk

### Relationship Queries
- `GET /graph/relationships/entity/{entity_id}` - Get entity relationships
- `GET /graph/relationships/chunk/{chunk_id}` - Get relationships from chunk

### Graph Analysis
- `GET /graph/path/{source_id}/{target_id}` - Find shortest path
- `GET /graph/connected/{entity_id}?max_hops=2` - Get connected entities
- `GET /graph/stats` - Get graph statistics
- `GET /graph/pagerank` - Calculate entity importance
- `POST /graph/subgraph` - Get subgraph for entities

### Health Check
- `GET /graph/health` - Check graph system health

## Performance Considerations

### Indexing
The migration creates optimized indexes:
- Vector indexes on entity embeddings (IVFFlat)
- B-tree indexes on entity/relationship IDs
- GIN indexes on JSONB metadata
- pgRouting optimized indexes on edges

### Batch Processing
Always use batch extraction for multiple chunks:
```python
# Good: Batch process
POST /graph/extract/batch with 100 chunk_ids

# Bad: Individual calls
for chunk_id in chunk_ids:
    POST /graph/extract/entities  # Slow!
```

### Caching
Consider caching frequently accessed paths and connected entities.

### Async Operations
All database operations are async using asyncpg for high performance.

## Troubleshooting

### pgRouting not found
```
ERROR: function pgr_dijkstra() does not exist
```
**Solution**: Install pgRouting extension (see Installation Steps #2)

### Slow graph queries
**Solution**: Ensure indexes are created (they should be automatic from migration)
```sql
-- Verify indexes
SELECT indexname FROM pg_indexes WHERE tablename IN ('entities', 'relationships', 'entity_edges');
```

### High extraction costs (Gemini API)
**Solution**: Adjust confidence thresholds to reduce LLM calls:
```python
# Higher threshold = fewer, higher-quality entities
confidence_threshold = 0.75  # Instead of 0.6
```

### Memory issues with large graphs
**Solution**: Use pagination and limit results:
```python
# Limit connected entities
GET /graph/connected/{entity_id}?max_hops=1  # Instead of 2

# Limit search results
POST /graph/entities/search with limit=10  # Instead of 50
```

## Next Steps

1. **Integrate graph routes** into your main FastAPI app:
   ```python
   from api.graph_routes import router as graph_router
   app.include_router(graph_router)
   ```

2. **Update environment variables**:
   ```bash
   # .env
   GEMINI_API_KEY=your_api_key
   DATABASE_URL=postgresql://user:pass@localhost/dbname
   ```

3. **Test the system**:
   ```bash
   # Run health check
   curl http://localhost:8000/graph/health

   # Upload a document
   # Extract entities
   # Query the graph
   ```

4. **Build visualization** (optional):
   - Use D3.js or Cytoscape.js for graph visualization
   - Create a frontend that displays entity relationships
   - Show paths between concepts visually

## Example: Complete Workflow

```python
import httpx
import asyncio

async def complete_workflow():
    client = httpx.AsyncClient(base_url="http://localhost:8000")

    # 1. Upload document
    with open("ml_paper.pdf", "rb") as f:
        upload_resp = await client.post("/upload_document",
            files={"file": f},
            data={"collection_name": "ml_papers"}
        )
    chunk_ids = upload_resp.json()["chunk_ids"]

    # 2. Extract knowledge graph
    extraction_resp = await client.post("/graph/extract/batch", json={
        "chunk_ids": chunk_ids,
        "entity_confidence_threshold": 0.6,
        "relationship_confidence_threshold": 0.6
    })
    print(f"Extracted {extraction_resp.json()['total_entities_extracted']} entities")

    # 3. Search for a concept
    search_resp = await client.post("/graph/entities/search", json={
        "query": "BERT",
        "limit": 1
    })
    bert_entity = search_resp.json()[0]
    bert_id = bert_entity["entity_id"]

    # 4. Find related concepts
    related_resp = await client.get(f"/graph/connected/{bert_id}?max_hops=2")
    related = related_resp.json()
    print(f"Found {related['total_connected']} related concepts")

    # 5. Get graph stats
    stats_resp = await client.get("/graph/stats")
    stats = stats_resp.json()
    print(f"Graph has {stats['total_entities']} entities and {stats['total_relationships']} relationships")

    await client.aclose()

asyncio.run(complete_workflow())
```

## Resources

- **pgRouting Documentation**: https://docs.pgrouting.org/
- **pgvector Documentation**: https://github.com/pgvector/pgvector
- **Gemini API**: https://ai.google.dev/
- **FastAPI**: https://fastapi.tiangolo.com/

## Support

For issues or questions:
1. Check the health endpoint: `GET /graph/health`
2. Review logs for extraction errors
3. Verify database connections and extensions
4. Check API key validity for Gemini

Happy graph building! 🚀
