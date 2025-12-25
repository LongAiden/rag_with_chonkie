"""
Abstract base class for document processors.
Implements the Abstract Method pattern to provide a consistent interface
for processing different document types (PDF, DOCX, TXT, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Tuple
from pathlib import Path


class DocumentProcessor(ABC):
    """
    Abstract base class for processing different document types.

    This class defines the contract that all document processors must follow:
    - extract_text(): Extract text from the document (must implement)
    - validate_file(): Validate the file before processing (must implement)
    - get_supported_extensions(): Return supported file extensions (must implement)
    - process_document(): Template method with shared workflow (already implemented)

    Template Method Pattern:
    The process_document() method defines the algorithm skeleton that all
    processors follow, while allowing subclasses to provide specific implementations
    for certain steps.
    """

    @abstractmethod
    def extract_text(self, file_path: str) -> Tuple[str, List[Tuple[int, int, int]]]:
        """
        Extract text from document (MUST IMPLEMENT).

        Args:
            file_path: Path to the document file

        Returns:
            Tuple of (full_text, page_mapping)
            where page_mapping is List[(start_pos, end_pos, page_num)]

        Raises:
            ValueError: If file cannot be processed
        """
        pass

    @abstractmethod
    def validate_file(self, file_path: str) -> bool:
        """
        Validate if the file can be processed (MUST IMPLEMENT).

        Args:
            file_path: Path to the document file

        Returns:
            True if file is valid and can be processed, False otherwise
        """
        pass

    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of supported file extensions (MUST IMPLEMENT).

        Returns:
            List of supported extensions (e.g., ['.pdf', '.PDF'])
        """
        pass

    # ===== CONCRETE METHODS (shared by all processors) =====

    def can_process(self, file_path: str) -> bool:
        """
        Check if this processor can handle the file based on extension.

        Args:
            file_path: Path to check

        Returns:
            True if this processor supports the file extension
        """
        file_ext = Path(file_path).suffix.lower()
        supported = [ext.lower() for ext in self.get_supported_extensions()]
        return file_ext in supported

    def process_document(
        self,
        file_path: str,
        chunk_size: int = 512,
        similarity_threshold: float = 0.5,
        embedding_model=None
    ) -> List:
        """
        Template Method: Process document through standard workflow.

        This method defines the algorithm skeleton:
        1. Validate file (calls child's validate_file)
        2. Extract text (calls child's extract_text)
        3. Chunk text (shared logic)
        4. Add page number metadata (shared logic)

        Args:
            file_path: Path to document
            chunk_size: Maximum tokens per chunk
            similarity_threshold: Similarity threshold for semantic chunking
            embedding_model: Custom embedding model

        Returns:
            List of chunks with page number metadata

        Raises:
            ValueError: If file is invalid or processing fails
        """
        from ingestion.chunking.semantic_chunker import chunk_with_semantic_chunker, get_page_number_for_position

        # Step 1: Validate (uses child's validation)
        if not self.validate_file(file_path):
            raise ValueError(f"Invalid file: {file_path}")

        print(f"Processing with {self.__class__.__name__}: {Path(file_path).name}")

        # Step 2: Extract text (uses child's extraction - polymorphism!)
        text, page_mapping = self.extract_text(file_path)

        print(f"Extracted {len(text)} characters from {Path(file_path).name}")

        # Step 3: Chunk the text (same for all processors)
        chunks = chunk_with_semantic_chunker(
            text,
            chunk_size,
            similarity_threshold,
            embedding_model
        )

        print(f"Created {len(chunks)} chunks")

        # Step 4: Add page number metadata (same for all processors)
        for chunk in chunks:
            if hasattr(chunk, 'start_index') and page_mapping:
                chunk.page_number = get_page_number_for_position(
                    chunk.start_index,
                    page_mapping
                )
            else:
                chunk.page_number = 1

        return chunks

    def __repr__(self) -> str:
        """String representation of the processor."""
        return f"{self.__class__.__name__}(extensions={self.get_supported_extensions()})"
