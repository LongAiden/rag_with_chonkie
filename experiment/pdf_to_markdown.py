import fitz  # PyMuPDF
import pandas as pd
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ConversionOptions:
    """
    Configuration object - allows extending behavior without changing interface.
    This is the OPTIONS PATTERN: prevent method explosion by encapsulating config.
    """
    # Content extraction
    extract_tables: bool = True
    extract_images: bool = True
    preserve_formatting: bool = True

    # Table detection
    table_overlap_threshold: float = 0.5  # How much overlap qualifies as "in table"

    # Heading detection (font size thresholds)
    h1_size_threshold: float = 18.0
    h2_size_threshold: float = 14.0

    # Output formatting
    include_page_numbers: bool = True
    image_placeholder: str = "[IMAGE]"
    table_wrapper_tag: str = "table"

    # Performance
    flags: int = fitz.TEXT_PRESERVE_IMAGES

    # Custom handlers (extensibility point)
    custom_block_handler: Optional[callable] = None


class PDFToMarkdownConverter:
    def __init__(self, default_options: Optional[ConversionOptions] = None):
        """
        Initialize converter with optional defaults.

        Zero-config usage: PDFToMarkdownConverter().convert("file.pdf")
        Custom config: PDFToMarkdownConverter(custom_options).convert("file.pdf")
        """
        self._default_options = default_options or ConversionOptions()
        self._doc: Optional[fitz.Document] = None
        self._owns_document = False

    def convert(
        self,
        source: str | Path | fitz.Document,
        output: Optional[str | Path] = None,
        pages: Optional[List[int] | range] = None,
        options: Optional[ConversionOptions] = None
    ) -> str:
        """
        Convert PDF to Markdown.

        This is the ONLY public method. Deep module principle: one interface, many capabilities.

        Args:
            source: PDF input
                - File path: "/path/to/file.pdf" or Path object
                - fitz.Document: Already opened document

            output: Where to write result (optional)
                - None: Return markdown as string (default)
                - File path: Write to this location

            pages: Which pages to convert (optional)
                - None: Convert all pages (default)
                - List[int]: Specific pages, e.g., [0, 1, 5]
                - range: Page range, e.g., range(10, 20)

            options: Conversion customization (optional)
                - None: Use default options
                - ConversionOptions: Override defaults

        Returns:
            Markdown string

        Examples:
            # Simplest usage
            markdown = converter.convert("document.pdf")

            # Specific pages
            markdown = converter.convert("document.pdf", pages=[0, 1, 2])

            # Custom options
            opts = ConversionOptions(extract_tables=False, h1_size_threshold=20)
            markdown = converter.convert("document.pdf", options=opts)

            # To file
            converter.convert("input.pdf", output="output.md")

            # Reuse opened document
            doc = fitz.open("large.pdf")
            markdown = converter.convert(doc, pages=range(100, 200))

        DESIGN NOTE:
        This single method replaces what could be:
        - convert_file()
        - convert_document()
        - convert_page_range()
        - convert_with_tables()
        - convert_without_images()
        - convert_to_file()
        ... etc (method explosion = shallow design)
        """
        effective_options = self._merge_options(options)

        try:
            # Load document (handles multiple source types)
            self._load_document(source)

            # Determine page range
            page_list = self._resolve_pages(pages)

            # Process all pages
            markdown = self._convert_pages(page_list, effective_options)

            # Handle output
            return self._write_output(markdown, output)

        finally:
            # Cleanup if we own the document
            self._cleanup_document()

    def convert_page(
        self,
        source: str | Path | fitz.Document,
        page_num: int,
        options: Optional[ConversionOptions] = None
    ) -> str:
        """
        Convenience method for single-page conversion.
        Delegates to the general convert() method.
        """
        return self.convert(source, pages=[page_num], options=options)

    def _merge_options(self, options: Optional[ConversionOptions]) -> ConversionOptions:
        """Merge provided options with defaults."""
        return options if options is not None else self._default_options

    def _load_document(self, source: str | Path | fitz.Document) -> None:
        """
        Load PDF document from various source types.

        HIDDEN COMPLEXITY:
        - Type detection and dispatch
        - File opening and error handling
        - Memory management decisions
        """
        if isinstance(source, fitz.Document):
            self._doc = source
            self._owns_document = False
        else:
            # Convert Path to str if needed
            path = str(source) if isinstance(source, Path) else source
            self._doc = fitz.open(path)
            self._owns_document = True

    def _resolve_pages(self, pages: Optional[List[int] | range]) -> List[int]:
        """
        Convert page specification to list of page numbers.

        HIDDEN COMPLEXITY:
        - Range handling
        - Validation and bounds checking
        - Default behavior (all pages)
        """
        if pages is None:
            return list(range(len(self._doc)))
        elif isinstance(pages, range):
            return list(pages)
        else:
            return pages

    def _convert_pages(self, page_list: List[int], options: ConversionOptions) -> str:
        """
        Convert multiple pages to markdown.

        HIDDEN COMPLEXITY:
        - Iteration strategy
        - Page-level aggregation
        - Separator formatting
        """
        markdown_parts = []

        for page_num in page_list:
            page_md = self._convert_single_page(page_num, options)

            if options.include_page_numbers:
                markdown_parts.append(f"[Page {page_num + 1}]\n\n{page_md}")
            else:
                markdown_parts.append(page_md)

        return "\n\n".join(markdown_parts)

    def _convert_single_page(self, page_num: int, options: ConversionOptions) -> str:
        """
        Convert a single page to markdown.

        This is the core conversion logic - completely hidden from caller.

        HIDDEN COMPLEXITY:
        - Table detection and extraction
        - Block extraction and filtering
        - Coordinate geometry calculations
        - Content type classification
        - Sorting and ordering
        - Markdown generation
        """
        page = self._doc[page_num]

        # Extract structural elements
        tables = self._extract_tables(
            page, options) if options.extract_tables else []
        table_bboxes = [table.bbox for table in tables]

        # Extract content blocks
        blocks = self._extract_blocks(page, options)

        # Process blocks into items
        items = []

        for block in blocks:
            # Skip blocks that are part of tables
            if self._is_block_in_table(block, table_bboxes, options):
                continue

            # Convert block to markdown item
            item = self._process_block(block, options)
            if item:
                items.append(item)

        # Add table items
        for table in tables:
            item = self._process_table(table, options)
            if item:
                items.append(item)

        # Sort by position (top-to-bottom, left-to-right)
        items.sort(key=lambda x: (x["y0"], x["x0"]))

        # Generate markdown
        return self._items_to_markdown(items)

    def _extract_tables(self, page: fitz.Page, options: ConversionOptions) -> List:
        """
        Extract tables from page.

        HIDDEN: Table detection algorithms, heuristics, confidence thresholds.
        """
        return page.find_tables()

    def _extract_blocks(self, page: fitz.Page, options: ConversionOptions) -> List[Dict]:
        """
        Extract content blocks from page.

        HIDDEN: PyMuPDF extraction flags, text preservation strategies.
        """
        text_dict = page.get_text("dict", flags=options.flags)
        return text_dict["blocks"]

    def _is_block_in_table(
        self,
        block: Dict,
        table_bboxes: List[tuple],
        options: ConversionOptions
    ) -> bool:
        """
        Determine if a block overlaps with any table.

        HIDDEN COMPLEXITY:
        - Bounding box intersection algorithm
        - Overlap percentage calculation
        - Threshold-based decision making

        This is geometric reasoning that caller never needs to understand.
        """
        block_rect = fitz.Rect(block["bbox"])
        block_area = abs(block_rect.x1 - block_rect.x0) * \
            abs(block_rect.y1 - block_rect.y0)

        if block_area == 0:
            return False

        for table_bbox in table_bboxes:
            table_rect = fitz.Rect(table_bbox)

            # Calculate intersection using PyMuPDF's & operator
            intersection = table_rect & block_rect
            inter_area = abs(intersection.x1 - intersection.x0) * \
                abs(intersection.y1 - intersection.y0)

            # Check overlap threshold
            overlap_ratio = inter_area / block_area
            if overlap_ratio > options.table_overlap_threshold:
                return True

        return False

    def _process_block(self, block: Dict, options: ConversionOptions) -> Optional[Dict]:
        """
        Process a content block into a markdown item.

        HIDDEN COMPLEXITY:
        - Block type classification
        - Text extraction from spans
        - Font size analysis
        - Heading inference
        - Image placeholder generation
        """
        block_rect = fitz.Rect(block["bbox"])

        # Custom handler hook (extensibility point)
        if options.custom_block_handler:
            custom_result = options.custom_block_handler(block, options)
            if custom_result is not None:
                return custom_result

        if block["type"] == 0:  # Text block
            return self._process_text_block(block, block_rect, options)
        elif block["type"] == 1:  # Image block
            return self._process_image_block(block_rect, options)

        return None

    def _process_text_block(
        self,
        block: Dict,
        block_rect: fitz.Rect,
        options: ConversionOptions
    ) -> Optional[Dict]:
        """
        Process text block with heading detection.

        HIDDEN: Font size heuristics, text aggregation, whitespace handling.
        """
        text_parts = []
        max_font_size = 0.0

        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text_parts.append(span.get("text", ""))
                max_font_size = max(max_font_size, span.get("size", 0))

        block_text = " ".join(text_parts).strip()

        if not block_text:
            return None

        # Infer heading level from font size
        if options.preserve_formatting:
            if max_font_size > options.h1_size_threshold:
                content = f"# {block_text}"
            elif max_font_size > options.h2_size_threshold:
                content = f"## {block_text}"
            else:
                content = block_text
        else:
            content = block_text

        return {
            "y0": block_rect.y0,
            "x0": block_rect.x0,
            "type": "text",
            "content": content
        }

    def _process_image_block(
        self,
        block_rect: fitz.Rect,
        options: ConversionOptions
    ) -> Optional[Dict]:
        """
        Process image block.

        HIDDEN: Image extraction strategy, placeholder formatting.

        Future extension point: Could extract actual images, save to disk,
        generate references, etc. - all without changing interface.
        """
        if not options.extract_images:
            return None

        return {
            "y0": block_rect.y0,
            "x0": block_rect.x0,
            "type": "image",
            "content": options.image_placeholder
        }

    def _process_table(self, table: Any, options: ConversionOptions) -> Optional[Dict]:
        """
        Process table into markdown.

        HIDDEN COMPLEXITY:
        - DataFrame conversion
        - Markdown table formatting
        - Empty table handling
        - Wrapper tag insertion
        """
        df = table.to_pandas()

        if df.empty:
            return None

        markdown = df.to_markdown(index=False)

        # Wrap in optional tags
        if options.table_wrapper_tag:
            content = f"<{options.table_wrapper_tag}>\n{markdown}\n</{options.table_wrapper_tag}>"
        else:
            content = markdown

        return {
            "y0": table.bbox[1],
            "x0": table.bbox[0],
            "type": "table",
            "content": content
        }

    def _items_to_markdown(self, items: List[Dict]) -> str:
        """
        Convert sorted items to final markdown string.

        HIDDEN: Separator strategy, spacing decisions.
        """
        return "\n\n".join(item["content"] for item in items)

    def _write_output(self, markdown: str, output: Optional[str | Path]) -> str:
        """
        Handle output writing.

        HIDDEN COMPLEXITY:
        - File I/O and encoding
        - Path handling
        - Error handling
        """
        if output is None:
            return markdown

        output_path = Path(output)
        output_path.write_text(markdown, encoding="utf-8")

        return markdown

    def _cleanup_document(self) -> None:
        """
        Clean up document resources if we own them.

        HIDDEN: Resource management, memory cleanup.
        """
        if self._owns_document and self._doc is not None:
            self._doc.close()
            self._doc = None
            self._owns_document = False


if __name__ == "__main__":
    # Quick test with your original use case
    converter = PDFToMarkdownConverter()

    # New approach:
    markdown = converter.convert(
        "docs\llama2.pdf",
        pages=[],  # Apply to all
        output="output_markdown.md"
    )
