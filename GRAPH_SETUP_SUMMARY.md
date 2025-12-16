# Graph Integration Setup Summary

## 📋 What Was Added

This document summarizes all the additions made to integrate knowledge graph capabilities with pgRouting into your RAG system.

---

## 1. 📦 New Python Libraries (requirements.txt)

**File**: [deployment/requirements.txt](deployment/requirements.txt)

Added the following dependencies:

```python
# Graph & Knowledge Extraction
spacy>=3.7.0                  # For NER and entity extraction
spacy-transformers>=1.3.0     # Transformer-based models for spacy
networkx>=3.0                 # For graph analysis and algorithms
```

**Installation**:
```bash
cd /Users/longnv/Coding/rag_llama_index
pip install -r deployment/requirements.txt
```

---

## 2. 🗄️ Database Schema (SQL Migration)

**File**: [migrations/001_create_graph_tables.sql](migrations/001_create_graph_tables.sql)

Created comprehensive database schema with:

### Tables
- **entities** - Stores ML/DL entities (models, algorithms, datasets, etc.)
  - entity_id (UUID), entity_name, entity_type, confidence
  - embedding (vector 384) for semantic search
  - metadata (JSONB), source_chunk_ids (UUID[])

- **relationships** - Stores relationships between entities
  - relationship_id (UUID), source_entity_id, target_entity_id
  - relationship_type, confidence, weight
  - metadata (JSONB), source_chunk_ids (UUID[])

- **entity_nodes** - UUID to BIGINT mapping for pgRouting
  - entity_id (UUID) → node_id (BIGINT)

- **entity_edges** - pgRouting-compatible edges
  - source, target (BIGINT), cost, reverse_cost
  - Auto-synced from relationships table

### Functions
- `get_or_create_node_id()` - UUID to BIGINT conversion
- `sync_entity_edges()` - Auto-sync relationships to edges
- `find_entity_path()` - Shortest path using Dijkstra
- `get_connected_entities()` - Find entities within N hops
- `calculate_entity_pagerank()` - Entity importance scoring

### Triggers
- `sync_relationships_to_edges` - Automatic edge synchronization

### Indexes
- Vector indexes (IVFFlat) on entity embeddings
- B-tree indexes on IDs and types
- GIN indexes on JSONB metadata

**Run Migration**:
```bash
psql -h localhost -U your_user -d your_database -f migrations/001_create_graph_tables.sql
```

---

## 3. 📁 New Python Modules

### graph_processing/ (New Folder)

#### [graph_processing/__init__.py](graph_processing/__init__.py)
- Package initialization
- Exports main classes

#### [graph_processing/entity_types.py](graph_processing/entity_types.py)
- **40+ Entity Types** for ML/DL domain:
  - ALGORITHM, MODEL, ARCHITECTURE, TECHNIQUE
  - DATASET, METRIC, TASK, FRAMEWORK
  - LAYER, ACTIVATION, LOSS_FUNCTION, OPTIMIZER
  - And many more...

- **25+ Relationship Types**:
  - USES, TRAINED_ON, IMPROVES, OUTPERFORMS
  - PART_OF, BASED_ON, SOLVES, ADDRESSES
  - IS_A, EXTENDS, IMPLEMENTS, ENABLES
  - And many more...

#### [graph_processing/entity_extraction.py](graph_processing/entity_extraction.py)
**Class**: `EntityExtractor`

**Key Methods**:
- `extract_entities_from_chunk()` - Extract entities from text using Gemini LLM
- `get_entities_by_chunk()` - Retrieve entities for a chunk
- `get_entity_by_id()` - Get entity details
- `search_entities()` - Search by name or embedding similarity

**Features**:
- LLM-based extraction with confidence scoring
- Automatic deduplication of entities
- Vector embeddings for semantic search
- Chunk reference tracking
- Batch-friendly prompts driven by `BATCH_SIZE` to minimize Gemini calls
- Environment-driven Gemini configuration (`GOOGLE_API_KEY` + `GEMINI_MODEL`) with quota-aware error handling

#### [graph_processing/relationship_extraction.py](graph_processing/relationship_extraction.py)
**Class**: `RelationshipExtractor`

**Key Methods**:
- `extract_relationships_from_chunk()` - Extract relationships using Gemini LLM
- `get_relationships_by_chunk()` - Get relationships from chunk
- `get_entity_relationships()` - Get all relationships for an entity

**Features**:
- Context-aware relationship extraction
- Confidence-based filtering
- Automatic edge creation (via database trigger)
- Shares the same env-configured Gemini model as the entity extractor for consistency

#### [graph_processing/graph_service.py](graph_processing/graph_service.py)
**Class**: `GraphService`

**Key Methods**:
- `find_shortest_path()` - Dijkstra's shortest path algorithm
- `get_connected_entities()` - Find entities within N hops
- `get_graph_stats()` - Graph statistics and distributions
- `calculate_pagerank()` - Rank entity importance
- `get_subgraph()` - Extract subgraph for specific entities

