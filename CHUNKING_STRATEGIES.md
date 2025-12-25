# Chunking Strategies Guide

This project supports 3 chunking strategies with **RecursiveChunker as default**.

## Available Strategies

### 1. RecursiveChunker (DEFAULT) ⚡
**Best balance of speed and quality**

- **Speed**: Fast (10-20 seconds for 15MB)
- **Quality**: Excellent - respects natural text boundaries
- **Use when**: Most use cases (recommended)

Splits on natural boundaries in order:
1. Paragraphs (`\n\n`)
2. Line breaks (`\n`)
3. Sentences (`. `, `! `, `? `)
4. Clauses (`, `, `; `)
5. Words (` `)
6. Characters (fallback)

### 2. TokenChunker 🚀
**Fastest, simple token-based**

- **Speed**: Very fast (3-5 seconds for 15MB)
- **Quality**: Good - predictable chunk sizes
- **Use when**: Speed is critical, large documents

Simple token counting with overlap.

### 3. SemanticChunker 🧠
**Highest quality, AI-powered**

- **Speed**: Very slow (5-30 minutes for 15MB)
- **Quality**: Perfect semantic boundaries
- **Use when**: Small documents (<500KB), quality > speed

Uses embeddings to find semantic topic changes.

## How to Use

### Method 1: Environment Variable (Global Setting)

Set `CHUNKER_TYPE` in your `.env` file or docker-compose.yml:

```bash
# .env
CHUNKER_TYPE=recursive  # Options: token, recursive, semantic
```

```yaml
# docker-compose.yml
services:
  app:
    environment:
      - CHUNKER_TYPE=recursive  # or token, semantic
```

### Method 2: API Parameter (Per Request)

Pass `chunker_type` when uploading:

```bash
# Use RecursiveChunker (default)
curl -X POST "http://localhost:8000/upload" \
  -F "file=@document.pdf" \
  -F "chunk_size=512"

# Use TokenChunker (fastest)
curl -X POST "http://localhost:8000/upload" \
  -F "file=@document.pdf" \
  -F "chunk_size=512" \
  -F "chunker_type=token"

# Use SemanticChunker (best quality, slow)
curl -X POST "http://localhost:8000/upload" \
  -F "file=@document.pdf" \
  -F "chunk_size=512" \
  -F "chunker_type=semantic"
```

### Method 3: Python Code

```python
from ingestion.chunking.chunker_factory import chunk_text

# Use default (recursive)
chunks = chunk_text(document_text, chunk_size=512)

# Use specific strategy
chunks = chunk_text(document_text, chunker_type="token")
chunks = chunk_text(document_text, chunker_type="recursive")
chunks = chunk_text(document_text, chunker_type="semantic")
```

## Performance Comparison

| Document Size | Token | Recursive | Semantic |
|--------------|-------|-----------|----------|
| 1MB PDF | 1s | 3s | 2 min |
| 5MB PDF | 3s | 10s | 10 min |
| 15MB PDF | 5s | 20s | 30 min |

## Recommendations

### 📚 Large Documents (>5MB)
**Use: TokenChunker** (`chunker_type=token`)
- Processes 15MB in 5 seconds
- Good quality for most RAG tasks

### 📄 Medium Documents (1-5MB)
**Use: RecursiveChunker** (default, no parameter needed)
- Best balance of speed and quality
- Respects paragraphs and sentences
- **RECOMMENDED for most use cases**

### 📝 Small Documents (<1MB)
**Use: RecursiveChunker or SemanticChunker**
- RecursiveChunker: Fast enough, excellent quality
- SemanticChunker: Perfect semantic boundaries if quality is critical

## Example Configurations

### For Production (Speed)
```bash
CHUNKER_TYPE=token
```

### For Best Quality (Balanced)
```bash
CHUNKER_TYPE=recursive  # DEFAULT
```

### For Research (Perfect Quality)
```bash
CHUNKER_TYPE=semantic
# Only for small documents!
```

## Advanced Configuration

Adjust chunk parameters:

```python
from ingestion.chunking.chunker_factory import get_chunker

# Token: Adjust overlap
chunker = get_chunker("token", chunk_size=512, chunk_overlap=100)

# Recursive: Same parameters
chunker = get_chunker("recursive", chunk_size=512, chunk_overlap=50)

# Semantic: Adjust threshold (lower = faster, larger chunks)
chunker = get_chunker("semantic",
                     chunk_size=512,
                     similarity_threshold=0.3)  # 0.3-0.7 recommended
```

## Troubleshooting

### Document taking too long to process?
→ Switch to `token` or `recursive` chunker

### Want better semantic boundaries?
→ Use `recursive` (good) or `semantic` (perfect but slow)

### Need consistent chunk sizes?
→ Use `token` chunker

### Default not working?
→ Check `CHUNKER_TYPE` environment variable
→ Restart services after changing env vars
