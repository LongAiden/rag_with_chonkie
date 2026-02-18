"""
Unit tests for PDFToMarkdownConverter.convert() method.

Tests cover:
1. Return type (string)
2. Source types (file path, Path object, fitz.Document)
3. Page selection (all pages, specific pages, ranges)
4. Output handling (return string vs write to file)
5. Options handling (default, custom, page numbers)
6. Resource cleanup
"""
from experiment.pdf_to_markdown import PDFToMarkdownConverter, ConversionOptions
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestConvertMethod:
    """Tests for the main convert() method."""

    @pytest.fixture
    def mock_fitz_doc(self):
        """Create a mock fitz.Document."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 2  # 2 pages

        # Mock page 0
        mock_page_0 = MagicMock()
        mock_page_0.find_tables.return_value = []
        mock_page_0.get_text.return_value = {
            "blocks": [
                {
                    "type": 0,
                    "bbox": (10, 10, 100, 30),
                    "lines": [
                        {
                            "spans": [
                                {"text": "Test content page 1", "size": 12}
                            ]
                        }
                    ]
                }
            ]
        }

        # Mock page 1
        mock_page_1 = MagicMock()
        mock_page_1.find_tables.return_value = []
        mock_page_1.get_text.return_value = {
            "blocks": [
                {
                    "type": 0,
                    "bbox": (10, 10, 100, 30),
                    "lines": [
                        {
                            "spans": [
                                {"text": "Test content page 2", "size": 12}
                            ]
                        }
                    ]
                }
            ]
        }

        mock_doc.__getitem__.side_effect = [mock_page_0, mock_page_1]

        return mock_doc

    def test_convert_returns_string(self, mock_fitz_doc, tmp_path):
        """Test that convert() returns a string."""
        with patch('experiment.pdf_to_markdown.fitz.open', return_value=mock_fitz_doc):
            converter = PDFToMarkdownConverter()
            pdf_path = tmp_path / "test.pdf"
            pdf_path.write_text("dummy")

            result = converter.convert(str(pdf_path))

            assert isinstance(result, str)

    def test_convert_with_path_object(self, mock_fitz_doc, tmp_path):
        """Test convert() accepts Path object as source."""
        with patch('experiment.pdf_to_markdown.fitz.open', return_value=mock_fitz_doc):
            converter = PDFToMarkdownConverter()
            pdf_path = tmp_path / "test.pdf"
            pdf_path.write_text("dummy")

            result = converter.convert(pdf_path)

            assert isinstance(result, str)

    def test_convert_with_fitz_document(self, mock_fitz_doc):
        """Test convert() accepts fitz.Document as source."""
        converter = PDFToMarkdownConverter()

        result = converter.convert(mock_fitz_doc)

        assert isinstance(result, str)
        # Should not close document we don't own
        mock_fitz_doc.close.assert_not_called()

    def test_convert_all_pages_by_default(self, mock_fitz_doc):
        """Test that convert() processes all pages when pages=None."""
        converter = PDFToMarkdownConverter()

        result = converter.convert(mock_fitz_doc)

        # Should contain content from both pages
        assert "Test content page 1" in result
        assert "Test content page 2" in result

    def test_convert_specific_pages_list(self, mock_fitz_doc):
        """Test convert() with specific page list."""
        converter = PDFToMarkdownConverter()

        # Only convert page 0
        result = converter.convert(mock_fitz_doc, pages=[0])

        assert "Test content page 1" in result
        assert "Test content page 2" not in result

    def test_convert_page_range(self, mock_fitz_doc):
        """Test convert() with page range."""
        converter = PDFToMarkdownConverter()

        result = converter.convert(mock_fitz_doc, pages=range(0, 1))

        assert "Test content page 1" in result
        assert "Test content page 2" not in result

    def test_convert_includes_page_numbers_by_default(self, mock_fitz_doc):
        """Test that page numbers are included by default."""
        converter = PDFToMarkdownConverter()

        result = converter.convert(mock_fitz_doc)

        assert "[Page 1]" in result
        assert "[Page 2]" in result

    def test_convert_without_page_numbers(self, mock_fitz_doc):
        """Test convert() with page numbers disabled."""
        options = ConversionOptions(include_page_numbers=False)
        converter = PDFToMarkdownConverter()

        result = converter.convert(mock_fitz_doc, options=options)

        assert "[Page 1]" not in result
        assert "[Page 2]" not in result

    def test_convert_writes_to_file(self, mock_fitz_doc, tmp_path):
        """Test convert() writes to file when output path is provided."""
        converter = PDFToMarkdownConverter()
        output_path = tmp_path / "output.md"

        result = converter.convert(mock_fitz_doc, output=output_path)

        # Should still return the markdown
        assert isinstance(result, str)
        # File should exist
        assert output_path.exists()
        # File should contain the markdown
        assert output_path.read_text(encoding="utf-8") == result

    def test_convert_with_custom_options(self, mock_fitz_doc):
        """Test convert() with custom ConversionOptions."""
        options = ConversionOptions(
            include_page_numbers=False,
            extract_tables=False
        )
        converter = PDFToMarkdownConverter()

        result = converter.convert(mock_fitz_doc, options=options)

        assert isinstance(result, str)

    def test_convert_uses_default_options(self, mock_fitz_doc):
        """Test that convert() uses default options when none provided."""
        default_options = ConversionOptions(include_page_numbers=False)
        converter = PDFToMarkdownConverter(default_options=default_options)

        result = converter.convert(mock_fitz_doc)

        # Should use default options (no page numbers)
        assert "[Page 1]" not in result

    def test_convert_cleans_up_owned_document(self, tmp_path):
        """Test that convert() closes documents it opens."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_page = MagicMock()
        mock_page.find_tables.return_value = []
        mock_page.get_text.return_value = {"blocks": []}
        mock_doc.__getitem__.return_value = mock_page

        with patch('experiment.pdf_to_markdown.fitz.open', return_value=mock_doc):
            converter = PDFToMarkdownConverter()
            pdf_path = tmp_path / "test.pdf"
            pdf_path.write_text("dummy")

            converter.convert(str(pdf_path))

            # Should close the document
            mock_doc.close.assert_called_once()

    def test_output_path_as_string(self, mock_fitz_doc, tmp_path):
        """Test output parameter as string."""
        converter = PDFToMarkdownConverter()
        output_path = str(tmp_path / "output.md")

        result = converter.convert(mock_fitz_doc, output=output_path)

        assert Path(output_path).exists()

    def test_output_path_as_path_object(self, mock_fitz_doc, tmp_path):
        """Test output parameter as Path object."""
        converter = PDFToMarkdownConverter()
        output_path = tmp_path / "output.md"

        result = converter.convert(mock_fitz_doc, output=output_path)

        assert output_path.exists()
