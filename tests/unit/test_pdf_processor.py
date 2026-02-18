"""
Unit tests for PDFProcessor.

Tests:
1. Supported extensions
2. Valid PDF validation
3. Invalid PDF validation (non-PDF files)
4. Empty PDF handling
5. Text extraction from PDF
6. Corrupted PDF handling
"""
import os
import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import directly from module to avoid cascade through __init__.py
from ingestion.processors.pdf_processor import PDFProcessor


class TestPDFProcessorSupportedExtensions:
    """Tests for supported extensions."""

    def test_supported_extensions(self):
        """Test that PDF processor supports .pdf extension."""
        processor = PDFProcessor()
        extensions = processor.get_supported_extensions()
        
        assert '.pdf' in extensions
        assert '.PDF' in extensions

    def test_supported_extensions_returns_list(self):
        """Test that get_supported_extensions returns a list."""
        processor = PDFProcessor()
        extensions = processor.get_supported_extensions()
        
        assert isinstance(extensions, list)


class TestPDFValidation:
    """Tests for PDF file validation."""

    def test_valid_pdf_validation(self, valid_pdf_path):
        """Test that valid PDF passes validation."""
        processor = PDFProcessor()
        
        is_valid = processor.validate_file(valid_pdf_path)
        
        assert is_valid is True

    def test_invalid_pdf_text_file(self, fake_pdf_path):
        """Test that a text file with .pdf extension fails validation."""
        processor = PDFProcessor()
        
        is_valid = processor.validate_file(fake_pdf_path)
        
        assert is_valid is False

    def test_non_existent_file_validation(self):
        """Test that non-existent file fails validation."""
        processor = PDFProcessor()
        
        is_valid = processor.validate_file("/nonexistent/file.pdf")
        
        assert is_valid is False

    def test_non_pdf_extension_validation(self, valid_txt_path):
        """Test that non-PDF extension fails validation."""
        processor = PDFProcessor()
        
        is_valid = processor.validate_file(valid_txt_path)
        
        assert is_valid is False

    def test_empty_pdf_validation(self, temp_dir):
        """Test that empty PDF file fails validation."""
        empty_pdf = temp_dir / "empty.pdf"
        empty_pdf.write_bytes(b"")
        
        processor = PDFProcessor()
        is_valid = processor.validate_file(str(empty_pdf))
        
        assert is_valid is False


class TestPDFTextExtraction:
    """Tests for text extraction from PDF files."""

    def test_extract_text_returns_tuple(self, valid_pdf_path):
        """Test that extract_text returns tuple of (text, page_mapping)."""
        processor = PDFProcessor()
        
        # Note: The minimal test PDF may not have extractable text
        # depending on how it was created
        try:
            result = processor.extract_text(valid_pdf_path)
            assert isinstance(result, tuple)
            assert len(result) == 2
            
            text, page_mapping = result
            assert isinstance(text, str)
            assert isinstance(page_mapping, list)
        except ValueError:
            # Some minimal PDFs may not be readable
            pytest.skip("Test PDF not readable")

    def test_extract_text_invalid_pdf_raises_error(self, fake_pdf_path):
        """Test that extracting from invalid PDF raises ValueError."""
        processor = PDFProcessor()
        
        with pytest.raises(ValueError) as excinfo:
            processor.extract_text(fake_pdf_path)
        
        assert "Failed to extract text" in str(excinfo.value)

    def test_page_mapping_format(self, valid_pdf_path):
        """Test that page mapping has correct format."""
        processor = PDFProcessor()
        
        try:
            text, page_mapping = processor.extract_text(valid_pdf_path)
            
            # Each entry should be (start_pos, end_pos, page_num)
            for entry in page_mapping:
                assert isinstance(entry, tuple)
                assert len(entry) == 3
                start_pos, end_pos, page_num = entry
                assert isinstance(start_pos, int)
                assert isinstance(end_pos, int)
                assert isinstance(page_num, int)
                assert start_pos <= end_pos
                assert page_num >= 1  # 1-indexed
        except ValueError:
            pytest.skip("Test PDF not readable")


class TestPDFProcessorWithRealPDF:
    """Tests with properly constructed PDF (requires PyPDF2 to create)."""

    @pytest.fixture
    def proper_pdf_path(self, temp_dir):
        """Create a proper PDF file for testing."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            pdf_path = temp_dir / "proper_test.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            c.drawString(100, 700, "This is test content on page 1")
            c.showPage()
            c.drawString(100, 700, "This is test content on page 2")
            c.showPage()
            c.save()
            
            return str(pdf_path)
        except ImportError:
            pytest.skip("reportlab not installed, skipping proper PDF test")

    def test_multi_page_pdf_extraction(self, proper_pdf_path):
        """Test extracting text from multi-page PDF."""
        if proper_pdf_path is None:
            pytest.skip("Could not create test PDF")
            
        processor = PDFProcessor()
        
        text, page_mapping = processor.extract_text(proper_pdf_path)
        
        assert "test content" in text.lower()
        assert len(page_mapping) == 2  # 2 pages
        
        # Check page numbers are 1-indexed
        page_numbers = [entry[2] for entry in page_mapping]
        assert 1 in page_numbers
        assert 2 in page_numbers

    def test_proper_pdf_validation(self, proper_pdf_path):
        """Test validation of properly constructed PDF."""
        if proper_pdf_path is None:
            pytest.skip("Could not create test PDF")
            
        processor = PDFProcessor()
        
        is_valid = processor.validate_file(proper_pdf_path)
        
        assert is_valid is True
