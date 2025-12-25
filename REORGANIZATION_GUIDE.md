# 🔄 Project Reorganization Guide

**Date**: 2025-12-25
**Status**: ✅ In Progress - Files Moved, Imports Need Updating

---

## 📋 What Changed

### **Old Structure** ❌
```
rag_llama_index/
└── document_processing/  (19 files - too many responsibilities!)
    ├── base_processor.py
    ├── pdf_processor.py
    ├── api_routes.py
    ├── retrieval.py
    └── ... (mixed concerns)
```

### **New Structure** ✅
```
rag_llama_index/
├── ingestion/              # Document Processing & Ingestion
│   ├── processors/         # Abstract Method pattern processors
│   │   ├── __init__.py
│   │   ├── base_processor.py
│   │   ├── pdf_processor.py
│   │   ├── docx_processor.py
│   │   ├── txt_processor.py
│   │   └── processor_factory.py
│   ├── chunking/           # Text chunking
│   │   ├── __init__.py
│   │   └── semantic_chunker.py (was: chunk_pdf_with_chonkie.py)
│   ├── embedding/          # Embedding & vector storage
│   │   ├── __init__.py
│   │   └── vector_store.py (was: embed_chunks_to_db.py)
│   ├── extraction/         # Entity extraction
│   │   ├── __init__.py
│   │   └── extraction_flow.py
│   └── validation/         # File validation
│       ├── __init__.py
│       └── file_validator.py
│
├── retrieval/              # Search & Retrieval
│   ├── __init__.py
│   ├── search.py (was: retrieval.py)
│   ├── reranking.py (was: reranker.py)
│   ├── llm_operations.py
│   └── utils.py
│
├── api/                    # API Layer
│   ├── routes/
│   │   ├── __init__.py
│   │   └── document_routes.py (was: api_routes.py)
│   ├── __init__.py
│   ├── app.py (was: full_pipeline_pgvector.py)
│   ├── config.py
│   ├── validators.py
│   └── templates.py
│
├── graph_processing/       # (Unchanged)
├── models/                 # (Unchanged)
├── worker/                 # (Unchanged)
└── config/                 # (Unchanged)
```

---

## 🔧 Import Changes Required

### **1. Processor Imports**

```python
# OLD
from document_processing.base_processor import DocumentProcessor
from document_processing.pdf_processor import PDFProcessor
from document_processing.processor_factory import get_processor_for_file

# NEW
from ingestion.processors import DocumentProcessor
from ingestion.processors import PDFProcessor
from ingestion.processors import get_processor_for_file
```

### **2. Chunking Imports**

```python
# OLD
from document_processing.chunk_pdf_with_chonkie import process_document_with_processor
from document_processing.chunk_pdf_with_chonkie import get_supported_file_types

# NEW
from ingestion.chunking import process_document_with_processor
from ingestion.chunking import get_supported_file_types
```

### **3. Embedding Imports**

```python
# OLD
from document_processing.embed_chunks_to_db import ChunkEmbeddingPipeline

# NEW
from ingestion.embedding import ChunkEmbeddingPipeline
```

### **4. Extraction Imports**

```python
# OLD
from document_processing.extraction_flow import run_entity_extraction_for_document

# NEW
from ingestion.extraction import run_entity_extraction_for_document
```

### **5. Validation Imports**

```python
# OLD
from document_processing.file_validator import FileValidator

# NEW
from ingestion.validation import FileValidator
```

### **6. Retrieval Imports**

```python
# OLD
from document_processing.retrieval import perform_document_search
from document_processing.reranker import BM25Reranker
from document_processing.llm_operations import generate_llm_response

# NEW
from retrieval import perform_document_search
from retrieval import BM25Reranker
from retrieval import generate_llm_response
```

### **7. API Imports**

```python
# OLD
from document_processing.config import AppConfig
from document_processing.validators import validate_upload_params
from document_processing.full_pipeline_pgvector import app

# NEW
from api.config import AppConfig
from api.validators import validate_upload_params
from api.app import app
```

---

## 📝 Files That Need Import Updates

### **Priority 1: Moved Files (Internal Imports)**

These files were moved and need their internal imports updated:

1. ✅ `ingestion/processors/base_processor.py`
   - Update: `from .chunk_pdf_with_chonkie import` → `from ingestion.chunking import`

2. ✅ `ingestion/chunking/semantic_chunker.py`
   - Update: `from .processor_factory import` → `from ingestion.processors import`

