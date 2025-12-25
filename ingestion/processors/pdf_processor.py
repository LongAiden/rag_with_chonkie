"""
PDF document processor implementation.
Handles extraction of text and page mapping from PDF files using PyPDF2.
"""

from typing import List, Tuple
from pathlib import Path
import PyPDF2

from .base_processor import DocumentProcessor


class PDFProcessor(DocumentProcessor):
    """
    Concrete implementation for processing PDF files.

    Uses PyPDF2 library to extract text with accurate page tracking.
    """

    def get_supported_extensions(self) -> List[str]:
        """PDF files support."""
        return ['.pdf', '.PDF']

    def validate_file(self, file_path: str) -> bool:
        """
        Validate if the file is a valid PDF.

        Args:
            file_path: Path to the PDF file

        Returns:
            True if file exists, has .pdf extension, and can be opened
        """
        path = Path(file_path)

        # Check file exists
        if not path.exists():
            print(f"File does not exist: {file_path}")
            return False

        # Check extension
        if path.suffix.lower() not in ['.pdf']:
            print(f"File is not a PDF: {file_path}")
            return False

        # Try to open and validate it's a valid PDF
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                # Check if PDF has at least one page
                if len(pdf_reader.pages) == 0:
                    print(f"PDF has no pages: {file_path}")
                    return False
            return True
        except Exception as e:
            print(f"Error validating PDF {file_path}: {e}")
            return False

    def extract_text(self, file_path: str) -> Tuple[str, List[Tuple[int, int, int]]]:
        """
        Extract text from PDF file with accurate page tracking.

        Args:
            file_path: Path to the PDF file

        Returns:
            Tuple of (full_text, page_mapping)
            where page_mapping is List[(start_pos, end_pos, page_num)]

        Raises:
            ValueError: If PDF cannot be read
        """
        text = ""
        page_mapping = []

        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()

                    start_pos = len(text)
                    text += page_text + "\n"
                    end_pos = len(text) - 1  # Exclude the newline

                    # Only add mapping if page has content
                    if page_text.strip():
                        # Use 1-indexed page numbers for readability
                        page_mapping.append((start_pos, end_pos, page_num + 1))

            return text, page_mapping

        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF {file_path}: {e}")
