"""
Unit tests for PDFToMarkdownConverter.convert_page() method.

Tests cover:
1. Return type (string)
2. Single page conversion
3. Options handling
"""
from experiment.pdf_to_markdown import PDFToMarkdownConverter, ConversionOptions
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest


class TestConvertPageMethod:
    """Tests for the convert_page() convenience method."""

    @pytest.fixture
    def mock_fitz_doc(self):
        """Create a mock fitz.Document with 2 pages."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 2

        mock_page = MagicMock()
        mock_page.find_tables.return_value = []
        mock_page.get_text.return_value = {
            "blocks": [
                {
                    "type": 0,
                    "bbox": (10, 10, 100, 30),
                    "lines": [
                        {
                            "spans": [
                                {"text": "Single page content", "size": 12}
                            ]
                        }
                    ]
                }
            ]
        }

        mock_doc.__getitem__.return_value = mock_page

        return mock_doc

    def test_convert_page_returns_string(self, mock_fitz_doc):
        """Test that convert_page() returns a string."""
        converter = PDFToMarkdownConverter()

        result = converter.convert_page(mock_fitz_doc, page_num=0)

        assert isinstance(result, str)

    def test_convert_page_converts_single_page(self, mock_fitz_doc):
        """Test that convert_page() only converts the specified page."""
        converter = PDFToMarkdownConverter()

        result = converter.convert_page(mock_fitz_doc, page_num=0)

        assert "Single page content" in result
        # Should only have one page marker
        assert result.count("[Page") == 1

    def test_convert_page_with_options(self, mock_fitz_doc):
        """Test convert_page() with custom options."""
        options = ConversionOptions(include_page_numbers=False)
        converter = PDFToMarkdownConverter()

        result = converter.convert_page(
            mock_fitz_doc, page_num=0, options=options)

        assert isinstance(result, str)
        assert "[Page" not in result
