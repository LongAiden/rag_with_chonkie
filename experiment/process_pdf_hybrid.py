"""
Hybrid PDF → Markdown using PyMuPDF (fitz) + Gemini VLM.

Strategy:
  - fitz always handles text extraction on every page.
  - Gemini is called only on cropped regions, never on whole-page renders:
      * Inline images  →  each image block is cropped and described by Gemini.
      * Tables         →  fitz extracts first; low-quality tables are re-extracted
                          by sending only the cropped table region to Gemini.
"""

import io
import os
import re
from typing import Optional

import fitz
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
IMAGE_CROP_DPI = 150               # DPI for cropped image/table regions

# Table quality thresholds for rescue logic
TABLE_MIN_ROWS = 2                 # tables with fewer rows are "suspicious"
TABLE_EMPTY_CELL_RATIO = 0.5      # tables with >50% empty cells are "suspicious"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ---------------------------------------------------------------------------
# Gemini client (lazy singleton)
# ---------------------------------------------------------------------------

_gemini_model = None


def _get_gemini_model():
    """Initialise and cache the Gemini GenerativeModel."""
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model

    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise ImportError(
            "google-generativeai is required. Install with: "
            "pip install google-generativeai"
        ) from exc

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is not set. "
            "Add it to your .env file."
        )

    genai.configure(api_key=api_key)
    _gemini_model = genai.GenerativeModel(GEMINI_MODEL)
    return _gemini_model


def _png_bytes_to_pil(png_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png_bytes))


# ---------------------------------------------------------------------------
# VLM prompts
# ---------------------------------------------------------------------------

VLM_IMAGE_PROMPT = """\
Describe this image concisely for embedding in a markdown document.
- If it is a table, render it as a GitHub-flavoured markdown table.
- If it is a chart or diagram, describe what it shows in 1–3 sentences.
- If it is a photograph or illustration, describe its content briefly.
- Output only the description or markdown table — no commentary.
"""

VLM_TABLE_RESCUE_PROMPT = """\
This is a cropped region from a PDF page that contains a table.
Render the table as a GitHub-flavoured markdown table.
Preserve all cell values exactly as they appear.
Output only the markdown table — no commentary.
"""


# ---------------------------------------------------------------------------
# Gemini API calls (cropped regions only)
# ---------------------------------------------------------------------------

def call_vlm_for_region(png_bytes: bytes, prompt: str = VLM_IMAGE_PROMPT) -> str:
    """
    Send a cropped image/table region to Gemini for description or transcription.

    Args:
        png_bytes: PNG-encoded region image.
        prompt: Instruction prompt (defaults to VLM_IMAGE_PROMPT).

    Returns:
        Markdown description or table produced by Gemini.
    """
    try:
        model = _get_gemini_model()
        img = _png_bytes_to_pil(png_bytes)
        response = model.generate_content([img, prompt])
        return response.text
    except Exception as exc:
        print(f"  [VLM region] Gemini call failed: {exc}")
        return f"<!-- VLM region extraction failed: {exc} -->"


# ---------------------------------------------------------------------------
# Image description helpers
# ---------------------------------------------------------------------------

def _crop_block(page: fitz.Page, bbox: tuple, dpi: int = IMAGE_CROP_DPI) -> bytes:
    """Render a bounding-box region of a page to PNG bytes."""
    rect = fitz.Rect(bbox)
    # Add a small padding so we don't clip edge pixels
    padded = rect + fitz.Rect(-2, -2, 2, 2)
    clip = padded & page.rect          # clamp to page bounds
    pix = page.get_pixmap(clip=clip, dpi=dpi)
    return pix.tobytes("png")


def describe_page_images(page: fitz.Page) -> list[str]:
    """
    For every image block on a page, crop it and ask Gemini to describe it.

    Returns a list of descriptions in top-to-bottom (y0) order, matching the
    order in which '<image> image <image>' placeholders appear in the fitz
    markdown output.
    """
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_IMAGES)["blocks"]
    image_blocks = sorted(
        (b for b in blocks if b["type"] == 1),
        key=lambda b: b["bbox"][1],
    )

    descriptions = []
    for block in image_blocks:
        png_bytes = _crop_block(page, block["bbox"])
        desc = call_vlm_for_region(png_bytes, VLM_IMAGE_PROMPT)
        descriptions.append(desc.strip())

    return descriptions


def _replace_image_placeholders(markdown: str, descriptions: list[str]) -> str:
    """
    Replace each '<image> image <image>' placeholder in `markdown` with the
    corresponding Gemini description (in order of appearance).
    """
    placeholder = "<image> image <image>"
    for desc in descriptions:
        replacement = f"<image>\n\n{desc}\n\n</image>"
        markdown = markdown.replace(placeholder, replacement, 1)
    return markdown


# ---------------------------------------------------------------------------
# fitz extraction
# ---------------------------------------------------------------------------

def process_page_fitz(
    doc: fitz.Document,
    page: fitz.Page,
    page_num: int,
    last_table_headers: Optional[list],
    describe_images: bool = True,
) -> tuple:
    """
    Extract text and structure via fitz, then describe any inline images
    with Gemini (cropped regions only).

    Returns:
        (markdown_str, updated_last_table_headers)
    """
    from process_pdf_to_md import process_page_to_markdown

    page_md, updated_headers = process_page_to_markdown(doc, page_num, last_table_headers)

    if describe_images and "<image> image <image>" in page_md:
        descriptions = describe_page_images(page)
        if descriptions:
            page_md = _replace_image_placeholders(page_md, descriptions)

    return page_md, updated_headers


