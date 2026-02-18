"""
Unit tests for PDFToMarkdownConverter.

Tests cover:
1. Basic conversion functionality
2. ConversionOptions configuration
3. Page selection (all pages, specific pages, ranges)
4. Output handling (return string vs write to file)
5. Source types (file path, Path object, fitz.Document)
6. Content extraction (tables, images, text)
7. Markdown formatting (headers, page numbers)
8. Edge cases and error handling
"""
from experiment.pdf_to_markdown import PDFToMarkdownConverter, ConversionOptions
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the converter


class TestConversionOptions:
    """Tests for ConversionOptions dataclass."""

    def test_default_options(self):
        """Test that ConversionOptions has sensible defaults."""
        options = ConversionOptions()

        assert options.extract_tables is True
        assert options.extract_images is True
        assert options.preserve_formatting is True
        assert options.table_overlap_threshold == 0.5
        assert options.h1_size_threshold == 18.0
        assert options.h2_size_threshold == 14.0
        assert options.include_page_numbers is True
        assert options.image_placeholder == "[IMAGE]"
        assert options.table_wrapper_tag == "table"
        assert options.custom_block_handler is None

    def test_custom_options(self):
        """Test creating ConversionOptions with custom values."""
        options = ConversionOptions(
            extract_tables=False,
            h1_size_threshold=20.0,
            image_placeholder="<IMAGE>",
            include_page_numbers=False
        )

        assert options.extract_tables is False
        assert options.h1_size_threshold == 20.0
        assert options.image_placeholder == "<IMAGE>"
        assert options.include_page_numbers is False


class TestPDFToMarkdownConverterInitialization:
    """Tests for converter initialization."""

    def test_init_without_options(self):
        """Test initializing converter without default options."""
        converter = PDFToMarkdownConverter()

        assert converter._default_options is not None
        assert isinstance(converter._default_options, ConversionOptions)
        assert converter._doc is None
        assert converter._owns_document is False

    def test_init_with_custom_options(self):
        """Test initializing converter with custom default options."""
        custom_options = ConversionOptions(extract_tables=False)
        converter = PDFToMarkdownConverter(default_options=custom_options)

        assert converter._default_options == custom_options
        assert converter._default_options.extract_tables is False


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
