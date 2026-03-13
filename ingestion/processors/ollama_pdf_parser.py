import base64
import io
import logging
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image as PILImage

from ingestion.processors.gemini_docling_parser import (
    GeminiDoclingParser,
    _strip_code_fences,
    _normalize_tables_in_markdown,
    _clean_html,
    _fix_table_closing_tags,
)
from ingestion.processors.prompts import (
    VLM_IMAGE_PROMPT as _VLM_IMAGE_PROMPT,
    VLM_TABLE_PROMPT as _VLM_TABLE_PROMPT,
    OLLAMA_IMAGE_PROMPT as _OLLAMA_IMAGE_PROMPT,
    OLLAMA_TABLE_PROMPT as _OLLAMA_TABLE_PROMPT,
)

logger = logging.getLogger(__name__)


class OllamaPDFParser(GeminiDoclingParser):
    """
    Hybrid PDF → Markdown using Docling layout extraction and a locally-hosted
    Ollama vision model for complex tables and figures.

    Key differences from GeminiDoclingParser:
    - _is_complex_table: AND instead of OR — prevents narrow tall tables (e.g. ToC) from going to VLM
    - _call_vlm: routes to Ollama with simpler prompts + fallback on failure
    - parse_pdf: page-by-page; heading levels are assigned via bbox height (inherited from base)
    """

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        vlm_model: str = "qwen3.5:9b",
        vlm_timeout: float = 120.0,
        images_scale: float = 1.0,
        complex_table_rows: int = 8,
        complex_table_cols: int = 6,
        max_pages: Optional[int] = None,
        h1_min_height: float = 20.0,
        h2_min_height: float = 11.0,
        h3_min_height: float = 9.0,
    ):
        super().__init__(
            api_key=None,
            gemini_model=None,
            rpm_limit=999,
            images_scale=images_scale,
            complex_table_rows=complex_table_rows,
            complex_table_cols=complex_table_cols,
            h1_min_height=h1_min_height,
            h2_min_height=h2_min_height,
            h3_min_height=h3_min_height,
        )
        self._ollama_base_url = ollama_base_url.rstrip("/")
        self._vlm_model = vlm_model
        self._vlm_timeout = vlm_timeout
        self._max_pages = max_pages

    def get_backend_name(self) -> str:
        return "ollama-docling"

    # ── Fix 1: AND instead of OR so narrow tall tables (ToC) stay in Docling ─

    def _is_complex_table(self, table) -> bool:
        try:
            return (
                table.data.num_rows > self._complex_table_rows
                and table.data.num_cols > self._complex_table_cols
            )
        except Exception:
            return False

    # ── Fix 2: Ollama VLM call with prompt remapping and fallback ─────────────

    def _call_vlm(self, pil_img: PILImage.Image, prompt: str) -> str:
        # Remap Gemini-tuned prompts to simpler Ollama-friendly versions
        if prompt is _VLM_IMAGE_PROMPT or prompt == _VLM_IMAGE_PROMPT:
            prompt = _OLLAMA_IMAGE_PROMPT
        elif prompt is _VLM_TABLE_PROMPT or prompt == _VLM_TABLE_PROMPT:
            prompt = _OLLAMA_TABLE_PROMPT

        try:
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

            self._vlm_calls += 1
            response = httpx.post(
                f"{self._ollama_base_url}/api/generate",
                json={
                    "model": self._vlm_model,
                    "prompt": prompt,
                    "images": [b64],
                    "stream": False,
                },
                timeout=self._vlm_timeout,
            )
            response.raise_for_status()
            raw = response.json()["response"]
            raw = _strip_code_fences(raw)
            raw = _normalize_tables_in_markdown(raw)
            return raw
        except Exception as exc:
            logger.warning(f"VLM call failed ({type(exc).__name__}: {exc}) — falling back to [IMAGE]")
            return "[IMAGE]"

    # ── Fix 3: page-by-page with heading level shift ──────────────────────────

    def parse_pdf(self, path, output_path=None) -> str:
        """Parse PDF page-by-page using Docling + Ollama VLM."""
        self._vlm_calls = 0
        pdf_path = str(path)

        total_pages = self._count_pages(pdf_path)
        if self._max_pages is not None:
            total_pages = min(total_pages, self._max_pages)
        logger.info(f"Parsing {total_pages} pages with Ollama VLM ({self._vlm_model})")

        pages_md = []
        out_file = None
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            out_file = open(output_path, "w", encoding="utf-8")

        converter = self._build_converter()

        try:
            for page_no in range(1, total_pages + 1):
                print(f"[{page_no}/{total_pages}] converting … ", end="", flush=True)
                try:
                    conv = converter.convert(pdf_path, page_range=(page_no, page_no))
                    doc = conv.document
                    items = [item for item, _ in doc.iterate_items() if item.prov]

                    page_md = self._process_page(page_no=page_no, items=items, doc=doc)
                    page_md = _normalize_tables_in_markdown(page_md)
                    page_md = _clean_html(page_md)
                    page_md = _fix_table_closing_tags(page_md)

                    chunk = page_md + "\n\n---\n\n"
                    pages_md.append(chunk)
                    if out_file:
                        out_file.write(chunk)
                        out_file.flush()
                    print("done")
                except Exception as exc:
                    print(f"ERROR: {exc}")
                    logger.error(f"[page {page_no}] {exc}", exc_info=True)
        finally:
            if out_file:
                out_file.close()

        markdown = "".join(pages_md)
        print(f"\nDone. Ollama VLM calls: {self._vlm_calls} | pages: {total_pages}")
        return markdown