# ---------------------------------------------------------------------------
# Table rescue (fitz quality check)
# ---------------------------------------------------------------------------

def _is_suspicious_table(table_md: str) -> bool:
    """
    Return True if a markdown table looks low-quality:
    - Fewer than TABLE_MIN_ROWS data rows, OR
    - More than TABLE_EMPTY_CELL_RATIO fraction of cells are empty.
    """
    lines = [l for l in table_md.splitlines() if l.strip().startswith("|")]
    # Remove separator row (---|---)
    data_lines = [l for l in lines if not re.match(r"^\s*\|[\s\-|:]+\|\s*$", l)]

    if len(data_lines) < TABLE_MIN_ROWS:
        return True

    total_cells = 0
    empty_cells = 0
    for line in data_lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        total_cells += len(cells)
        empty_cells += sum(1 for c in cells if not c)

    if total_cells > 0 and (empty_cells / total_cells) > TABLE_EMPTY_CELL_RATIO:
        return True

    return False


def maybe_rescue_tables(page: fitz.Page, markdown: str) -> str:
    """
    Find <table> blocks in `markdown` that look low-quality and re-extract
    them by sending the corresponding page region to Gemini.

    Matching works by sequential index: the N-th <table> block in the markdown
    corresponds to the N-th table detected by page.find_tables().
    """
    # Find all <table>…<table> blocks
    table_pattern = re.compile(r"<table>\n(.*?)\n<table>", re.DOTALL)
    table_matches = list(table_pattern.finditer(markdown))

    if not table_matches:
        return markdown

    detected_tables = page.find_tables().tables  # fitz TableFinder result

    result = markdown
    offset = 0  # track string position shift after replacements

    for idx, match in enumerate(table_matches):
        table_md = match.group(1)

        if not _is_suspicious_table(table_md):
            continue

        if idx >= len(detected_tables):
            break  # no matching fitz table to crop

        fitz_table = detected_tables[idx]
        png_bytes = _crop_block(page, fitz_table.bbox)
        rescued_md = call_vlm_for_region(png_bytes, VLM_TABLE_RESCUE_PROMPT).strip()

        old_block = match.group(0)
        new_block = f"<table>\n{rescued_md}\n<table>"

        # Adjust for previous replacements shifting positions
        start = match.start() + offset
        end = match.end() + offset
        result = result[:start] + new_block + result[end:]
        offset += len(new_block) - len(old_block)

    return result


# ---------------------------------------------------------------------------
# Main hybrid processor
# ---------------------------------------------------------------------------

def process_pdf_hybrid(
    doc: fitz.Document,
    describe_images: bool = True,
    rescue_tables: bool = True,
) -> str:
    """
    Process a PDF document page-by-page using the hybrid fitz + Gemini strategy.

    Every page uses fitz for text extraction. Gemini is invoked only for
    cropped regions: inline images (describe_images=True) and low-quality
    tables (rescue_tables=True).

    Args:
        doc: Open fitz Document.
        describe_images: If True, inline images are described by Gemini
            (cropped per-image, not whole page).
        rescue_tables: If True, low-quality tables are re-extracted by Gemini
            (cropped per-table, not whole page).

    Returns:
        Full document markdown as a single string.
    """
    full_markdown = ""
    last_table_headers: Optional[list] = None
    total = len(doc)

    for page_num in range(total):
        page = doc[page_num]

        try:
            page_md, last_table_headers = process_page_fitz(
                doc, page, page_num, last_table_headers,
                describe_images=describe_images,
            )
            if rescue_tables:
                page_md = maybe_rescue_tables(page, page_md)

            full_markdown += page_md + "\n\n---\n\n"

        except Exception as exc:
            print(f"[page {page_num + 1}] error: {exc}")
            last_table_headers = None

        if (page_num + 1) % 10 == 0:
            print(f"  {page_num + 1}/{total} pages processed...")

    return full_markdown


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Hybrid PDF → Markdown converter (fitz + Gemini VLM)"
    )
    parser.add_argument("pdf", help="Path to the input PDF file")
    parser.add_argument(
        "-o", "--output", default="output_hybrid.md",
        help="Output markdown file (default: output_hybrid.md)",
    )
    parser.add_argument(
        "--no-image-desc", action="store_true",
        help="Disable Gemini image descriptions (cropped per image)",
    )
    parser.add_argument(
        "--no-rescue", action="store_true",
        help="Disable Gemini table rescue (cropped per table)",
    )
    parser.add_argument(
        "--pages", type=int, default=None,
        help="Process only the first N pages (useful for testing)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"PDF not found: {args.pdf}")
        raise SystemExit(1)

    print(f"Opening: {args.pdf}")
    doc = fitz.open(args.pdf)

    if args.pages:
        # Slice to a sub-document for quick testing
        sub = fitz.open()
        sub.insert_pdf(doc, from_page=0, to_page=min(args.pages - 1, len(doc) - 1))
        doc.close()
        doc = sub
        print(f"Processing first {len(doc)} page(s)...")
    else:
        print(f"Processing {len(doc)} pages...")

    md = process_pdf_hybrid(
        doc,
        describe_images=not args.no_image_desc,
        rescue_tables=not args.no_rescue,
    )
    doc.close()

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Saved → {args.output}")
