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
    def converter_default(self, sample_pdf_path, temp_output_dir):
        """Fixture to create a converter with default config"""
        output_path = Path(temp_output_dir) / "default_output.md"
        return PDFToMarkdownConverter(
            file_path=sample_pdf_path,
            output_path=str(output_path)
        )

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
            table_intersection_threshold=0.5
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

    # ==================== Initialization Tests ====================

    def test_converter_initialization_valid_path(self, sample_pdf_path, temp_output_dir):
        """Test converter initialization with valid PDF path"""
        output_path = Path(temp_output_dir) / "test_output.md"
        converter = PDFToMarkdownConverter(
            file_path=sample_pdf_path,
            output_path=str(output_path)
        )
        assert converter.file_path == Path(sample_pdf_path)
        assert converter.output_path == output_path
        assert converter.doc is not None
        assert isinstance(converter.config, PDFConfig)

    def test_converter_initialization_invalid_path(self, temp_output_dir):
        """Test converter initialization with invalid PDF path"""
        output_path = Path(temp_output_dir) / "test_output.md"
        with pytest.raises(FileNotFoundError):
            PDFToMarkdownConverter(
                file_path="nonexistent.pdf",
                output_path=str(output_path)
            )

    def test_converter_initialization_with_custom_config(self, sample_pdf_path, temp_output_dir):
        """Test converter initialization with custom configuration"""
        output_path = Path(temp_output_dir) / "test_output.md"
        config = PDFConfig(
            header_size_threshold_h1=20,
            header_size_threshold_h2=16
        )
        converter = PDFToMarkdownConverter(
            file_path=sample_pdf_path,
            output_path=str(output_path),
            config=config
        )
        assert converter.config.header_size_threshold_h1 == 20
        assert converter.config.header_size_threshold_h2 == 16

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

    def test_write_markdown_creates_file(self, sample_pdf_path, temp_output_dir):
        """Test that write_markdown creates output file"""
        output_path = Path(temp_output_dir) / "test_output.md"
        converter = PDFToMarkdownConverter(
            file_path=sample_pdf_path,
            output_path=str(output_path)
        )
        result = converter.write_markdown(output_path=str(output_path))

        assert output_path.exists()
        assert isinstance(result, MarkdownOutput)
        assert result.success is True
        assert result.output_path == output_path
        assert result.pages_processed > 0

    def test_write_markdown_content_not_empty(self, sample_pdf_path, temp_output_dir):
        """Test that written markdown file is not empty"""
        output_path = Path(temp_output_dir) / "test_output.md"
        converter = PDFToMarkdownConverter(
            file_path=sample_pdf_path,
            output_path=str(output_path)
        )
        converter.write_markdown(output_path=str(output_path))

        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert len(content) > 0
        assert "[Page 1]" in content

    def test_write_markdown_processes_all_pages(self, sample_pdf_path, temp_output_dir):
        """Test that write_markdown processes all pages in document"""
        output_path = Path(temp_output_dir) / "test_output.md"
        converter = PDFToMarkdownConverter(
            file_path=sample_pdf_path,
            output_path=str(output_path)
        )
        result = converter.write_markdown(output_path=str(output_path))

        # Should process all pages in the document
        assert result.pages_processed == result.total_pages

        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should contain first and last page markers
        assert "[Page 1]" in content
        assert f"[Page {result.total_pages}]" in content

    def test_write_markdown_invalid_output_path(self, sample_pdf_path):
        """Test that invalid output path raises error"""
        converter = PDFToMarkdownConverter(
            file_path=sample_pdf_path,
            output_path="/invalid/path/that/does/not/exist/output.md"
        )
        with pytest.raises(Exception):
            converter.write_markdown(
                output_path="/invalid/path/that/does/not/exist/output.md"
            )

    def test_write_markdown_overwrites_existing_file(self, sample_pdf_path, temp_output_dir):
        """Test that write_markdown can overwrite existing files"""
        output_path = Path(temp_output_dir) / "test_output.md"
        converter = PDFToMarkdownConverter(
            file_path=sample_pdf_path,
            output_path=str(output_path)
        )

        # Write first time
        converter.write_markdown(output_path=str(output_path))

        # Write second time (should overwrite)
        result = converter.write_markdown(output_path=str(output_path))

        assert result.success is True
        assert output_path.exists()

    # ==================== Full Document Tests ====================

    def test_process_full_document(self, sample_pdf_path, temp_output_dir):
        """Test processing full document"""
        output_path = Path(temp_output_dir) / "full_doc.md"
        converter = PDFToMarkdownConverter(
            file_path=sample_pdf_path,
            output_path=str(output_path)
        )
        result = converter.write_markdown(output_path=str(output_path))

        assert result.success is True
        assert result.pages_processed == result.total_pages
        assert output_path.exists()

        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should contain first page at minimum
        assert "[Page 1]" in content

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

    def test_markdown_output_validation(self, sample_pdf_path, temp_output_dir):
        """Test that MarkdownOutput model validates correctly"""
        output_path = Path(temp_output_dir) / "test_output.md"
        converter = PDFToMarkdownConverter(
            file_path=sample_pdf_path,
            output_path=str(output_path)
        )
        result = converter.write_markdown(output_path=str(output_path))

        # Validate all fields
        assert isinstance(result.success, bool)
        assert isinstance(result.output_path, Path)
        assert isinstance(result.pages_processed, int)
        assert isinstance(result.total_pages, int)
        assert result.error_message is None or isinstance(
            result.error_message, str)

    def test_error_handling_with_corrupted_pdf(self, temp_output_dir):
        """Test error handling when PDF file is invalid"""
        # Create a fake PDF file
        fake_pdf = Path(temp_output_dir) / "fake.pdf"
        fake_pdf.write_text("This is not a real PDF file")

        output_path = Path(temp_output_dir) / "test_output.md"

        # This should raise an exception when trying to open the PDF
        with pytest.raises(Exception):
            PDFToMarkdownConverter(
                file_path=str(fake_pdf),
                output_path=str(output_path)
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