**Features**:
- pgRouting integration for high-performance graph algorithms
- Bidirectional path finding
- Cost-based routing (lower confidence = higher cost)

#### [graph_processing/extraction_service.py](graph_processing/extraction_service.py)
**Class**: `ExtractionService`

**Role**:
- Coordinates entity + relationship extraction for chunks/documents
- Batches Gemini calls using `GraphConfig.batch_size` to control quota usage
- Surfaces `EntityExtractionError` when the LLM returns quota/rate-limit issues so uploads log warnings instead of silent zeros

**Flow**:
1. Load Gemini settings (`GOOGLE_API_KEY`, `GEMINI_MODEL`) and `BATCH_SIZE` from [`GraphConfig`](config/graph_config.py).
2. Group chunk text into batch prompts and call Gemini once per batch.
3. Persist entities, then optionally extract relationships per chunk.
4. Return success/failed chunk counts so the upload summary reflects skipped chunks.

---

## 4. 📊 Pydantic Models

**File**: [models/graph_models.py](models/graph_models.py)

Complete set of request/response models:

### Entity Models
- `EntityBase`, `EntityCreate`, `EntityResponse`
- `EntitySearchRequest`

### Relationship Models
- `RelationshipBase`, `RelationshipCreate`, `RelationshipResponse`
- `RelationshipWithNames`

### Graph Query Models
- `GraphPathResponse` - Path finding results
- `ConnectedEntitiesResponse` - Connected entities
- `GraphStatsResponse` - Graph statistics
- `PageRankResponse` - PageRank scores
- `SubgraphResponse` - Subgraph data

### Extraction Models
- `ExtractEntitiesRequest`, `ExtractRelationshipsRequest`
- `BatchExtractionRequest`, `BatchExtractionResponse`
- `ExtractionResult`

---

## 5. 🚀 FastAPI Routes

**File**: [api/graph_routes.py](api/graph_routes.py)

**15+ API Endpoints** organized in categories:

### Entity Extraction
- `POST /graph/extract/entities` - Extract entities from chunk
- `POST /graph/extract/relationships` - Extract relationships
- `POST /graph/extract/batch` - Batch extraction

### Entity Queries
- `GET /graph/entities/{entity_id}` - Get entity details
- `POST /graph/entities/search` - Search entities
- `GET /graph/entities/chunk/{chunk_id}` - Get chunk entities

### Relationship Queries
- `GET /graph/relationships/entity/{entity_id}` - Get entity relationships
- `GET /graph/relationships/chunk/{chunk_id}` - Get chunk relationships

### Graph Analysis
- `GET /graph/path/{source_id}/{target_id}` - Find shortest path
- `GET /graph/connected/{entity_id}` - Get connected entities (N-hops)
- `GET /graph/stats` - Graph statistics
- `GET /graph/pagerank` - Calculate PageRank
- `POST /graph/subgraph` - Get subgraph

### Health Check
- `GET /graph/health` - System health check

**Features**:
- Async operations using asyncpg
- Dependency injection for services
- Comprehensive error handling
- OpenAPI documentation

---

## 6. 📖 Documentation

**File**: [GRAPH_INTEGRATION_GUIDE.md](GRAPH_INTEGRATION_GUIDE.md)

Comprehensive 400+ line guide covering:
- Architecture overview
- Step-by-step installation
- Usage examples
- API reference
- Integration patterns
- Performance optimization
- Troubleshooting
- Complete workflow example

---

## 📂 Complete File Structure

```
rag_llama_index/
├── graph_processing/              # ✨ NEW
│   ├── __init__.py               # Package init
│   ├── entity_types.py           # ML/DL entity & relationship types
│   ├── entity_extraction.py      # Entity extraction service
│   ├── relationship_extraction.py # Relationship extraction service
│   └── graph_service.py          # Graph operations (pgRouting)
│
├── models/
│   └── graph_models.py           # ✨ NEW - Pydantic models
│
├── api/
│   └── graph_routes.py           # ✨ NEW - FastAPI routes
│
├── migrations/
│   └── 001_create_graph_tables.sql # ✨ NEW - Database schema
│
├── deployment/
│   └── requirements.txt          # ✨ UPDATED - Added graph libraries
│
├── GRAPH_INTEGRATION_GUIDE.md    # ✨ NEW - Comprehensive guide
└── GRAPH_SETUP_SUMMARY.md        # ✨ NEW - This file
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd /Users/longnv/Coding/rag_llama_index
pip install -r deployment/requirements.txt
```

### 2. Install PostgreSQL Extension
```sql
-- Connect to your database
CREATE EXTENSION IF NOT EXISTS "pgrouting";
```

### 3. Run Migration
```bash
psql -h localhost -U user -d dbname -f migrations/001_create_graph_tables.sql
```

### 4. Integrate Routes
```python
# In your main FastAPI app
from api.graph_routes import router as graph_router
app.include_router(graph_router)
```

