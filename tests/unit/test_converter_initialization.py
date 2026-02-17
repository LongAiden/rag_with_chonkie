"""
Unit tests for PDFToMarkdownConverter initialization.

Tests cover:
1. Initialization without options
2. Initialization with custom default options
"""
from experiment.pdf_to_markdown import PDFToMarkdownConverter, ConversionOptions
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


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
