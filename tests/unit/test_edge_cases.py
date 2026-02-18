"""
Unit tests for edge cases and error handling.

Tests cover:
1. Empty PDFs
2. Empty text blocks
3. Formatting options
4. Output path handling
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


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_pdf(self):
        """Test converting PDF with no content."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_page = MagicMock()
        mock_page.find_tables.return_value = []
        mock_page.get_text.return_value = {"blocks": []}

        mock_doc.__getitem__.return_value = mock_page

        converter = PDFToMarkdownConverter()
        result = converter.convert(mock_doc)

        # Should return string (possibly empty or with page markers)
        assert isinstance(result, str)

    def test_empty_text_blocks_ignored(self):
        """Test that empty text blocks are ignored."""
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
                                {"text": "   ", "size": 12}  # Only whitespace
                            ]
                        }
                    ]
                }
            ]
        }

        mock_doc.__getitem__.return_value = mock_page

        converter = PDFToMarkdownConverter()
        result = converter.convert(mock_doc)

        # Should not contain the empty block
        assert "   " not in result.replace("[Page 1]", "").strip()

    def test_no_formatting_mode(self):
        """Test with preserve_formatting=False."""
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
                                {"text": "Large Text", "size": 20}
                            ]
                        }
                    ]
                }
            ]
        }

        mock_doc.__getitem__.return_value = mock_page

        options = ConversionOptions(preserve_formatting=False)
        converter = PDFToMarkdownConverter()
        result = converter.convert(mock_doc, options=options)

        # Should not have header formatting
        assert "# Large Text" not in result
        assert "Large Text" in result

    def test_output_path_as_string(self, tmp_path):
        """Test output parameter as string."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_page = MagicMock()
        mock_page.find_tables.return_value = []
        mock_page.get_text.return_value = {"blocks": []}

        mock_doc.__getitem__.return_value = mock_page

        converter = PDFToMarkdownConverter()
        output_path = str(tmp_path / "output.md")

        result = converter.convert(mock_doc, output=output_path)

        assert Path(output_path).exists()

    def test_output_path_as_path_object(self, tmp_path):
        """Test output parameter as Path object."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_page = MagicMock()
        mock_page.find_tables.return_value = []
        mock_page.get_text.return_value = {"blocks": []}

        mock_doc.__getitem__.return_value = mock_page

        converter = PDFToMarkdownConverter()
        output_path = tmp_path / "output.md"

        result = converter.convert(mock_doc, output=output_path)

        assert output_path.exists()
