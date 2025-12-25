"""
Document ingestion module.
Handles document processing, chunking, embedding, and validation.
"""

from ingestion.processors import (
    DocumentProcessor,
    PDFProcessor,
    DOCXProcessor,
    TXTProcessor,
    get_processor_for_file,
    get_registry
)
from ingestion.chunking import (
    process_document_with_processor,
    get_supported_file_types,
    list_available_processors
)

__all__ = [
    # Processors
    'DocumentProcessor',
    'PDFProcessor',
    'DOCXProcessor',
    'TXTProcessor',
    'get_processor_for_file',
    'get_registry',
    # Chunking
    'process_document_with_processor',
    'get_supported_file_types',
    'list_available_processors',
]
