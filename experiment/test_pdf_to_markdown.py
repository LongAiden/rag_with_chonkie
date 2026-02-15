import pytest
import fitz
from pathlib import Path
from pdf_to_markdown import PDFToMarkdownConverter, PDFConfig, MarkdownOutput
import tempfile
import os


class TestPDFToMarkdownConverter:
    """Test suite for PDFToMarkdownConverter class"""

    @pytest.fixture
    def sample_pdf_path(self):
        """Fixture to provide a sample PDF path"""
        # Using the existing PDF from the project
        pdf_path = Path("../docs/llama2.pdf")
        if not pdf_path.exists():
            pytest.skip(f"Sample PDF not found at {pdf_path}")
        return str(pdf_path.resolve())

    @pytest.fixture
    def converter_default(self, sample_pdf_path):
        """Fixture to create a converter with default config"""
        return PDFToMarkdownConverter(file_path=sample_pdf_path)

    @pytest.fixture
    def temp_output_dir(self):
        """Fixture to create a temporary output directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    # ==================== Configuration Tests ====================

    def test_config_validation_valid(self):
        """Test that valid configuration is accepted"""
        config = PDFConfig(
            header_size_threshold_h1=18,
            header_size_threshold_h2=14,
            table_intersection_threshold=0.5,
            start_page=0,
            end_page=None
        )
        assert config.header_size_threshold_h1 == 18
        assert config.header_size_threshold_h2 == 14
        assert config.table_intersection_threshold == 0.5

    def test_config_validation_invalid_thresholds(self):
        """Test that invalid thresholds are rejected"""
        with pytest.raises(ValueError):
            PDFConfig(header_size_threshold_h1=10, header_size_threshold_h2=15)

        with pytest.raises(ValueError):
            PDFConfig(table_intersection_threshold=1.5)

    def test_config_validation_invalid_page_range(self):
        """Test that invalid page ranges are rejected"""
        with pytest.raises(ValueError):
            PDFConfig(start_page=-1)

        with pytest.raises(ValueError):
            PDFConfig(start_page=10, end_page=5)

    # ==================== Initialization Tests ====================

    def test_converter_initialization_valid_path(self, sample_pdf_path):
        """Test converter initialization with valid PDF path"""
        converter = PDFToMarkdownConverter(file_path=sample_pdf_path)
        assert converter.file_path == Path(sample_pdf_path)
        assert converter.doc is not None
        assert isinstance(converter.config, PDFConfig)

    def test_converter_initialization_invalid_path(self):
        """Test converter initialization with invalid PDF path"""
        with pytest.raises(FileNotFoundError):
            PDFToMarkdownConverter(file_path="nonexistent.pdf")

    def test_converter_initialization_with_custom_config(self, sample_pdf_path):
        """Test converter initialization with custom configuration"""
        config = PDFConfig(
            header_size_threshold_h1=20,
            header_size_threshold_h2=16,
            start_page=0,
            end_page=5
        )
        converter = PDFToMarkdownConverter(
            file_path=sample_pdf_path, config=config)
        assert converter.config.header_size_threshold_h1 == 20
        assert converter.config.header_size_threshold_h2 == 16
        assert converter.config.end_page == 5

    # ==================== Process Page Tests ====================

    def test_process_page_to_markdown_returns_string(self, converter_default):
        """Test that process_page_to_markdown returns a string"""
        result = converter_default.process_page_to_markdown(page_num=0)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_process_page_to_markdown_contains_page_marker(self, converter_default):
        """Test that output contains page marker"""
        result = converter_default.process_page_to_markdown(page_num=0)
        assert "[Page 1]" in result

    def test_process_page_to_markdown_invalid_page(self, converter_default):
        """Test that invalid page number raises error"""
        total_pages = len(converter_default.doc)
        with pytest.raises(IndexError):
            converter_default.process_page_to_markdown(
                page_num=total_pages + 10)

    def test_process_page_to_markdown_negative_page(self, converter_default):
        """Test that negative page number raises error"""
        with pytest.raises(ValueError):
            converter_default.process_page_to_markdown(page_num=-1)

    def test_process_page_detects_headers(self, converter_default):
        """Test that headers are properly detected and formatted"""
        result = converter_default.process_page_to_markdown(page_num=0)
        # Should contain at least one header (# or ##)
        assert "#" in result

    def test_process_page_handles_tables(self, sample_pdf_path):
        """Test that tables are properly detected and formatted"""
        converter = PDFToMarkdownConverter(file_path=sample_pdf_path)
        # Process first few pages to find tables
        for page_num in range(min(5, len(converter.doc))):
            result = converter.process_page_to_markdown(page_num=page_num)
            if "<table>" in result:
                assert "</table>" in result or "<table>" in result.count(
                    "<table>") >= 2
                break

    def test_process_page_handles_images(self, converter_default):
        """Test that images are properly detected and formatted"""
        # Process first few pages to find images
        for page_num in range(min(10, len(converter_default.doc))):
            result = converter_default.process_page_to_markdown(
                page_num=page_num)
            if "<image>" in result:
                assert "image" in result.lower()
                break

    # ==================== Write Markdown Tests ====================

    def test_write_markdown_creates_file(self, converter_default, temp_output_dir):
        """Test that write_markdown creates output file"""
        output_path = Path(temp_output_dir) / "test_output.md"
        result = converter_default.write_markdown(
            output_path=str(output_path),
            start_page=0,
            end_page=2
        )

        assert output_path.exists()
        assert isinstance(result, MarkdownOutput)
        assert result.success is True
        assert result.output_path == output_path
        assert result.pages_processed == 2

    def test_write_markdown_content_not_empty(self, converter_default, temp_output_dir):
        """Test that written markdown file is not empty"""
        output_path = Path(temp_output_dir) / "test_output.md"
        converter_default.write_markdown(
            output_path=str(output_path),
            start_page=0,
            end_page=1
        )

        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert len(content) > 0
        assert "[Page 1]" in content

    def test_write_markdown_respects_page_range(self, converter_default, temp_output_dir):
        """Test that write_markdown respects page range"""
        output_path = Path(temp_output_dir) / "test_output.md"
        result = converter_default.write_markdown(
            output_path=str(output_path),
            start_page=1,
            end_page=3
        )

        # Pages 1 and 2 (0-indexed: pages 2 and 3)
        assert result.pages_processed == 2

        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert "[Page 2]" in content
        assert "[Page 3]" in content
        assert "[Page 1]" not in content

    def test_write_markdown_uses_config_page_range(self, sample_pdf_path, temp_output_dir):
        """Test that write_markdown uses config page range when not specified"""
        config = PDFConfig(start_page=0, end_page=2)
        converter = PDFToMarkdownConverter(
            file_path=sample_pdf_path, config=config)

        output_path = Path(temp_output_dir) / "test_output.md"
        result = converter.write_markdown(output_path=str(output_path))

        assert result.pages_processed == 2

    def test_write_markdown_invalid_output_path(self, converter_default):
        """Test that invalid output path raises error"""
        with pytest.raises(Exception):
            converter_default.write_markdown(
                output_path="/invalid/path/that/does/not/exist/output.md",
                start_page=0,
                end_page=1
            )

    def test_write_markdown_overwrites_existing_file(self, converter_default, temp_output_dir):
        """Test that write_markdown can overwrite existing files"""
        output_path = Path(temp_output_dir) / "test_output.md"

        # Write first time
        converter_default.write_markdown(
            output_path=str(output_path),
            start_page=0,
            end_page=1
        )

        # Write second time (should overwrite)
        result = converter_default.write_markdown(
            output_path=str(output_path),
            start_page=0,
            end_page=2
        )

        assert result.success is True
        assert output_path.exists()

    # ==================== Full Document Tests ====================

    def test_process_full_document(self, converter_default, temp_output_dir):
        """Test processing full document (limited to first 5 pages)"""
        output_path = Path(temp_output_dir) / "full_doc.md"
        result = converter_default.write_markdown(
            output_path=str(output_path),
            start_page=0,
            end_page=5
        )

        assert result.success is True
        assert result.pages_processed == 5
        assert output_path.exists()

        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should contain all 5 pages
        for i in range(1, 6):
            assert f"[Page {i}]" in content

    # ==================== Edge Cases ====================

    def test_empty_page_handling(self, converter_default):
        """Test handling of potentially empty pages"""
        # This should not raise an error even if page is empty
        result = converter_default.process_page_to_markdown(page_num=0)
        assert isinstance(result, str)

    def test_context_manager_support(self, sample_pdf_path):
        """Test that converter can be used as context manager"""
        with PDFToMarkdownConverter(file_path=sample_pdf_path) as converter:
            assert converter.doc is not None
            result = converter.process_page_to_markdown(page_num=0)
            assert isinstance(result, str)

        # Document should be closed after context exit
        assert converter.doc.is_closed

    def test_markdown_output_validation(self, converter_default, temp_output_dir):
        """Test that MarkdownOutput model validates correctly"""
        output_path = Path(temp_output_dir) / "test_output.md"
        result = converter_default.write_markdown(
            output_path=str(output_path),
            start_page=0,
            end_page=2
        )

        # Validate all fields
        assert isinstance(result.success, bool)
        assert isinstance(result.output_path, Path)
        assert isinstance(result.pages_processed, int)
        assert isinstance(result.total_pages, int)
        assert result.error_message is None or isinstance(
            result.error_message, str)

    def test_error_handling_in_write_markdown(self, sample_pdf_path, temp_output_dir):
        """Test error handling when processing fails"""
        converter = PDFToMarkdownConverter(file_path=sample_pdf_path)

        # Try to write with invalid page range
        output_path = Path(temp_output_dir) / "test_output.md"

        # This should handle the error gracefully
        with pytest.raises(ValueError):
            converter.write_markdown(
                output_path=str(output_path),
                start_page=1000,  # Invalid page
                end_page=1001
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
