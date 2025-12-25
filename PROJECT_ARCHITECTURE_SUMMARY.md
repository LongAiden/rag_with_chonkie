# 🏗️ Project Architecture Summary

**Date**: 2025-12-25
**Version**: 2.0 (After Reorganization)

---

## 📋 Table of Contents

1. [Project Structure](#project-structure)
2. [Design Patterns Implemented](#design-patterns-implemented)
3. [Module Responsibilities](#module-responsibilities)
4. [Import Guide](#import-guide)
5. [Graph Processing Analysis](#graph-processing-analysis)
6. [Recommendations](#recommendations)

---

## 🏗️ Project Structure

```
rag_llama_index/
│
├── ingestion/                  # 📥 Document Ingestion Pipeline
│   ├── processors/             # Abstract Method Pattern
│   │   ├── base_processor.py           # Abstract base class
│   │   ├── pdf_processor.py            # PDF implementation
│   │   ├── docx_processor.py           # DOCX implementation
│   │   ├── txt_processor.py            # TXT implementation
│   │   └── processor_factory.py        # Factory Method pattern
│   ├── chunking/               # Text Chunking
│   │   └── semantic_chunker.py         # Semantic chunking with Chonkie
│   ├── embedding/              # Vector Embeddings
│   │   └── vector_store.py             # pgvector storage
│   ├── extraction/             # Entity Extraction
│   │   └── extraction_flow.py          # Extraction orchestration
│   └── validation/             # File Validation
│       └── file_validator.py           # File type & security validation
│
├── retrieval/                  # 🔍 Search & Retrieval
│   ├── search.py                       # Vector similarity search
│   ├── reranking.py                    # BM25 reranking
│   ├── llm_operations.py               # LLM response generation
│   └── utils.py                        # Retrieval utilities
│
├── api/                        # 🌐 API Layer
│   ├── routes/
│   │   ├── document_routes.py          # Document upload/query endpoints
│   │   └── graph_routes.py             # Graph query endpoints
│   ├── app.py                          # FastAPI application
│   ├── config.py                       # Application configuration
│   ├── validators.py                   # Request validation
│   └── templates.py                    # HTML templates
│
├── graph_processing/           # 🕸️ Knowledge Graph
│   ├── entity_extraction.py            # Entity extraction with LLM
│   ├── relationship_extraction.py      # Relationship extraction
│   ├── graph_service.py                # Graph operations & queries
│   ├── extraction_service.py           # Extraction orchestration
│   └── entity_types.py                 # Entity/Relationship enums
│
├── models/                     # 📊 Data Models
│   ├── models.py                       # Pydantic models for API
│   └── graph_models.py                 # Graph-specific models
│
├── worker/                     # ⚙️ Background Workers
│   ├── celery_app.py                   # Celery configuration
│   └── tasks.py                        # Async task definitions
│
└── config/                     # ⚙️ Configuration
    ├── graph_config.py                 # Graph-specific config
    └── __init__.py
```

---

## 🎨 Design Patterns Implemented

### **1. Abstract Method Pattern** 🎭

**Location**: `ingestion/processors/`

**Purpose**: Standardize document processing across different file types

**Implementation**:

```python
# Abstract base class
class DocumentProcessor(ABC):
    @abstractmethod
    def extract_text(self, file_path) -> Tuple[str, PageMapping]:
        """Each processor implements differently"""
        pass

    @abstractmethod
    def validate_file(self, file_path) -> bool:
        """Each processor validates differently"""
        pass

    def process_document(self, file_path):
        """Template Method - same workflow for all"""
        self.validate_file(file_path)       # Polymorphic call
        text, mapping = self.extract_text() # Polymorphic call
        chunks = self.chunk_text(text)      # Shared logic
        return chunks
```

**Concrete Implementations**:
- `PDFProcessor` - Uses PyPDF2
- `DOCXProcessor` - Uses python-docx
- `TXTProcessor` - Plain text reading

**Benefits**:
- ✅ Consistent interface across all processors
- ✅ Shared workflow (Template Method)
- ✅ Easy to add new file types (just create new class)
- ✅ Python's `@abstractmethod` catches missing implementations

---

### **2. Factory Method Pattern** 🏭

**Location**: `ingestion/processors/processor_factory.py`

**Purpose**: Automatically select the right processor based on file type

**Implementation**:

```python
class ProcessorRegistry:
    def __init__(self):
        self._processors = [
            PDFProcessor(),
            DOCXProcessor(),
            TXTProcessor(),
        ]

    def get_processor(self, file_path) -> DocumentProcessor:
        """Factory Method - returns appropriate processor"""
        for processor in self._processors:
            if processor.can_process(file_path):
                return processor
        raise ValueError("No processor found")

# Usage - No IF-ELSE needed!
processor = get_processor_for_file('document.pdf')  # Returns PDFProcessor
chunks = processor.process_document('document.pdf')  # Polymorphism
```

**Benefits**:
- ✅ No IF-ELSE chains
- ✅ Centralized processor management
- ✅ Plugin-style architecture
- ✅ Easy to add new processors

---

### **3. Separation of Concerns** 🎯

Each module has a single, well-defined responsibility:

| Module | Responsibility | Key Classes |
|--------|---------------|-------------|
| `ingestion/` | Document → Chunks → Embeddings | `ChunkEmbeddingPipeline` |
| `retrieval/` | Search → Rerank → Generate | `BM25Reranker`, LLM functions |
| `api/` | HTTP requests → Responses | FastAPI routes |
| `graph_processing/` | Entity/Relationship extraction | `EntityExtractor`, `GraphService` |
| `worker/` | Background tasks | Celery tasks |

---

## 📦 Module Responsibilities

### **Ingestion Module** (`ingestion/`)

**What it does**: Transforms raw documents into searchable vector embeddings

**Flow**:
```
Document → Validate → Extract Text → Chunk → Embed → Store in pgvector
```

**Key Components**:
- **Processors**: Handle different file types (PDF, DOCX, TXT)
- **Chunker**: Semantic chunking using Chonkie
- **Vector Store**: pgvector storage with embeddings
- **Validator**: File type, size, security validation

**Usage**:
```python
from ingestion import process_document_with_processor
from ingestion.embedding import ChunkEmbeddingPipeline

# Process document
chunks = process_document_with_processor('document.pdf', chunk_size=512)

# Store with embeddings
pipeline = ChunkEmbeddingPipeline(db_params, 'all-MiniLM-L6-v2', 'chunks')
doc_id = await pipeline.process_document('document.pdf')
```

---

### **Retrieval Module** (`retrieval/`)

**What it does**: Finds relevant chunks and generates LLM responses

**Flow**:
```
Query → Vector Search → BM25 Rerank → Graph Enrichment → LLM Generation
```

**Key Components**:
- **Search**: pgvector cosine similarity
- **Reranking**: BM25 keyword-based reranking
- **LLM Operations**: Structured response generation
- **Utils**: BM25 scorer and utilities

**Usage**:
```python
from retrieval import perform_document_search

result = await perform_document_search(
    query="What is ResNet?",
    limit=5,
    threshold=0.7,
    pipeline=pipeline
)
# Returns: RAGResponse with answer, sources, confidence
```

---

### **API Module** (`api/`)

**What it does**: Exposes HTTP endpoints for document upload and querying

**Endpoints**:
- `POST /upload` - Upload and process documents
- `POST /query` - Query documents with RAG
- `GET /stats` - Database statistics
- `GET /health` - Health check
- `GET /supported-types` - Get supported file types (dynamic!)
- `DELETE /table/{name}` - Delete table

**Usage**:
```bash
# Upload
curl -X POST http://localhost:8000/upload -F "file=@doc.pdf"

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is ResNet?", "limit": 5}'
```

---

## 📚 Import Guide

### **Ingestion**

```python
# Processors (Abstract Method Pattern)
from ingestion.processors import (
    DocumentProcessor,         # Abstract base class
    PDFProcessor,             # PDF implementation
    DOCXProcessor,            # DOCX implementation
    TXTProcessor,             # TXT implementation
    get_processor_for_file,   # Factory function
    get_registry              # Get processor registry
)

# Chunking
from ingestion.chunking import (
    process_document_with_processor,  # RECOMMENDED
    process_document,                 # DEPRECATED
    get_supported_file_types,
    list_available_processors
)

# Embedding
from ingestion.embedding import (
    ChunkEmbeddingPipeline,
    EmbeddingGenerator,
    VectorStore
)

# Extraction
from ingestion.extraction import run_entity_extraction_for_document

# Validation
from ingestion.validation import FileValidator, ValidationResult
```

### **Retrieval**

```python
from retrieval import (
    perform_document_search,  # Main search function
    generate_llm_response,    # LLM response generation
    BM25Reranker              # BM25 reranking
)
```

### **API**

```python
from api import app, get_pipeline
from api.config import AppConfig
from api.validators import validate_upload_params
```

### **Graph Processing**

```python
from graph_processing import (
    EntityExtractor,
    RelationshipExtractor,
    GraphService,
    EntityType,
    RelationshipType
)
```

---

## 🕸️ Graph Processing Analysis

### **Current Structure** ✅ GOOD

```
graph_processing/
├── entity_extraction.py         (433 lines) - Entity extraction with Gemini
├── relationship_extraction.py   (301 lines) - Relationship extraction
├── graph_service.py             (392 lines) - Graph queries & operations
├── extraction_service.py        (311 lines) - Orchestration
└── entity_types.py              (141 lines) - Enums & type definitions
```

### **Assessment** 📊

| Aspect | Status | Notes |
|--------|--------|-------|
| **Organization** | ✅ Good | Clear separation of concerns |
| **Size** | ✅ Reasonable | Files 140-433 lines (manageable) |
| **Patterns** | ⚠️ Could improve | No abstract patterns yet |
| **Coupling** | ⚠️ Moderate | Direct Gemini API coupling |
| **Extensibility** | ⚠️ Limited | Hard to add new LLM providers |

### **Current Design**

```python
# Direct coupling to Gemini
class EntityExtractor:
    def __init__(self, gemini_api_key, gemini_model):
        genai.configure(api_key=gemini_api_key)  # Hardcoded to Gemini
        self.model = genai.GenerativeModel(gemini_model)

    async def extract_entities(self, text):
        response = self.model.generate_content(prompt)  # Gemini-specific
        return self._parse_entities(response.text)
```

**Problems**:
- ❌ Tightly coupled to Gemini API
- ❌ Can't easily switch to OpenAI/Claude
- ❌ Duplicate LLM calling code
- ❌ Hard to test (mocking Gemini)

---

### **Recommended Refactoring** 💡

Apply the **same Abstract Method + Factory patterns** used in document processing!

#### **Proposed Structure**

```
graph_processing/
├── extractors/                  # NEW - Abstract Method Pattern
│   ├── __init__.py
│   ├── base_extractor.py       # Abstract LLM extractor
│   ├── gemini_extractor.py     # Gemini implementation
│   ├── openai_extractor.py     # OpenAI implementation (future)
│   └── extractor_factory.py    # Factory Method
│
├── services/                    # Orchestration
│   ├── entity_service.py       # Entity extraction orchestration
│   ├── relationship_service.py # Relationship extraction orchestration
│   └── graph_service.py        # Graph queries
│
├── types/                       # Type definitions
│   └── entity_types.py
│
└── __init__.py
```

#### **Proposed Design**

```python
# base_extractor.py - Abstract Method Pattern
from abc import ABC, abstractmethod

class BaseLLMExtractor(ABC):
    """Abstract base class for LLM-based extractors"""

    @abstractmethod
    async def generate_entities(self, text: str, schema: dict) -> List[Entity]:
        """Extract entities using LLM - implementation varies by provider"""
        pass

    @abstractmethod
    async def generate_relationships(self, text: str, entities: List) -> List[Relationship]:
        """Extract relationships - implementation varies by provider"""
        pass

    # Shared logic
    def filter_by_confidence(self, results, threshold):
        return [r for r in results if r.confidence >= threshold]


# gemini_extractor.py - Concrete implementation
class GeminiExtractor(BaseLLMExtractor):
    def __init__(self, api_key, model):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    async def generate_entities(self, text, schema):
        prompt = self._create_entity_prompt(text, schema)
        response = self.model.generate_content(prompt)
        return self._parse_entities(response.text)


# openai_extractor.py - Future implementation
class OpenAIExtractor(BaseLLMExtractor):
    def __init__(self, api_key, model):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    async def generate_entities(self, text, schema):
        # OpenAI-specific implementation
        response = self.client.chat.completions.create(
            model=self.model,
            functions=[self._entity_function(schema)],
            messages=[{"role": "user", "content": text}]
        )
        return self._parse_entities(response)


# extractor_factory.py - Factory Method
class ExtractorFactory:
    @staticmethod
    def create(provider: str, api_key: str, model: str) -> BaseLLMExtractor:
        if provider == "gemini":
            return GeminiExtractor(api_key, model)
        elif provider == "openai":
            return OpenAIExtractor(api_key, model)
        elif provider == "claude":
            return ClaudeExtractor(api_key, model)
        raise ValueError(f"Unknown provider: {provider}")


# Usage - Easy to switch providers!
extractor = ExtractorFactory.create("gemini", api_key, "gemini-2.5-flash")
entities = await extractor.generate_entities(text, schema)

# Later, switch to OpenAI:
extractor = ExtractorFactory.create("openai", api_key, "gpt-4")
entities = await extractor.generate_entities(text, schema)  # Same interface!
```

#### **Benefits**

| Benefit | Impact |
|---------|--------|
| **Multi-LLM Support** | ✅ Easy to add OpenAI, Claude, local models |
| **Testing** | ✅ Easy to mock with test doubles |
| **Configuration** | ✅ Switch LLM via config file |
| **Consistency** | ✅ Same patterns as document processing |
| **Maintainability** | ✅ Single responsibility per class |

---

## 🎯 Recommendations

### **Priority 1: Keep Current Changes** ✅

The ingestion/retrieval/api reorganization is excellent:
- ✅ Clear separation of concerns
- ✅ Easy to navigate
- ✅ Follows single responsibility principle
- ✅ Consistent with design patterns

### **Priority 2: Refactor Graph Processing** 🔄

Apply Abstract Method + Factory patterns to graph processing:

**Phase 1**: Create abstract extractor
```bash
graph_processing/extractors/base_extractor.py
```

**Phase 2**: Migrate Gemini logic
```bash
graph_processing/extractors/gemini_extractor.py
```

**Phase 3**: Add factory
```bash
graph_processing/extractors/extractor_factory.py
```

**Phase 4**: Update services to use factory
```python
# extraction_service.py
from graph_processing.extractors import create_extractor

extractor = create_extractor(
    provider=config.llm_provider,  # "gemini", "openai", etc.
    api_key=config.api_key,
    model=config.model_name
)
```

### **Priority 3: Documentation** 📚

- ✅ **ABSTRACTION_PATTERN_SUMMARY.md** - Created
- ✅ **MIGRATION_COMPLETE.md** - Created
- ✅ **REORGANIZATION_GUIDE.md** - Created
- ✅ **PROJECT_ARCHITECTURE_SUMMARY.md** - This file
- ⚠️ **GRAPH_REFACTORING_GUIDE.md** - TODO (if refactoring graph)

---

## 📊 Metrics

### **Before Reorganization**

- Modules: 1 (`document_processing/`)
- Files: 19 files in one folder
- Responsibilities: Mixed (processing, retrieval, API)
- Design Patterns: None
- Extensibility: Low

### **After Reorganization**

- Modules: 3 (`ingestion/`, `retrieval/`, `api/`)
- Files: Organized by responsibility
- Responsibilities: Single per module
- Design Patterns: 2 (Abstract Method, Factory Method)
- Extensibility: High ✅

---

## 🎓 Key Takeaways

1. **Abstract Method Pattern** = Consistent interface + Polymorphism
2. **Factory Method Pattern** = No IF-ELSE + Easy extension
3. **Separation of Concerns** = Easier to find, test, maintain
4. **Same patterns throughout** = Consistent codebase

**Result**: Clean, maintainable, scalable architecture! 🚀

---

## 📚 Related Documentation

- [Abstract Method & Factory Patterns](ABSTRACTION_PATTERN_SUMMARY.md)
- [Migration Guide](MIGRATION_COMPLETE.md)
- [Reorganization Guide](REORGANIZATION_GUIDE.md)
- [Cleanup Summary](CLEANUP_SUMMARY.md)

---

**Status**: ✅ Architecture v2.0 Complete

**Next Steps**:
1. Optional: Refactor graph processing to use same patterns
2. Add more file type processors (HTML, ePub, Markdown)
3. Add more LLM providers (OpenAI, Claude)
4. Add comprehensive tests

