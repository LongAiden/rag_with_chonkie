"""
PDF to Markdown Converter

This module provides a class-based interface for converting PDF documents to Markdown format
with support for headers, tables, and images. Uses PyMuPDF (fitz) for PDF processing and
Pydantic for data validation.
"""

import fitz  # PyMuPDF
import pandas as pd
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class PDFConfig(BaseModel):
    """Configuration for PDF to Markdown conversion"""

    header_size_threshold_h1: float = Field(
        default=18,
        description="Font size threshold for H1 headers",
        gt=0
    )
    header_size_threshold_h2: float = Field(
        default=14,
        description="Font size threshold for H2 headers",
        gt=0
    )
    table_intersection_threshold: float = Field(
        default=0.5,
        description="Threshold for determining if text is inside a table (0-1)",
        ge=0,
        le=1
    )

    @field_validator('header_size_threshold_h2')
    @classmethod
    def validate_h2_smaller_than_h1(cls, v, info):
        """Ensure H2 threshold is smaller than H1 threshold"""
        if 'header_size_threshold_h1' in info.data:
            h1_threshold = info.data['header_size_threshold_h1']
            if v >= h1_threshold:
                raise ValueError(
                    f"header_size_threshold_h2 ({v}) must be less than "
                    f"header_size_threshold_h1 ({h1_threshold})"
                )
        return v


class MarkdownOutput(BaseModel):
    """Output model for markdown conversion results"""

    success: bool = Field(description="Whether the conversion was successful")
    output_path: Path = Field(description="Path to the output markdown file")
    pages_processed: int = Field(description="Number of pages processed", ge=0)
    total_pages: int = Field(description="Total pages in the document", ge=0)
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if conversion failed"
    )


class PDFToMarkdownConverter:
    """
    Convert PDF documents to Markdown format with support for headers, tables, and images.

    Example:
        >>> converter = PDFToMarkdownConverter("document.pdf")
        >>> result = converter.write_markdown("output.md", start_page=0, end_page=10)
        >>> print(f"Processed {result.pages_processed} pages")

    Or use as context manager:
        >>> with PDFToMarkdownConverter("document.pdf") as converter:
        ...     result = converter.write_markdown("output.md")
    """

    def __init__(self, file_path: str, output_path: str, config: Optional[PDFConfig] = None):
        """
        Initialize the PDF to Markdown converter.

        Args:
            file_path: Path to the PDF file
            config: Optional configuration for conversion. If None, uses defaults.

        Raises:
            FileNotFoundError: If the PDF file doesn't exist
            Exception: If the PDF file cannot be opened
        """
        self.file_path = Path(file_path)
        self.output_path = Path(output_path)

        if not self.file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        self.config = config or PDFConfig()

        try:
            self.doc = fitz.open(str(self.file_path))
        except Exception as e:
            raise Exception(f"Failed to open PDF file: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close the document"""
        if self.doc and not self.doc.is_closed:
            self.doc.close()
        return False

    def process_page_to_markdown(self, page_num: int) -> str:
        """
        TBD 
        """
        # 5. SORT AND COMPILE
        # -------------------
        # Sort items by vertical position (y0), then horizontal (x0)
        items.sort(key=lambda x: (x["y0"], x["x0"]))

        # Build final string
        markdown_output = f"[Page {page_num + 1}]\n\n"
        for item in items:
            markdown_output += item["content"] + "\n\n"

        return markdown_output

    def write_markdown(
        self,
        output_path: str,
    ) -> MarkdownOutput:
        """
        Process PDF pages and write markdown to a file.

        Args:
            output_path: Path where the markdown file will be written
            start_page: Starting page number (0-indexed). If None, uses config value.
            end_page: Ending page number (0-indexed, exclusive). If None, uses config value
                     or processes all pages.

        Returns:
            MarkdownOutput model with conversion results

        Raises:
            ValueError: If page range is invalid
            Exception: If writing to file fails
        """
        output_file = Path(output_path)
        page_nums = self.doc.page_count

        try:
            full_markdown = ""
            pages_processed = 0

            for page_num in range(0, page_nums+1):
                try:
                    # Add a separator between pages
                    page_markdown = self.process_page_to_markdown(page_num)
                    full_markdown += page_markdown + "\n\n---\n\n"
                    pages_processed += 1

                except Exception as e:
                    # Log error but continue processing
                    error_msg = f"Error processing page {page_num}: {e}"
                    full_markdown += f"\n\n[ERROR: {error_msg}]\n\n"

            # Write to file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(full_markdown)

            return MarkdownOutput(
                success=True,
                output_path=output_file,
                pages_processed=pages_processed,
                total_pages=len(self.doc),
                error_message=None
            )

        except Exception as e:
            return MarkdownOutput(
                success=False,
                output_path=output_file,
                pages_processed=pages_processed if 'pages_processed' in locals() else 0,
                total_pages=len(self.doc),
                error_message=str(e)
            )

    def close(self):
        """Close the PDF document"""
        if self.doc and not self.doc.is_closed:
            self.doc.close()

    def __del__(self):
        """Destructor to ensure document is closed"""
        self.close()


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python pdf_to_markdown.py <pdf_file> [output_file]")
        sys.exit(1)

    pdf_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "output_markdown.md"
    start_page = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    end_page = int(sys.argv[4]) if len(sys.argv) > 4 else None

    # Create converter with custom config
    config = PDFConfig(
        header_size_threshold_h1=18,
        header_size_threshold_h2=14
    )

    with PDFToMarkdownConverter(pdf_file, output=output_file, config=config) as converter:
        print(f"Processing PDF: {pdf_file}")
        print(f"Total pages: {len(converter.doc)}")

        result = converter.write_markdown(output_file)

        if result.success:
            print(f"✓ Successfully processed {result.pages_processed} pages")
            print(f"✓ Output written to: {result.output_path}")
        else:
            print(f"✗ Conversion failed: {result.error_message}")
            sys.exit(1)