3. ✅ `ingestion/embedding/vector_store.py`
   - Update: `from document_processing.chunk_pdf_with_chonkie import` → `from ingestion.chunking import`

4. ✅ `ingestion/extraction/extraction_flow.py`
   - Update various `document_processing` imports

5. ✅ `retrieval/search.py`
   - Update: `from document_processing.llm_operations import` → `from retrieval.llm_operations import`
   - Update: `from document_processing.reranker import` → `from retrieval.reranking import`

6. ✅ `api/routes/document_routes.py`
   - Update all `document_processing` imports to new paths

7. ✅ `api/app.py`
   - Update: `from document_processing.embed_chunks_to_db import` → `from ingestion.embedding import`
   - Update: `from document_processing.config import` → `from api.config import`

### **Priority 2: Other Project Files**

Files that import from the moved modules:

8. ✅ `worker/tasks.py`
   - Update: `from document_processing.full_pipeline_pgvector import` → `from api.app import`

9. ✅ `api/graph_routes.py` (if it imports document_processing)

10. ✅ Any test files in `test/`

---

## 🚀 Migration Steps

### **Automated Migration Script**

```bash
# Step 1: Update imports in ingestion modules
find ingestion -name "*.py" -type f -exec sed -i '' 's/from document_processing\./from ingestion./g' {} +
find ingestion -name "*.py" -type f -exec sed -i '' 's/from \.chunk_pdf_with_chonkie/from ingestion.chunking.semantic_chunker/g' {} +
find ingestion -name "*.py" -type f -exec sed -i '' 's/from \.processor_factory/from ingestion.processors.processor_factory/g' {} +

# Step 2: Update imports in retrieval modules
find retrieval -name "*.py" -type f -exec sed -i '' 's/from document_processing\./from retrieval./g' {} +

# Step 3: Update imports in API modules
find api -name "*.py" -type f -exec sed -i '' 's/from document_processing\.chunk_pdf_with_chonkie/from ingestion.chunking/g' {} +
find api -name "*.py" -type f -exec sed -i '' 's/from document_processing\.embed_chunks_to_db/from ingestion.embedding/g' {} +
find api -name "*.py" -type f -exec sed -i '' 's/from document_processing\.extraction_flow/from ingestion.extraction/g' {} +
find api -name "*.py" -type f -exec sed -i '' 's/from document_processing\.retrieval/from retrieval.search/g' {} +
find api -name "*.py" -type f -exec sed -i '' 's/from document_processing\.reranker/from retrieval.reranking/g' {} +
find api -name "*.py" -type f -exec sed -i '' 's/from document_processing\.llm_operations/from retrieval.llm_operations/g' {} +
find api -name "*.py" -type f -exec sed -i '' 's/from document_processing\.file_validator/from ingestion.validation/g' {} +

# Step 4: Update worker imports
sed -i '' 's/from document_processing\.full_pipeline_pgvector/from api.app/g' worker/tasks.py

# Step 5: Verify syntax
python3 -m py_compile ingestion/**/*.py retrieval/*.py api/**/*.py
```

---

## ✅ Verification Checklist

- [ ] All `ingestion/` imports updated
- [ ] All `retrieval/` imports updated
- [ ] All `api/` imports updated
- [ ] `worker/tasks.py` imports updated
- [ ] All files compile without syntax errors
- [ ] API starts successfully
- [ ] Upload endpoint works
- [ ] Query endpoint works
- [ ] Entity extraction works

---

## 🎯 Benefits Achieved

| Aspect | Before | After |
|--------|--------|-------|
| **Folder Organization** | 1 folder (19 files) | 3 folders (clean separation) |
| **Responsibilities** | Mixed | Single responsibility per folder |
| **File Finding** | Hard (search through 19 files) | Easy (organized by purpose) |
| **Testing** | Difficult (tight coupling) | Easier (isolated modules) |
| **New Developers** | Confusing | Clear structure |

---

## 📚 Related Documentation

- **Abstract Method Pattern**: [ABSTRACTION_PATTERN_SUMMARY.md](ABSTRACTION_PATTERN_SUMMARY.md)
- **Migration Summary**: [MIGRATION_COMPLETE.md](MIGRATION_COMPLETE.md)
- **Cleanup Summary**: [CLEANUP_SUMMARY.md](CLEANUP_SUMMARY.md)

---

**Status**: ✅ Files moved, __init__.py files created
**Next**: Update all imports using the migration script above

