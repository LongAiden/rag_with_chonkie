# Entity Configuration Reference

## 📍 Where is the Entities Config?

The entity and graph configuration is spread across multiple files. Here's where to find everything:

---

## 1. 🎛️ Main Configuration Module

**Location**: [config/graph_config.py](config/graph_config.py)

This is the **primary configuration file** containing all settings:

```python
from config import graph_config, get_graph_config

# Access configuration
threshold = graph_config.entity_confidence_threshold  # 0.6
model = graph_config.gemini_model  # "gemini-2.0-flash-exp"
max_entities = graph_config.max_entities_per_chunk  # 50
```

**Key Settings**:
- ✅ Entity extraction thresholds
- ✅ Relationship extraction thresholds
- ✅ LLM model configuration
- ✅ Graph algorithm parameters
- ✅ Performance tuning
- ✅ Database pool settings
- ✅ Logging configuration

---

## 2. 🏷️ Entity & Relationship Types

**Location**: [graph_processing/entity_types.py](graph_processing/entity_types.py)

This file defines **40+ entity types** and **25+ relationship types** for ML/DL domain:

```python
from graph_processing.entity_types import EntityType, RelationshipType

# Available entity types
EntityType.MODEL          # "MODEL" - ResNet, BERT, GPT, etc.
EntityType.ALGORITHM      # "ALGORITHM" - Backpropagation, SGD, etc.
EntityType.DATASET        # "DATASET" - ImageNet, COCO, etc.
EntityType.TECHNIQUE      # "TECHNIQUE" - Dropout, Normalization, etc.
# ... 40+ more types

# Available relationship types
RelationshipType.USES           # "USES"
RelationshipType.TRAINED_ON     # "TRAINED_ON"
RelationshipType.IMPROVES       # "IMPROVES"
RelationshipType.OUTPERFORMS    # "OUTPERFORMS"
# ... 25+ more types
```

