"""
Draft: Hybrid PDF → Markdown using PyMuPDF (fitz) + VLM.

Routing logic:
  - Text-heavy pages / bordered tables  →  fitz path (fast, cheap)
  - Image-heavy / scanned / complex     →  VLM path  (robust, semantic)

This is proxy / skeleton code — VLM calls are stubbed out.
"""

import base64
import fitz
import os
from typing import Optional

# ---------------------------------------------------------------------------
# Thresholds (tune per document type)
# ---------------------------------------------------------------------------
TEXT_DENSITY_THRESHOLD = 100       # min chars for fitz to handle the page
IMAGE_AREA_RATIO_THRESHOLD = 0.6   # if images cover >60% of page → VLM
VLM_DPI = 200                      # render DPI when sending page to VLM


# ---------------------------------------------------------------------------
# VLM stub  (replace with real API call: Claude / GPT-4o / Gemini / etc.)
# ---------------------------------------------------------------------------

def call_vlm(png_bytes: bytes, prompt: str) -> str:
    """
    Stub: send a page image to a VLM and get markdown back.

    Replace the body with your actual API call, e.g.:
        import anthropic
        client = anthropic.Anthropic()
        b64 = base64.standard_b64encode(png_bytes).decode()
        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64",
                     "media_type": "image/png", "data": b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return msg.content[0].text
    """
    _ = png_bytes, prompt          # suppress unused warnings
    return "<!-- VLM output placeholder -->"


def call_vlm_for_region(png_bytes: bytes) -> str:
    """Stub: ask VLM to describe / transcribe a cropped image region."""
    _ = png_bytes
    return "<!-- VLM region placeholder -->"


# ---------------------------------------------------------------------------
# Page classifier
# ---------------------------------------------------------------------------

def classify_page(page: fitz.Page) -> str:
    """
    Returns 'fitz' or 'vlm' based on text density and image coverage.
    """
    text = page.get_text().strip()
    if len(text) < TEXT_DENSITY_THRESHOLD:
        return "vlm"                       # scanned or near-empty text

    image_blocks = [
        b for b in page.get_text("dict", flags=fitz.TEXT_PRESERVE_IMAGES)["blocks"]
        if b["type"] == 1
    ]
    image_area = sum(
        (b["bbox"][2] - b["bbox"][0]) * (b["bbox"][3] - b["bbox"][1])
        for b in image_blocks
    )
    page_area = page.rect.width * page.rect.height

    if page_area > 0 and (image_area / page_area) > IMAGE_AREA_RATIO_THRESHOLD:
        return "vlm"

    return "fitz"


# ---------------------------------------------------------------------------
# fitz path  (imports from existing script)
# ---------------------------------------------------------------------------

def process_page_fitz(
    doc: fitz.Document,
    page_num: int,
    last_table_headers: Optional[list],
) -> tuple:
    """
    Thin wrapper around process_page_to_markdown from process_pdf_to_md.py.
    Returns (markdown_str, updated_last_table_headers).
    """
    from process_pdf_to_md import process_page_to_markdown
    return process_page_to_markdown(doc, page_num, last_table_headers)


# ---------------------------------------------------------------------------
# VLM path
# ---------------------------------------------------------------------------

VLM_PAGE_PROMPT = """\
Convert this PDF page to clean markdown.
- Use # / ## / ### for headings based on visual size.
- Render tables as GitHub-flavoured markdown tables.
- For charts or diagrams write a short description in an <image> tag.
- Do not add commentary; output only the markdown.
"""


def process_page_vlm(page: fitz.Page, page_num: int) -> str:
    """
    Render page to PNG, hand off to VLM, return markdown string.
    last_table_headers is not threaded here — the VLM handles cross-page
    context implicitly (or you can add a prompt injection).
    """
    pix = page.get_pixmap(dpi=VLM_DPI)
    png_bytes = pix.tobytes("png")
    vlm_output = call_vlm(png_bytes, VLM_PAGE_PROMPT)
    return f"[Page {page_num + 1}]\n\n{vlm_output}\n\n"


# ---------------------------------------------------------------------------
# Optional: rescue bad fitz tables using VLM on the cropped region
# ---------------------------------------------------------------------------

def maybe_rescue_tables(page: fitz.Page, markdown: str) -> str:
    """
    Stub: after fitz processing, detect suspicious tables (e.g. single-row
    tables or tables with many empty cells) and re-process their bounding
    boxes with the VLM.
    """
    # TODO: parse `markdown` to find <table> blocks, check quality,
    #       crop page.get_pixmap(clip=bbox), call call_vlm_for_region()
    return markdown


# ---------------------------------------------------------------------------
# Main hybrid processor
# ---------------------------------------------------------------------------

def process_pdf_hybrid(doc: fitz.Document) -> str:
    full_markdown = ""
    last_table_headers: Optional[list] = None   # only used on fitz path
    total = len(doc)

    for page_num in range(total):
        page = doc[page_num]
        route = classify_page(page)

        try:
            if route == "fitz":
                page_md, last_table_headers = process_page_fitz(
                    doc, page_num, last_table_headers
                )
                page_md = maybe_rescue_tables(page, page_md)   # optional
            else:
                page_md = process_page_vlm(page, page_num)
                last_table_headers = None   # reset — VLM handled continuity

            full_markdown += page_md + "\n\n---\n\n"

        except Exception as e:
            print(f"[page {page_num + 1}] error ({route}): {e}")
            last_table_headers = None

        if (page_num + 1) % 50 == 0:
            print(f"  {page_num + 1}/{total} pages processed...")

    return full_markdown


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    file_path = r"D:\Books\sample.pdf"
    output_file = "output_hybrid.md"

    if not os.path.exists(file_path):
        print(f"PDF not found: {file_path}")
    else:
        print(f"Opening: {file_path}")
        doc = fitz.open(file_path)
        md = process_pdf_hybrid(doc)
        doc.close()

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Saved → {output_file}")
