"""
Unit tests for ConversionOptions dataclass.

Tests cover:
1. Default option values
2. Custom option configuration
"""
from experiment.pdf_to_markdown import ConversionOptions
import sys
from pathlib import Path


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