**Customize Entity Types**:
Edit the `enabled_entity_types` list in [config/graph_config.py:128](config/graph_config.py#L128):

```python
enabled_entity_types: List[str] = Field(
    default=[
        "ALGORITHM", "MODEL", "ARCHITECTURE", "TECHNIQUE",
        "DATASET", "METRIC", "TASK", "FRAMEWORK",
        # Add or remove types here
    ],
    description="Enabled entity types for extraction"
)
```

---

## 3. 🌍 Environment Variables

**Location**: [deployment/.env](deployment/.env) or [deployment/.env.example](deployment/.env.example)

Configuration values can be overridden via environment variables:

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

# LLM
GOOGLE_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.0-flash-exp

# Embedding
ENTITY_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENTITY_EMBEDDING_DIMENSION=384

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

---

## 4. 📚 Entity Type Descriptions

**Location**: [graph_processing/entity_types.py:173](graph_processing/entity_types.py#L173)

Descriptions used by the LLM for entity extraction:

```python
ENTITY_TYPE_DESCRIPTIONS = {
    EntityType.ALGORITHM: "A computational procedure or formula (e.g., backpropagation, gradient descent)",
    EntityType.MODEL: "A specific ML/DL model instance (e.g., BERT, GPT-3, ResNet-50)",
    EntityType.ARCHITECTURE: "A model structure or design pattern (e.g., Transformer, CNN, LSTM)",
    EntityType.TECHNIQUE: "A method or approach (e.g., dropout, batch normalization)",
    EntityType.DATASET: "A collection of data used for training/evaluation (e.g., ImageNet, MNIST)",
    # ... more descriptions
}
```

**Customize Descriptions**: Edit this dictionary to change how the LLM understands entity types.

---

## 5. 🔗 Relationship Type Descriptions

**Location**: [graph_processing/entity_types.py:184](graph_processing/entity_types.py#L184)

Descriptions used by the LLM for relationship extraction:

```python
RELATIONSHIP_TYPE_DESCRIPTIONS = {
    RelationshipType.IS_A: "Entity is a type/instance of another (hierarchical)",
    RelationshipType.USES: "Entity uses or employs another entity",
    RelationshipType.IMPROVES: "Entity improves or enhances another",
    RelationshipType.TRAINED_ON: "Model is trained on a dataset",
    # ... more descriptions
}
```

---

## 📊 Configuration Hierarchy

```
Priority (High to Low):
1. Environment Variables (.env)          ← Highest priority
2. GraphConfig defaults (graph_config.py) ← Default values
3. Function parameters                    ← Override at call time
```

**Example**:
```python
# 1. Set in .env
ENTITY_CONFIDENCE_THRESHOLD=0.7

# 2. Default in graph_config.py (if not in .env)
entity_confidence_threshold: float = Field(default=0.6)

# 3. Override at call time
entities = await extractor.extract_entities_from_chunk(
    chunk_id=chunk_id,
    chunk_text=text,
    confidence_threshold=0.8  # ← Overrides everything
)
```

---

## 🎯 Quick Configuration Tasks

### Change Entity Confidence Threshold
**File**: [deployment/.env](deployment/.env)
```bash
ENTITY_CONFIDENCE_THRESHOLD=0.75  # Higher = more precise, fewer entities
```

### Enable Only Specific Entity Types
**File**: [config/graph_config.py:128](config/graph_config.py#L128)
```python
enabled_entity_types: List[str] = Field(
    default=["MODEL", "DATASET", "ALGORITHM"],  # Only these 3 types
)
```

### Change LLM Model
**File**: [deployment/.env](deployment/.env)
```bash
GEMINI_MODEL=gemini-1.5-pro  # Use Pro model instead
```

### Increase Batch Size for Faster Processing
**File**: [deployment/.env](deployment/.env)
```bash
BATCH_SIZE=20
ENABLE_PARALLEL_EXTRACTION=true
```

### Add Custom Entity Type
**File**: [graph_processing/entity_types.py:15](graph_processing/entity_types.py#L15)
```python
class EntityType(str, Enum):
    # Existing types...
    CUSTOM_TYPE = "CUSTOM_TYPE"  # ← Add your custom type
```

### Add Custom Relationship Type
**File**: [graph_processing/entity_types.py:77](graph_processing/entity_types.py#L77)
```python
class RelationshipType(str, Enum):
    # Existing types...
    CUSTOM_RELATION = "CUSTOM_RELATION"  # ← Add your custom relationship
```

---

## 📁 File Summary

| File | Purpose | What to Configure |
|------|---------|-------------------|
| [config/graph_config.py](config/graph_config.py) | Main config | All settings, defaults, enabled types |
| [graph_processing/entity_types.py](graph_processing/entity_types.py) | Entity/Relationship definitions | Add new types, edit descriptions |
| [deployment/.env](deployment/.env) | Environment variables | Override any config value |
| [config/README.md](config/README.md) | Config documentation | Learn about all parameters |

---

## 🔧 Usage Examples

### 1. Access Config in Code
```python
from config import graph_config

# Get settings
threshold = graph_config.entity_confidence_threshold
model = graph_config.gemini_model
max_hops = graph_config.default_max_hops
```

### 2. Check if Entity Type is Enabled
```python
from config import is_entity_type_enabled

if is_entity_type_enabled("MODEL"):
    # Process MODEL entities
    pass
```

### 3. Get Full Extraction Config
```python
from config import get_extraction_config

config = get_extraction_config()
print(config)
# {
#     "entity_confidence_threshold": 0.6,
#     "relationship_confidence_threshold": 0.6,
#     "max_entities_per_chunk": 50,
#     "max_relationships_per_chunk": 100,
#     "enabled_entity_types": [...],
#     "enabled_relationship_types": [...]
# }
```

### 4. Use Config in Entity Extraction
```python
from config import graph_config
from graph_processing import EntityExtractor

extractor = EntityExtractor(
    db_pool=pool,
    gemini_api_key=graph_config.gemini_api_key,
    embedding_model=embedding_model
)

# Uses configured threshold
entities = await extractor.extract_entities_from_chunk(
    chunk_id=chunk_id,
    chunk_text=text,
    confidence_threshold=graph_config.entity_confidence_threshold
)
```

---

## 🚀 Getting Started

1. **Review defaults** in [config/graph_config.py](config/graph_config.py)
2. **Copy .env.example** to .env: `cp deployment/.env.example deployment/.env`
3. **Set your API key**: Add `GOOGLE_API_KEY=your-key` to .env
4. **Customize thresholds** if needed in .env
5. **Start using** the configuration in your code

---

## 📖 Related Documentation

- [GRAPH_INTEGRATION_GUIDE.md](GRAPH_INTEGRATION_GUIDE.md) - Complete integration guide
- [config/README.md](config/README.md) - Detailed configuration documentation
- [graph_processing/entity_types.py](graph_processing/entity_types.py) - All entity & relationship types

---

**TL;DR**:
- **Main config**: [config/graph_config.py](config/graph_config.py)
- **Entity types**: [graph_processing/entity_types.py](graph_processing/entity_types.py)
- **Environment variables**: [deployment/.env](deployment/.env)
- **Import**: `from config import graph_config`
