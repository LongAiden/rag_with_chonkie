# Utility Scripts

Scripts for managing the RAG + Knowledge Graph system.

## extract_existing_chunks.py

**Purpose:** One-time migration script to extract entities and relationships from documents uploaded BEFORE entity extraction was enabled.

**Important:** Entity extraction is now **automatic** for new uploads (controlled by `ENABLE_ENTITY_EXTRACTION` environment variable). You only need this script to process existing chunks.

### Usage

**Test with first 10 chunks:**
```bash
docker exec -it rag_app python scripts/extract_existing_chunks.py --limit 10
```

**Process all existing chunks:**
```bash
docker exec -it rag_app python scripts/extract_existing_chunks.py --batch-size 50
```

**Custom batch size (for performance tuning):**
```bash
docker exec -it rag_app python scripts/extract_existing_chunks.py --batch-size 20
```

### Options

- `--limit N`: Only process first N chunks (useful for testing)
- `--batch-size N`: Process N chunks at a time (default: 50)

### What Happens During Upload (Automatic)

When entity extraction is enabled (`ENABLE_ENTITY_EXTRACTION=true`), the upload flow is:

1. **Upload Document** → `/upload` endpoint
2. **Extract Text & Chunk** → Creates chunks in `chunks` table
3. **Generate Embeddings** → Stores in pgvector
4. **Extract Entities** → LLM extracts ML/DL concepts automatically
5. **Extract Relationships** → LLM identifies how concepts relate
6. **Return Response** → Shows entities/relationships count

### Environment Variables

Configure in `docker-compose.yml` or `.env`:

```bash
# Enable/disable automatic entity extraction on upload
ENABLE_ENTITY_EXTRACTION=true

# Confidence thresholds
ENTITY_CONFIDENCE_THRESHOLD=0.6
RELATIONSHIP_CONFIDENCE_THRESHOLD=0.6

# Gemini API configuration
GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash-exp
```

### Performance Notes

- Each chunk takes ~2-3 seconds to process (LLM API calls)
- 6,000 chunks ≈ 5-6 hours total processing time
- Processing happens in background, doesn't block upload response
- Failed extractions don't fail the upload

### Monitoring Progress

```bash
# Watch entity count grow
watch -n 5 'docker exec -it rag_postgres psql -U admin -d rag_db -c "SELECT COUNT(*) FROM entities;"'

# Check extraction logs
docker logs -f rag_app | grep "entity_extraction"
```
