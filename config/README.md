# Graph Configuration Guide

## Overview

The `config/` module contains all configuration for the knowledge graph and entity extraction system.

## Configuration File

**Main File**: [graph_config.py](graph_config.py)

This file contains the `GraphConfig` class with all configurable parameters for:
- Entity extraction settings
- Relationship extraction settings
- Graph algorithm parameters
- LLM configuration
- Performance tuning
- Database settings

## Usage

### 1. Import Configuration

```python
from config import graph_config, get_graph_config

# Access settings directly
threshold = graph_config.entity_confidence_threshold
model = graph_config.gemini_model

# Or get fresh instance
config = get_graph_config()
```

### 2. Use in Entity Extraction

```python
from config import graph_config
from graph_processing import EntityExtractor

# Config values are automatically used
extractor = EntityExtractor(
    db_pool=pool,
    gemini_api_key=graph_config.gemini_api_key,
    embedding_model=embedding_model
)

# Extract with configured threshold
entities = await extractor.extract_entities_from_chunk(
    chunk_id=chunk_id,
    chunk_text=text,
    confidence_threshold=graph_config.entity_confidence_threshold
)
```

### 3. Check Enabled Entity Types

```python
from config import is_entity_type_enabled, is_relationship_type_enabled

# Check if entity type is enabled
if is_entity_type_enabled("MODEL"):
    # Process MODEL entities
    pass

# Check if relationship type is enabled
if is_relationship_type_enabled("USES"):
    # Process USES relationships
    pass
```

## Configuration Parameters

### Entity Extraction
| Parameter | Default | Description |
|-----------|---------|-------------|
| `entity_confidence_threshold` | 0.6 | Minimum confidence (0-1) for entities |
| `entity_extraction_enabled` | true | Enable entity extraction |
| `max_entities_per_chunk` | 50 | Max entities per chunk |
| `enabled_entity_types` | [list] | Enabled entity types |

### Relationship Extraction
| Parameter | Default | Description |
|-----------|---------|-------------|
| `relationship_confidence_threshold` | 0.6 | Minimum confidence (0-1) |
| `relationship_extraction_enabled` | true | Enable relationship extraction |
| `max_relationships_per_chunk` | 100 | Max relationships per chunk |
| `enabled_relationship_types` | [list] | Enabled relationship types |

### Graph Algorithms
| Parameter | Default | Description |
|-----------|---------|-------------|
| `default_max_hops` | 2 | Default hops for connectivity queries |
| `pagerank_damping_factor` | 0.85 | PageRank damping factor |
| `pagerank_max_iterations` | 100 | Max PageRank iterations |

### LLM Configuration
| Parameter | Default | Description |
|-----------|---------|-------------|
| `gemini_api_key` | from env | Gemini API key |
| `gemini_model` | gemini-2.5-flash | Gemini model name |

### Embedding Configuration
| Parameter | Default | Description |
|-----------|---------|-------------|
| `entity_embedding_model` | all-MiniLM-L6-v2 | SentenceTransformer model |
| `entity_embedding_dimension` | 384 | Embedding dimension |

### Performance
| Parameter | Default | Description |
|-----------|---------|-------------|
| `batch_size` | 10 | Batch processing size |
| `enable_parallel_extraction` | true | Parallel processing |
| `enable_entity_caching` | true | Cache entity lookups |
| `cache_ttl_seconds` | 3600 | Cache TTL (1 hour) |

### Database
| Parameter | Default | Description |
|-----------|---------|-------------|
| `db_pool_min_size` | 2 | Min connection pool size |
| `db_pool_max_size` | 10 | Max connection pool size |
| `db_pool_timeout` | 30.0 | Connection timeout (seconds) |

### Logging
| Parameter | Default | Description |
|-----------|---------|-------------|
| `log_level` | INFO | Logging level |
| `log_entity_extraction` | true | Log entity extraction |
| `log_relationship_extraction` | true | Log relationship extraction |

## Environment Variables

Add these to your [.env](../deployment/.env) file:

```bash
# Entity Extraction
ENTITY_CONFIDENCE_THRESHOLD=0.6
ENTITY_EXTRACTION_ENABLED=true
MAX_ENTITIES_PER_CHUNK=50

# Relationship Extraction
RELATIONSHIP_CONFIDENCE_THRESHOLD=0.6
RELATIONSHIP_EXTRACTION_ENABLED=true
MAX_RELATIONSHIPS_PER_CHUNK=100

# Graph Algorithms
DEFAULT_MAX_HOPS=2
PAGERANK_DAMPING_FACTOR=0.85
PAGERANK_MAX_ITERATIONS=100

# LLM
GOOGLE_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.5-flash

# Performance
BATCH_SIZE=10
ENABLE_PARALLEL_EXTRACTION=true
ENABLE_ENTITY_CACHING=true
CACHE_TTL_SECONDS=3600

# Logging
LOG_LEVEL=INFO
LOG_ENTITY_EXTRACTION=true
LOG_RELATIONSHIP_EXTRACTION=true
```

## Customization Examples

### 1. Higher Quality Extraction (Higher Threshold)

```bash
# .env
ENTITY_CONFIDENCE_THRESHOLD=0.75
RELATIONSHIP_CONFIDENCE_THRESHOLD=0.75
```

More precise but fewer entities/relationships extracted.

### 2. Enable Specific Entity Types Only

Edit [graph_config.py](graph_config.py):

```python
enabled_entity_types: List[str] = Field(
    default=["MODEL", "ALGORITHM", "DATASET", "METRIC"],
    description="Only extract these entity types"
)
```

### 3. Increase Batch Size for Faster Processing

```bash
# .env
BATCH_SIZE=20
ENABLE_PARALLEL_EXTRACTION=true
```

### 4. Debug Mode

```bash
# .env
LOG_LEVEL=DEBUG
LOG_ENTITY_EXTRACTION=true
LOG_RELATIONSHIP_EXTRACTION=true
```

## Helper Functions

### Get All Extraction Config
```python
from config import get_extraction_config

config = get_extraction_config()
# Returns:
# {
#     "entity_confidence_threshold": 0.6,
#     "relationship_confidence_threshold": 0.6,
#     "max_entities_per_chunk": 50,
#     "max_relationships_per_chunk": 100,
#     "enabled_entity_types": [...],
#     "enabled_relationship_types": [...]
# }
```

### Check Entity Type
```python
from config import is_entity_type_enabled

if is_entity_type_enabled("ALGORITHM"):
    # ALGORITHM type is enabled
    pass
```

### Check Relationship Type
```python
from config import is_relationship_type_enabled

if is_relationship_type_enabled("TRAINED_ON"):
    # TRAINED_ON type is enabled
    pass
```

## Best Practices

1. **Use Environment Variables** - Don't hardcode values, use .env
2. **Start with Defaults** - Default settings work well for most cases
3. **Adjust Thresholds** - Tune based on your data quality needs
4. **Monitor Performance** - Watch extraction times and API costs
5. **Cache Aggressively** - Enable caching for production

## Files

- [graph_config.py](graph_config.py) - Main configuration class
- [__init__.py](__init__.py) - Module exports
- [README.md](README.md) - This file

## Related Documentation

- [GRAPH_INTEGRATION_GUIDE.md](../GRAPH_INTEGRATION_GUIDE.md) - Complete integration guide
- [entity_types.py](../graph_processing/entity_types.py) - All entity/relationship types
- [.env.example](../deployment/.env.example) - Environment variables template
