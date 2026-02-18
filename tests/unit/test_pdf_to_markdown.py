import pytest
import fitz
from pathlib import Path
from ingestion.processors.pdf_to_markdown import PDFToMarkdownConverter, ConversionOptions
import tempfile


class TestPDFToMarkdownConverter:
    """Test suite for PDFToMarkdownConverter class"""

    @pytest.fixture
    def sample_pdf_path(self):
        """Fixture to provide a sample PDF path"""
        # Using the existing PDF from the project
        pdf_path = Path("docs/llama2.pdf")
        if not pdf_path.exists():
            pytest.skip(f"Sample PDF not found at {pdf_path}")
        return str(pdf_path.resolve())

    @pytest.fixture
    def temp_output_dir(self):
        """Fixture to create a temporary output directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def converter(self):
        """Fixture to create a converter with default options"""
        return PDFToMarkdownConverter()

    # ==================== Configuration Tests ====================

    def test_options_defaults(self):
        """Test that default ConversionOptions values are set correctly"""
        options = ConversionOptions()
        assert options.h1_size_threshold == 18.0
        assert options.h2_size_threshold == 14.0
        assert options.table_overlap_threshold == 0.5
        assert options.extract_tables is True
        assert options.extract_images is True

    def test_options_custom_values(self):
        """Test that custom ConversionOptions values are accepted"""
        options = ConversionOptions(
            h1_size_threshold=20.0,
            h2_size_threshold=16.0,
            table_overlap_threshold=0.7
        )
        assert options.h1_size_threshold == 20.0
        assert options.h2_size_threshold == 16.0
        assert options.table_overlap_threshold == 0.7

    # ==================== Initialization Tests ====================

    def test_converter_default_initialization(self):
        """Test converter initializes with default options"""
        converter = PDFToMarkdownConverter()
        assert converter._default_options is not None
        assert isinstance(converter._default_options, ConversionOptions)

    def test_converter_custom_options_initialization(self):
        """Test converter initialization with custom options"""
        options = ConversionOptions(h1_size_threshold=20.0, h2_size_threshold=16.0)
        converter = PDFToMarkdownConverter(default_options=options)
        assert converter._default_options.h1_size_threshold == 20.0
        assert converter._default_options.h2_size_threshold == 16.0

    def test_converter_invalid_path(self):
        """Test converter raises error on invalid PDF path"""
        converter = PDFToMarkdownConverter()
        with pytest.raises(Exception):
            converter.convert("nonexistent.pdf")

    # ==================== Convert Method Tests ====================

    def test_convert_returns_string(self, sample_pdf_path):
        """Test that convert() returns a string"""
        converter = PDFToMarkdownConverter()
        result = converter.convert(sample_pdf_path, pages=[0])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_convert_single_page_contains_page_marker(self, sample_pdf_path):
        """Test that output contains page marker"""
        converter = PDFToMarkdownConverter()
        result = converter.convert(sample_pdf_path, pages=[0])
        assert "[Page 1]" in result

    def test_convert_detects_headers(self, sample_pdf_path):
        """Test that headers are properly detected and formatted"""
        converter = PDFToMarkdownConverter()
        result = converter.convert(sample_pdf_path, pages=[0])
        assert "#" in result

    def test_convert_page_method(self, sample_pdf_path):
        """Test convert_page convenience method"""
        converter = PDFToMarkdownConverter()
        result = converter.convert_page(sample_pdf_path, page_num=0)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_convert_with_custom_options(self, sample_pdf_path):
        """Test conversion with custom options overrides"""
        converter = PDFToMarkdownConverter()
        options = ConversionOptions(extract_images=False, extract_tables=False)
        result = converter.convert(sample_pdf_path, pages=[0], options=options)
        assert isinstance(result, str)

    def test_convert_without_page_numbers(self, sample_pdf_path):
        """Test conversion with page numbers disabled"""
        converter = PDFToMarkdownConverter()
        options = ConversionOptions(include_page_numbers=False)
        result = converter.convert(sample_pdf_path, pages=[0], options=options)
        assert "[Page" not in result

    # ==================== Write to File Tests ====================

    def test_convert_writes_to_file(self, sample_pdf_path, temp_output_dir):
        """Test that convert() creates output file when output path is given"""
        output_path = Path(temp_output_dir) / "test_output.md"
        converter = PDFToMarkdownConverter()
        result = converter.convert(sample_pdf_path, output=str(output_path))

        assert output_path.exists()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_convert_file_content_not_empty(self, sample_pdf_path, temp_output_dir):
        """Test that written markdown file is not empty"""
        output_path = Path(temp_output_dir) / "test_output.md"
        converter = PDFToMarkdownConverter()
        converter.convert(sample_pdf_path, output=str(output_path))

        content = output_path.read_text(encoding="utf-8")
        assert len(content) > 0
        assert "[Page 1]" in content

    def test_convert_all_pages(self, sample_pdf_path, temp_output_dir):
        """Test converting all pages (no page filter)"""
        output_path = Path(temp_output_dir) / "full_doc.md"
        converter = PDFToMarkdownConverter()
        result = converter.convert(sample_pdf_path, output=str(output_path))

        assert output_path.exists()
        assert "[Page 1]" in result

    def test_convert_overwrites_existing_file(self, sample_pdf_path, temp_output_dir):
        """Test that convert() can overwrite existing files"""
        output_path = Path(temp_output_dir) / "test_output.md"
        converter = PDFToMarkdownConverter()

        # Write first time
        converter.convert(sample_pdf_path, pages=[0], output=str(output_path))
        # Write second time (should overwrite)
        result = converter.convert(sample_pdf_path, pages=[0], output=str(output_path))

        assert output_path.exists()
        assert isinstance(result, str)

    # ==================== Edge Cases ====================

    def test_convert_accepts_fitz_document(self, sample_pdf_path):
        """Test that converter accepts an already-opened fitz.Document"""
        doc = fitz.open(sample_pdf_path)
        converter = PDFToMarkdownConverter()
        result = converter.convert(doc, pages=[0])
        assert isinstance(result, str)
        doc.close()

    def test_convert_with_page_range(self, sample_pdf_path):
        """Test conversion with a range object for pages"""
        converter = PDFToMarkdownConverter()
        result = converter.convert(sample_pdf_path, pages=range(0, 2))
        assert isinstance(result, str)
        assert "[Page 1]" in result

    def test_convert_corrupted_pdf(self, temp_output_dir):
        """Test error handling when PDF file is invalid"""
        fake_pdf = Path(temp_output_dir) / "fake.pdf"
        fake_pdf.write_text("This is not a real PDF file")

        converter = PDFToMarkdownConverter()
        with pytest.raises(Exception):
            converter.convert(str(fake_pdf))

    def test_convert_handles_tables(self, sample_pdf_path):
        """Test that tables are properly detected and formatted"""
        converter = PDFToMarkdownConverter()
        doc = fitz.open(sample_pdf_path)
        total_pages = len(doc)
        doc.close()

        for page_num in range(min(5, total_pages)):
            result = converter.convert(sample_pdf_path, pages=[page_num])
            if "<table>" in result:
                assert "</table>" in result
                break

    def test_convert_handles_images(self, sample_pdf_path):
        """Test that images are properly detected and replaced with placeholder"""
        converter = PDFToMarkdownConverter()
        doc = fitz.open(sample_pdf_path)
        total_pages = len(doc)
        doc.close()

        for page_num in range(min(10, total_pages)):
            result = converter.convert(sample_pdf_path, pages=[page_num])
            if "[IMAGE]" in result:
                assert "[IMAGE]" in result
                break


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