### 5. Set Environment Variables
```bash
export GEMINI_API_KEY="your-api-key"
export DATABASE_URL="postgresql://user:pass@localhost/dbname"
```

### 6. Test
```bash
# Health check
curl http://localhost:8000/graph/health

# Extract entities from a chunk
curl -X POST http://localhost:8000/graph/extract/entities \
  -H "Content-Type: application/json" \
  -d '{"chunk_id": "your-chunk-uuid", "confidence_threshold": 0.6}'
```

---

## 💡 Key Features

### 1. **Automatic Entity Extraction**
- LLM-based extraction using Gemini
- 40+ entity types for ML/DL domain
- Confidence-based filtering
- Vector embeddings for semantic search

### 2. **Relationship Discovery**
- 25+ relationship types
- Context-aware extraction
- Automatic graph construction
- Database trigger-based synchronization

### 3. **Graph Algorithms**
- **Dijkstra's Algorithm** - Shortest path between concepts
- **Driving Distance** - Find entities within N hops
- **PageRank** - Identify important concepts
- **Subgraph Extraction** - Focus on specific entities

### 4. **Performance Optimized**
- Async operations (asyncpg)
- Optimized indexes (IVFFlat, B-tree, GIN)
- Batch processing support
- Connection pooling

### 5. **Domain-Specific**
- Tailored for Machine Learning / Deep Learning
- Comprehensive entity taxonomy
- Semantic relationship types
- Ready for research papers, documentation, tutorials

---

## 📊 Use Cases

### 1. **Concept Discovery**
Find how concepts are connected:
```
"How is BERT related to ImageNet?"
→ BERT → Transformer → Attention → CNN → ImageNet
```

### 2. **Knowledge Exploration**
Discover related concepts within N hops:
```
GET /graph/connected/{bert_entity_id}?max_hops=2
→ Returns: Transformer, Attention, NLP, GPT, RoBERTa, etc.
```

### 3. **Enhanced RAG**
Combine vector search with graph context:
- Vector search finds relevant chunks
- Graph finds related concepts
- Merged results provide richer context

### 4. **Research Paper Analysis**
Extract and connect concepts from papers:
- Models mentioned
- Datasets used
- Techniques applied
- Performance comparisons

### 5. **Concept Importance**
Find central concepts using PageRank:
```
GET /graph/pagerank
→ Top concepts: "Neural Networks", "Gradient Descent", "Backpropagation"
```

---

## 🎯 Next Steps

1. **Test the System**
   - Upload a sample ML paper
   - Extract entities and relationships
   - Query the graph

2. **Integrate with Existing Pipeline**
   - Add graph extraction to document processing
   - Enhance search with graph context
   - Implement graph-based reranking

3. **Build Visualization** (Optional)
   - Use D3.js or Cytoscape.js
   - Display entity network
   - Interactive graph exploration

4. **Optimize Performance**
   - Monitor query performance
   - Adjust confidence thresholds
   - Implement caching strategies

5. **Extend Functionality**
   - Add custom entity types
   - Define new relationship types
   - Implement domain-specific extraction rules

---

## 📚 References

- **pgRouting Documentation**: https://docs.pgrouting.org/
- **pgvector**: https://github.com/pgvector/pgvector
- **Gemini API**: https://ai.google.dev/
- **FastAPI**: https://fastapi.tiangolo.com/
- **spaCy**: https://spacy.io/

---

## ✅ Checklist

- [x] Python dependencies added to requirements.txt
- [x] Database schema created (SQL migration)
- [x] Entity extraction module implemented
- [x] Relationship extraction module implemented
- [x] Graph service with pgRouting integration
- [x] Pydantic models for all operations
- [x] 15+ FastAPI endpoints
- [x] Comprehensive documentation
- [x] ML/DL domain-specific entity types (40+)
- [x] ML/DL domain-specific relationship types (25+)
- [x] Automatic edge synchronization
- [x] Vector embeddings for entities
- [x] Graph algorithms (Dijkstra, PageRank, etc.)
- [x] Batch processing support
- [x] Health check endpoint

---

## 🎉 Summary

You now have a **complete knowledge graph system** integrated with your RAG pipeline:

- ✅ **4 new Python modules** for graph processing
- ✅ **4 database tables** with pgRouting support
- ✅ **15+ API endpoints** for graph operations
- ✅ **40+ entity types** for ML/DL domain
- ✅ **25+ relationship types** for semantic connections
- ✅ **5+ graph algorithms** (Dijkstra, PageRank, etc.)
- ✅ **Complete documentation** with examples

The system is ready to extract entities and relationships from your ML/DL documents, build a knowledge graph, and enable powerful graph-based queries!

---

**Questions or issues?** Check the [GRAPH_INTEGRATION_GUIDE.md](GRAPH_INTEGRATION_GUIDE.md) for detailed troubleshooting and examples.
