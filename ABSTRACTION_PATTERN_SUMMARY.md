# Abstract Method & Factory Pattern Implementation Guide

**Project**: RAG with LlamaIndex
**Date**: 2025-12-24
**Patterns Implemented**: Abstract Method Pattern + Factory Method Pattern

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [What Was Changed](#what-was-changed)
3. [Pattern Explanations](#pattern-explanations)
4. [File Structure](#file-structure)
5. [How to Use](#how-to-use)
6. [Benefits](#benefits)
7. [Adding New File Types](#adding-new-file-types)
8. [Testing](#testing)
9. [Migration Guide](#migration-guide)

---

## 🎯 Overview

This refactoring implements two design patterns to improve document processing in the RAG system:

### **Abstract Method Pattern**
- **Purpose**: Define a common interface for all document processors
- **Implementation**: `DocumentProcessor` abstract base class
- **Benefit**: All processors (PDF, DOCX, TXT) follow the same contract

### **Factory Method Pattern**
- **Purpose**: Automatically select the right processor based on file type
- **Implementation**: `ProcessorRegistry` and `get_processor_for_file()`
- **Benefit**: No IF-ELSE chains, easy to extend

---

## 📝 What Was Changed

### **Before (Old Implementation)**

```python
# chunk_pdf_with_chonkie.py - OLD WAY
def process_document(file_path):
    file_type = Path(file_path).suffix.lower()

    # IF-ELSE chain for each file type
    if file_type == 'pdf':
        text, page_mapping = extract_text_from_pdf(file_path)
    elif file_type == 'docx':
        text, page_mapping = extract_text_from_docx(file_path)
    elif file_type == 'txt':
        # inline TXT logic
        with open(file_path, 'r') as f:
            text = f.read()
    else:
        raise ValueError("Unsupported file type")

    # Common chunking logic
    chunks = chunk_with_semantic_chunker(text)
    return chunks
```

**Problems**:
- ❌ Code duplication (similar structure for each file type)
- ❌ Adding new formats requires modifying existing code
- ❌ No validation before processing
- ❌ IF-ELSE chain grows with each new format
- ❌ Hard to test uniformly

### **After (New Implementation)**

```python
# NEW WAY
def process_document_with_processor(file_path):
    # Factory automatically selects the right processor
    processor = get_processor_for_file(file_path)

    # Same call for all file types (polymorphism!)
    chunks = processor.process_document(file_path)

    return chunks
```

**Benefits**:
- ✅ No code duplication
- ✅ Adding new formats = add one new class
- ✅ Built-in validation
- ✅ No IF-ELSE chains
- ✅ Easy to test

---

## 🏗️ Pattern Explanations

### **1. Abstract Method Pattern**

#### **What It Is**
An abstract base class that defines:
- **Abstract methods**: Must be implemented by children (enforced by Python's `@abstractmethod`)
- **Concrete methods**: Shared by all children (implemented in base class)

#### **In This Project**

```python
# base_processor.py
from abc import ABC, abstractmethod

class DocumentProcessor(ABC):
    # ABSTRACT: Children MUST implement these
    @abstractmethod
    def extract_text(self, file_path):
        """Each processor implements differently"""
        pass

    @abstractmethod
    def validate_file(self, file_path):
        """Each processor validates differently"""
        pass

    # CONCRETE: Shared by all processors
    def process_document(self, file_path):
        """Template Method - same workflow for all"""
        self.validate_file(file_path)      # Uses child's validation
        text, mapping = self.extract_text(file_path)  # Uses child's extraction
        chunks = chunk_with_semantic_chunker(text)    # Same for all
        return chunks
```

#### **Why It's Useful**
- **Contract**: All processors MUST have `extract_text()` and `validate_file()`
- **Reusability**: Chunking logic written once, used by all
- **Consistency**: Same workflow for all file types

---

### **2. Factory Method Pattern**

#### **What It Is**
A pattern that creates objects without specifying their exact class. The factory decides which class to instantiate based on input.

#### **In This Project**

```python
# processor_factory.py
class ProcessorRegistry:
    def __init__(self):
        self._processors = [
            PDFProcessor(),
            DOCXProcessor(),
            TXTProcessor()
        ]

    def get_processor(self, file_path):
        """Factory Method: Returns the right processor"""
        for processor in self._processors:
            if processor.can_process(file_path):
                return processor
        raise ValueError("No processor found")

# Usage
processor = get_processor_for_file("document.pdf")  # Returns PDFProcessor
processor = get_processor_for_file("report.docx")   # Returns DOCXProcessor
processor = get_processor_for_file("notes.txt")     # Returns TXTProcessor
```

#### **Why It's Useful**
- **Automatic selection**: No manual IF-ELSE logic needed
- **Extensible**: Add new processor, factory automatically uses it
- **Centralized**: One place manages all processors

---

## 📁 File Structure

```
document_processing/
├── base_processor.py           # Abstract base class
├── pdf_processor.py            # PDF implementation
├── docx_processor.py           # DOCX implementation
├── txt_processor.py            # TXT implementation
├── processor_factory.py        # Factory and registry
└── chunk_pdf_with_chonkie.py   # Updated with new functions
```

### **File Descriptions**

| File | Purpose | Pattern |
|------|---------|---------|
| `base_processor.py` | Abstract base class defining interface | Abstract Method |
| `pdf_processor.py` | Concrete PDF implementation | Concrete Class |
| `docx_processor.py` | Concrete DOCX implementation | Concrete Class |
| `txt_processor.py` | Concrete TXT implementation | Concrete Class |
| `processor_factory.py` | Creates appropriate processor | Factory Method |
| `chunk_pdf_with_chonkie.py` | High-level API for users | Facade |

---

## 🚀 How to Use

### **Basic Usage**

```python
from document_processing.chunk_pdf_with_chonkie import process_document_with_processor

# Process any supported file type
chunks = process_document_with_processor('document.pdf', chunk_size=512)
chunks = process_document_with_processor('report.docx', chunk_size=1024)
chunks = process_document_with_processor('notes.txt')

# Access chunk data
for chunk in chunks:
    print(f"Page {chunk.page_number}: {chunk.text}")
```

### **Advanced Usage**

```python
from document_processing.processor_factory import get_processor_for_file

# Get processor manually
processor = get_processor_for_file('document.pdf')
print(f"Using: {processor}")  # Output: PDFProcessor(extensions=['.pdf', '.PDF'])

# Validate before processing
if processor.validate_file('document.pdf'):
    chunks = processor.process_document('document.pdf')
else:
    print("Invalid file!")

# List all supported file types
from document_processing.chunk_pdf_with_chonkie import get_supported_file_types
print(f"Supported: {get_supported_file_types()}")
# Output: ['.pdf', '.docx', '.txt', '.md']
```

### **Using in Your API**

```python
# api_routes.py
from fastapi import UploadFile
from document_processing.chunk_pdf_with_chonkie import process_document_with_processor

@app.post("/upload_document")
async def upload_document(file: UploadFile):
    # Save file
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Process with automatic processor selection
    try:
        chunks = process_document_with_processor(file_path, chunk_size=512)
        return {
            "status": "success",
            "chunks": len(chunks),
            "message": f"Processed {file.filename}"
        }
    except ValueError as e:
        return {"status": "error", "message": str(e)}
```

---

## 🎁 Benefits

### **1. Easy to Add New File Types**

**Before**: Modify existing code (risky!)
```python
# Had to modify process_document() function
def process_document(file_path):
    if file_type == 'pdf':
        ...
    elif file_type == 'docx':
        ...
    elif file_type == 'epub':  # NEW - risk breaking existing code
        ...
```

**After**: Just add one new class
```python
# Create new file: epub_processor.py
from .base_processor import DocumentProcessor
import ebooklib

class ePubProcessor(DocumentProcessor):
    def get_supported_extensions(self):
        return ['.epub']

    def validate_file(self, file_path):
        # ePub-specific validation
        return file_path.endswith('.epub')

    def extract_text(self, file_path):
        # ePub-specific extraction
        book = epub.read_epub(file_path)
        text = ""
        for item in book.get_items():
            text += item.get_content()
        return text, [(0, len(text), 1)]

# Register it (done automatically in factory __init__)
# No other code changes needed!
```

### **2. Better Testing**

```python
# Test all processors uniformly
def test_processor_interface():
    processors = [
        (PDFProcessor(), "test.pdf"),
        (DOCXProcessor(), "test.docx"),
        (TXTProcessor(), "test.txt"),
    ]

    for processor, test_file in processors:
        # Same test for all!
        assert processor.validate_file(test_file)
        text, mapping = processor.extract_text(test_file)
        assert len(text) > 0
        assert len(mapping) > 0
```

### **3. Polymorphism**

```python
# Treat all file types the same way
def process_batch_of_files(file_paths):
    """Process multiple files of different types"""
    all_chunks = []

    for file_path in file_paths:
        # Don't care what type it is!
        processor = get_processor_for_file(file_path)
        chunks = processor.process_document(file_path)
        all_chunks.extend(chunks)

    return all_chunks

# Works with mixed file types
files = ['doc1.pdf', 'doc2.docx', 'doc3.txt', 'doc4.md']
chunks = process_batch_of_files(files)  # All processed uniformly!
```

### **4. Validation Before Processing**

```python
from document_processing.processor_factory import get_processor_for_file

processor = get_processor_for_file('document.pdf')

# Check if file is valid before processing
if processor.validate_file('document.pdf'):
    chunks = processor.process_document('document.pdf')
else:
    print("Invalid or corrupted PDF file")
```

---

## 🆕 Adding New File Types

### **Step-by-Step Guide**

#### **Example: Adding HTML Support**

**Step 1**: Create `html_processor.py`

```python
"""HTML document processor implementation."""
from typing import List, Tuple
from pathlib import Path
from bs4 import BeautifulSoup

from .base_processor import DocumentProcessor

class HTMLProcessor(DocumentProcessor):

    def get_supported_extensions(self) -> List[str]:
        return ['.html', '.htm']

    def validate_file(self, file_path: str) -> bool:
        path = Path(file_path)
        if not path.exists():
            return False
        if path.suffix.lower() not in ['.html', '.htm']:
            return False
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(100)  # Try reading
            return True
        except:
            return False

    def extract_text(self, file_path: str) -> Tuple[str, List[Tuple[int, int, int]]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Parse HTML and extract text
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)

            # Simple page mapping (treat as one page)
            page_mapping = [(0, len(text) - 1, 1)] if text else []

            return text, page_mapping
        except Exception as e:
            raise ValueError(f"Failed to extract text from HTML {file_path}: {e}")
```

**Step 2**: Register in factory

```python
# processor_factory.py - add to __init__
from .html_processor import HTMLProcessor

class ProcessorRegistry:
    def _register_default_processors(self):
        self.register(PDFProcessor())
        self.register(DOCXProcessor())
        self.register(TXTProcessor())
        self.register(HTMLProcessor())  # <-- Add this line
```

**Step 3**: Done! 🎉

```python
# Automatically works now
chunks = process_document_with_processor('webpage.html')
```

---

## 🧪 Testing

### **Test Suite Example**

```python
# test_processors.py
import pytest
from document_processing.pdf_processor import PDFProcessor
from document_processing.docx_processor import DOCXProcessor
from document_processing.txt_processor import TXTProcessor
from document_processing.processor_factory import get_processor_for_file

class TestProcessorInterface:
    """Test that all processors follow the interface"""

    def test_pdf_processor(self):
        processor = PDFProcessor()
        assert processor.can_process('test.pdf')
        assert not processor.can_process('test.docx')
        assert '.pdf' in processor.get_supported_extensions()

    def test_docx_processor(self):
        processor = DOCXProcessor()
        assert processor.can_process('test.docx')
        assert not processor.can_process('test.pdf')
        assert '.docx' in processor.get_supported_extensions()

    def test_factory_selection(self):
        """Test factory selects correct processor"""
        pdf_proc = get_processor_for_file('document.pdf')
        assert isinstance(pdf_proc, PDFProcessor)

        docx_proc = get_processor_for_file('report.docx')
        assert isinstance(docx_proc, DOCXProcessor)

        txt_proc = get_processor_for_file('notes.txt')
        assert isinstance(txt_proc, TXTProcessor)

    def test_unsupported_file_type(self):
        """Test error for unsupported file types"""
        with pytest.raises(ValueError):
            get_processor_for_file('file.xyz')

class TestProcessing:
    """Test actual document processing"""

    @pytest.fixture
    def sample_files(self):
        return {
            'pdf': 'test_data/sample.pdf',
            'docx': 'test_data/sample.docx',
            'txt': 'test_data/sample.txt'
        }

    def test_process_all_types(self, sample_files):
        """Test processing all file types"""
        for file_type, file_path in sample_files.items():
            processor = get_processor_for_file(file_path)
            chunks = processor.process_document(file_path, chunk_size=512)

            assert len(chunks) > 0
            assert all(hasattr(chunk, 'page_number') for chunk in chunks)
```

---

## 🔄 Migration Guide

### **For Existing Code**

The old `process_document()` function still works (backward compatible):

```python
# OLD WAY - Still works!
from document_processing.chunk_pdf_with_chonkie import process_document

chunks = process_document('document.pdf')  # Works but deprecated
```

### **Migration Steps**

1. **Find all uses of `process_document()`**
   ```bash
   grep -r "process_document" --include="*.py"
   ```

2. **Replace with new function**
   ```python
   # Before
   from document_processing.chunk_pdf_with_chonkie import process_document
   chunks = process_document(file_path)

   # After
   from document_processing.chunk_pdf_with_chonkie import process_document_with_processor
   chunks = process_document_with_processor(file_path)
   ```

3. **Test thoroughly**

4. **Remove old functions** (optional, after migration complete)

---

## 📊 Comparison Table

| Aspect | Before (No Patterns) | After (With Patterns) |
|--------|---------------------|----------------------|
| **Add new file type** | Modify 2+ places | Add 1 new class |
| **Code duplication** | High (similar logic repeated) | None (shared base class) |
| **Testing** | Test each function separately | Test interface once |
| **Validation** | Inconsistent | Enforced by abstract class |
| **File type detection** | Manual IF-ELSE | Automatic (factory) |
| **Extensibility** | Low (modify existing code) | High (add new classes) |
| **Polymorphism** | No | Yes |
| **Maintainability** | Low (IF-ELSE grows) | High (isolated classes) |

---

## 🎓 Key Takeaways

### **When to Use Abstract Method Pattern**
✅ Similar operations on different data types (PDF, DOCX, TXT)
✅ Want to enforce a common interface
✅ Want to share common logic (template method)
✅ Need easy extensibility

### **When to Use Factory Method Pattern**
✅ Object creation depends on runtime conditions
✅ Want to avoid IF-ELSE chains
✅ Need centralized object management
✅ Want to support plugins/extensions

### **Benefits in This Project**
- **Before**: Adding ePub support = modify 2 files, risk breaking existing code
- **After**: Adding ePub support = create 1 new file, zero risk

---

## 📚 Further Reading

- **Abstract Method Pattern**: Template Method pattern in Gang of Four
- **Factory Method Pattern**: Factory pattern in Gang of Four
- **SOLID Principles**: Open/Closed Principle (open for extension, closed for modification)
- **Python ABC**: [Python Abstract Base Classes](https://docs.python.org/3/library/abc.html)

---

## 🤝 Contributing

To add a new document processor:

1. Create a new file: `document_processing/yourtype_processor.py`
2. Inherit from `DocumentProcessor`
3. Implement: `extract_text()`, `validate_file()`, `get_supported_extensions()`
4. Register in `processor_factory.py`
5. Add tests
6. Update this documentation

---

**Happy Coding!** 🚀

If you have questions, refer to the implementations in:
- [base_processor.py](document_processing/base_processor.py)
- [pdf_processor.py](document_processing/pdf_processor.py)
- [processor_factory.py](document_processing/processor_factory.py)
