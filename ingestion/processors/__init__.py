"""
Document processor implementations using Abstract Method pattern.
"""

from .base_processor import DocumentProcessor
from .pdf_processor import PDFProcessor
from .docx_processor import DOCXProcessor
from .txt_processor import TXTProcessor
from ingestion.processors.processor_factory import (
    ProcessorRegistry,
    get_processor_for_file,
    get_registry
)

__all__ = [
    'DocumentProcessor',
    'PDFProcessor',
    'DOCXProcessor',
    'TXTProcessor',
    'ProcessorRegistry',
    'get_processor_for_file',
    'get_registry',
]
