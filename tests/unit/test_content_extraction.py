"""
Unit tests for content extraction features.

Tests cover:
1. Text block extraction
2. Header detection (H1, H2)
3. Image extraction and placeholders
4. Table extraction and formatting
5. Custom extraction options
"""
from experiment.pdf_to_markdown import PDFToMarkdownConverter, ConversionOptions
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestContentExtraction:
    """Tests for content extraction features."""

    def test_extract_text_blocks(self):
        """Test extraction of text blocks."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_page = MagicMock()
        mock_page.find_tables.return_value = []
        mock_page.get_text.return_value = {
            "blocks": [
                {
                    "type": 0,  # Text block
                    "bbox": (10, 10, 100, 30),
                    "lines": [
                        {
                            "spans": [
                                {"text": "Regular text", "size": 12}
                            ]
                        }
                    ]
                }
            ]
        }

        mock_doc.__getitem__.return_value = mock_page

        converter = PDFToMarkdownConverter()
        result = converter.convert(mock_doc)

        assert "Regular text" in result

    def test_extract_headers_h1(self):
        """Test extraction and formatting of H1 headers."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

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
                                # > 18.0 threshold
                                {"text": "Large Header", "size": 20}
                            ]
                        }
                    ]
                }
            ]
        }

        mock_doc.__getitem__.return_value = mock_page

        converter = PDFToMarkdownConverter()
        result = converter.convert(mock_doc)

        assert "# Large Header" in result

    def test_extract_headers_h2(self):
        """Test extraction and formatting of H2 headers."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

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
                                # > 14.0, < 18.0
                                {"text": "Medium Header", "size": 16}
                            ]
                        }
                    ]
                }
            ]
        }

        mock_doc.__getitem__.return_value = mock_page

        converter = PDFToMarkdownConverter()
        result = converter.convert(mock_doc)

        assert "## Medium Header" in result

    def test_extract_images(self):
        """Test extraction of image blocks."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_page = MagicMock()
        mock_page.find_tables.return_value = []
        mock_page.get_text.return_value = {
            "blocks": [
                {
                    "type": 1,  # Image block
                    "bbox": (10, 10, 100, 100)
                }
            ]
        }

        mock_doc.__getitem__.return_value = mock_page

        converter = PDFToMarkdownConverter()
        result = converter.convert(mock_doc)

        assert "[IMAGE]" in result

    def test_custom_image_placeholder(self):
        """Test custom image placeholder."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_page = MagicMock()
        mock_page.find_tables.return_value = []
        mock_page.get_text.return_value = {
            "blocks": [
                {
                    "type": 1,
                    "bbox": (10, 10, 100, 100)
                }
            ]
        }

        mock_doc.__getitem__.return_value = mock_page

        options = ConversionOptions(image_placeholder="<IMG>")
        converter = PDFToMarkdownConverter()
        result = converter.convert(mock_doc, options=options)

        assert "<IMG>" in result
        assert "[IMAGE]" not in result

    def test_disable_image_extraction(self):
        """Test disabling image extraction."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_page = MagicMock()
        mock_page.find_tables.return_value = []
        mock_page.get_text.return_value = {
            "blocks": [
                {
                    "type": 1,
                    "bbox": (10, 10, 100, 100)
                }
            ]
        }

        mock_doc.__getitem__.return_value = mock_page

        options = ConversionOptions(extract_images=False)
        converter = PDFToMarkdownConverter()
        result = converter.convert(mock_doc, options=options)

        # Should not contain image placeholder
        assert "[IMAGE]" not in result

    def test_extract_tables(self):
        """Test extraction of tables."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        # Mock table
        mock_table = MagicMock()
        mock_table.bbox = (10, 10, 200, 100)

        # Mock pandas DataFrame
        import pandas as pd
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        mock_table.to_pandas.return_value = df

        mock_page = MagicMock()
        mock_page.find_tables.return_value = [mock_table]
        mock_page.get_text.return_value = {"blocks": []}

        mock_doc.__getitem__.return_value = mock_page

        converter = PDFToMarkdownConverter()
        result = converter.convert(mock_doc)

        # Should contain table wrapper tags
        assert "<table>" in result
        assert "</table>" in result

    def test_disable_table_extraction(self):
        """Test disabling table extraction."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_table = MagicMock()
        mock_table.bbox = (10, 10, 200, 100)

        mock_page = MagicMock()
        mock_page.find_tables.return_value = [mock_table]
        mock_page.get_text.return_value = {"blocks": []}

        mock_doc.__getitem__.return_value = mock_page

        options = ConversionOptions(extract_tables=False)
        converter = PDFToMarkdownConverter()
        result = converter.convert(mock_doc, options=options)

        # Should not extract tables
        assert "<table>" not in result

    def test_custom_table_wrapper_tag(self):
        """Test custom table wrapper tag."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_table = MagicMock()
        mock_table.bbox = (10, 10, 200, 100)

        import pandas as pd
        df = pd.DataFrame({"A": [1]})
        mock_table.to_pandas.return_value = df

        mock_page = MagicMock()
        mock_page.find_tables.return_value = [mock_table]
        mock_page.get_text.return_value = {"blocks": []}

        mock_doc.__getitem__.return_value = mock_page

        options = ConversionOptions(table_wrapper_tag="div")
        converter = PDFToMarkdownConverter()
        result = converter.convert(mock_doc, options=options)

        assert "<div>" in result
        assert "</div>" in result
        assert "<table>" not in result
