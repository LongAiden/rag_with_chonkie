import re
import time
import logging
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional

from PIL import Image as PILImage

from ingestion.processors.pdf_parser_base import PDFParserBase

logger = logging.getLogger(__name__)

# ── Prompts ───────────────────────────────────────────────────────────────────
_VLM_TABLE_PROMPT = """\
This is a cropped region from a PDF page containing a table.
Extract and render the table content.

Rules:
- Wrap the output in <table></table> tags (closing tag must be </table>).
- Optionally include <table_caption>Title</table_caption> before the table \
if a caption or title is visible above or below it.
- Use GitHub-flavoured markdown table syntax.
- Separator row must use ONLY dashes: |-|-| (no colons, no padding spaces).
- Do NOT use any HTML inside cells (no <br>, no <td>, no <tr>).
- If a cell contains multiple lines of text, join them with a single space \
in the SAME cell.
- Ensure every row has the same number of columns.
- If a cell is merged vertically (one value applies to multiple rows), keep \
the value in the top row only.
- If the table has multiple header rows, include all of them in order.
- Preserve all cell values exactly as they appear.
- Output only the <table>...</table> block — no commentary or preamble.
- Do NOT use code fences.
"""

_VLM_IMAGE_PROMPT = """\
This is an image, chart, diagram, figure, or visual element cropped from a PDF page.
Extract and preserve ALL content inside <figure></figure> tags.

Rules:
- Transcribe ALL visible text EXACTLY as it appears, in its original language.
  Do NOT translate, paraphrase, or describe text — copy it verbatim.
- If the image contains Japanese text, output it in Japanese. NEVER translate it to English.
- Do NOT write any English description or summary of the diagram structure.
- Preserve logical reading order (top-to-bottom, left-to-right within each column).
- For diagrams or flowcharts: transcribe ONLY the visible text labels, captions,
  and annotations verbatim in the original language. No English descriptions.
- For charts/graphs: transcribe all axis labels, legend entries, and data values.
- For colored boxes, banners, or callout regions: include ALL text inside them.
- If the image also contains a table, render it as a GFM markdown table.
- ALL transcribed text must be placed inside the <figure>...</figure> block.
- Output only the <figure>...</figure> block — no commentary or preamble.
- Do NOT use code fences.
"""

# ── Defaults ──────────────────────────────────────────────────────────────────
_DEFAULT_RPM_LIMIT = 10
_DEFAULT_COMPLEX_TABLE_ROWS = 8
_DEFAULT_COMPLEX_TABLE_COLS = 6
_DEFAULT_IMAGES_SCALE = 1.0


# ── Rate limiter ──────────────────────────────────────────────────────────────
class _RateLimiter:
    def __init__(self, max_calls: int = _DEFAULT_RPM_LIMIT, period: float = 60.0):
        self.max_calls = max_calls
        self.period = period
        self._calls: deque = deque()

    def wait(self):
        while True:
            now = time.monotonic()
            while self._calls and now - self._calls[0] >= self.period:
                self._calls.popleft()
            if len(self._calls) < self.max_calls:
                break
            sleep_for = self.period - (now - self._calls[0])
            logger.info(f"[rate limiter] quota reached, sleeping {sleep_for:.1f}s …")
            time.sleep(sleep_for)
        self._calls.append(time.monotonic())


# ── Post-processing helpers ───────────────────────────────────────────────────
def _normalize_table(table_md: str) -> str:
    lines = table_md.splitlines()
    result: list[str] = []
    for line in lines:
        if not line.strip().startswith("|"):
            result.append(line)
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r"[-:\s]+", c) for c in cells if c):
            result.append("|" + "|".join(["-"] * len(cells)) + "|")
            continue
        if cells and cells[0] == "" and any(c for c in cells[1:]):
            if result:
                prev = [c.strip() for c in result[-1].strip().strip("|").split("|")]
                for i, cont in enumerate(cells):
                    if cont and i < len(prev):
                        prev[i] = (prev[i] + " " + cont).strip()
                result[-1] = "| " + " | ".join(prev) + " |"
                continue
        result.append("| " + " | ".join(cells) + " |")
    return "\n".join(result)


def _clean_html(md: str) -> str:
    md = re.sub(r"\s*<br\s*/?>\s*", " ", md, flags=re.IGNORECASE)
    md = re.sub(r"</?t[rdh]\b[^>]*>", "", md, flags=re.IGNORECASE)
    return md


def _strip_code_fences(md: str) -> str:
    md = re.sub(r"^```(?:markdown)?\s*\n?", "", md, flags=re.IGNORECASE)
    md = re.sub(r"\n?```\s*$", "", md, flags=re.IGNORECASE)
    return md.strip()


def _fix_table_closing_tags(md: str) -> str:
    lines, result, in_table = md.splitlines(), [], False
    for line in lines:
        s = line.strip()
        if s == "<table>":
            if in_table:
                result.append("</table>")
                in_table = False
            else:
                result.append(line)
                in_table = True
        elif s == "</table>":
            result.append(line)
            in_table = False
        else:
            result.append(line)
    return "\n".join(result)


def _normalize_tables_in_markdown(md: str) -> str:
    out, buf = [], []

    def flush():
        if buf:
            out.extend(_normalize_table("\n".join(buf)).splitlines())
            buf.clear()

    for line in md.splitlines():
        if line.strip().startswith("|"):
            buf.append(line)
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out)


# ── Main parser ───────────────────────────────────────────────────────────────
class GeminiDoclingParser(PDFParserBase):
    """
    Hybrid PDF → Markdown using Docling layout extraction and Gemini
    for complex tables (> complex_table_rows rows or > complex_table_cols cols)
    and figures. No fitz — image rendering is 100% via docling.
    """

    def __init__(
        self,
        api_key: str,
        gemini_model: str = "gemini-2.5-flash",
        rpm_limit: int = _DEFAULT_RPM_LIMIT,
        images_scale: float = _DEFAULT_IMAGES_SCALE,
        complex_table_rows: int = _DEFAULT_COMPLEX_TABLE_ROWS,
        complex_table_cols: int = _DEFAULT_COMPLEX_TABLE_COLS,
        h1_min_height: float = 20.0,
        h2_min_height: float = 11.0,
        h3_min_height: float = 9.0,
    ):
        self._api_key = api_key
        self._gemini_model = gemini_model
        self._rate_limiter = _RateLimiter(rpm_limit)
        self._images_scale = images_scale
        self._complex_table_rows = complex_table_rows
        self._complex_table_cols = complex_table_cols
        self._h1_min_height = h1_min_height
        self._h2_min_height = h2_min_height
        self._h3_min_height = h3_min_height
        self._genai_model = None
        self._vlm_calls: int = 0

    def get_backend_name(self) -> str:
        return "gemini-docling"

    # ── Docling converter ─────────────────────────────────────────────────────

    def _build_converter(self):
        from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        opts = PdfPipelineOptions()
        opts.do_ocr = False
        opts.do_table_structure = True
        opts.table_structure_options = TableStructureOptions(do_cell_matching=True)
        opts.accelerator_options = AcceleratorOptions(
            num_threads=4, device=AcceleratorDevice.AUTO
        )
        opts.generate_page_images = True
        opts.generate_picture_images = True
        opts.images_scale = self._images_scale
        return DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
        )

    # ── Gemini client ─────────────────────────────────────────────────────────

    def _get_model(self):
        if self._genai_model is not None:
            return self._genai_model
        import google.generativeai as genai
        genai.configure(api_key=self._api_key)
        self._genai_model = genai.GenerativeModel(self._gemini_model)
        return self._genai_model

    def _call_gemini(self, pil_img: PILImage.Image, prompt: str, retries: int = 3) -> str:
        self._rate_limiter.wait()
        model = self._get_model()
        for attempt in range(retries):
            try:
                self._vlm_calls += 1
                return model.generate_content([pil_img, prompt]).text
            except Exception as exc:
                err = str(exc).lower()
                if "429" in err or "quota" in err or "resource_exhausted" in err:
                    if "per_day" in err or "day" in err:
                        raise RuntimeError("[Gemini] Daily quota exhausted.") from exc
                    wait = 60
                    logger.warning(f"RPM limit hit (attempt {attempt+1}/{retries}), waiting {wait}s …")
                    time.sleep(wait)
                    self._rate_limiter._calls.clear()
                    self._rate_limiter.wait()
                else:
                    raise
        raise RuntimeError(f"Gemini call failed after {retries} retries")

    def _call_vlm(self, pil_img: PILImage.Image, prompt: str) -> str:
        raw = self._call_gemini(pil_img, prompt)
        raw = _strip_code_fences(raw)
        raw = _normalize_tables_in_markdown(raw)
        return raw

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _is_complex_table(self, table) -> bool:
        try:
            return (
                table.data.num_rows > self._complex_table_rows
                or table.data.num_cols > self._complex_table_cols
            )
        except Exception:
            return False

    def _count_pages(self, pdf_path: str) -> int:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_path)
        count = len(pdf)
        pdf.close()
        return count

    @staticmethod
    def _item_sort_key(item) -> tuple[float, float]:
        if not item.prov:
            return (0.0, 0.0)
        bbox = item.prov[0].bbox
        return (-bbox.t, bbox.l)

    # ── Per-page assembly ─────────────────────────────────────────────────────

    def _find_same_band_items(self, anchor, all_items, h_gap_thresh: float = 20.0):
        from docling_core.types.doc import TextItem, SectionHeaderItem
        if not anchor.prov:
            return []
        ab = anchor.prov[0].bbox
        a_page = anchor.prov[0].page_no
        a_height = max(ab.t - ab.b, 1.0)
        result = []
        for item in all_items:
            if item is anchor:
                continue
            if not isinstance(item, (TextItem, SectionHeaderItem)):
                continue
            if not item.prov or item.prov[0].page_no != a_page:
                continue
            ib = item.prov[0].bbox
            v_overlap = min(ab.t, ib.t) - max(ab.b, ib.b)
            if v_overlap / a_height < 0.2:
                continue
            h_gap = max(0, ib.l - ab.r) if ib.l > ab.r else max(0, ab.l - ib.r)
            if h_gap <= h_gap_thresh:
                result.append(item)
        return result

    def _expand_and_crop(self, doc, page_no: int, bboxes, padding: int = 8):
        page = doc.pages.get(page_no)
        if page is None or page.image is None or page.image.pil_image is None:
            return None
        pil_full = page.image.pil_image
        img_w, img_h = pil_full.size
        ph = page.size.height
        l = min(b.l for b in bboxes)
        bot = min(b.b for b in bboxes)
        r = max(b.r for b in bboxes)
        t = max(b.t for b in bboxes)
        sc = self._images_scale
        pix_l = max(0,     int(l * sc) - padding)
        pix_t = max(0,     int((ph - t) * sc) - padding)
        pix_r = min(img_w, int(r * sc) + padding)
        pix_b = min(img_h, int((ph - bot) * sc) + padding)
        if pix_r <= pix_l or pix_b <= pix_t:
            return None
        return pil_full.crop((pix_l, pix_t, pix_r, pix_b))

    def _process_page(self, page_no: int, items: list, doc) -> str:
        from docling_core.types.doc import TableItem, PictureItem, TextItem, SectionHeaderItem

        # Pre-pass: find text items absorbed into adjacent picture crops
        adjacent_texts: dict = {}
        skip_ids: set = set()
        for item in items:
            if not isinstance(item, PictureItem) or not item.prov:
                continue
            band = self._find_same_band_items(item, items)
            if band:
                adjacent_texts[id(item)] = band
                skip_ids.update(id(t) for t in band)

        ordered: list = []
        for item in items:
            if not item.prov:
                continue
            y, x = self._item_sort_key(item)

            if id(item) in skip_ids:
                continue

            if isinstance(item, PictureItem):
                adj = adjacent_texts.get(id(item))
                if adj:
                    bboxes = [item.prov[0].bbox] + [t.prov[0].bbox for t in adj]
                    pil = self._expand_and_crop(doc, item.prov[0].page_no, bboxes)
                    if pil is None:
                        pil = item.get_image(doc)
                    label = f"image+{len(adj)} text-items"
                else:
                    pil = item.get_image(doc)
                    label = "image"
                if pil is None:
                    logger.warning(f"  p{page_no}: PictureItem has no image, skipping")
                    continue
                logger.info(f"  p{page_no}: {label} ({pil.width}×{pil.height}px) → Gemini")
                md = self._call_vlm(pil, _VLM_IMAGE_PROMPT).strip()

            elif isinstance(item, TableItem) and self._is_complex_table(item):
                pil = item.get_image(doc)
                if pil is None:
                    logger.warning(f"  p{page_no}: complex table has no image, falling back to Docling")
                    try:
                        md = item.export_to_markdown()
                    except Exception:
                        md = str(item.data)
                    md = f"<table>\n\n{md}\n\n</table>"
                else:
                    logger.info(
                        f"  p{page_no}: complex table "
                        f"({item.data.num_rows}×{item.data.num_cols}, "
                        f"{pil.width}×{pil.height}px) → Gemini"
                    )
                    md = self._call_vlm(pil, _VLM_TABLE_PROMPT).strip()
                    if not md.startswith("<table>"):
                        md = f"<table>\n\n{md}\n\n</table>"

            elif isinstance(item, TableItem):
                logger.debug(f"  p{page_no}: simple table ({item.data.num_rows}×{item.data.num_cols}) → Docling")
                try:
                    md = item.export_to_markdown()
                except Exception:
                    try:
                        md = item.export_to_dataframe().to_markdown(index=False)
                    except Exception:
                        md = str(item.data)
                md = f"<table>\n\n{md}\n\n</table>"

            elif isinstance(item, SectionHeaderItem):
                # Use bbox height as font-size proxy to assign heading level.
                # Docling often flattens all headers to level=1; height is more reliable.
                bbox_height = item.prov[0].bbox.t - item.prov[0].bbox.b
                if bbox_height > self._h1_min_height:
                    prefix = "#"
                elif bbox_height > self._h2_min_height:
                    prefix = "##"
                elif bbox_height > self._h3_min_height:
                    prefix = "###"
                else:
                    # Too small to be a heading — emit as body text to suppress
                    # false positives (e.g. inline styled "Constant width" labels).
                    md = (item.text or "").strip()
                    if not md:
                        continue
                    ordered.append((y, x, md))
                    continue
                md = f"{prefix} {item.text}"

            elif isinstance(item, TextItem):
                md = (item.text or "").strip()
                if not md:
                    continue

            else:
                continue

            ordered.append((y, x, md))

        ordered.sort(key=lambda t: (t[0], t[1]))
        body = "\n\n".join(md for _, _, md in ordered)
        return f"[PAGE:{page_no}]\n\n{body}"

    # ── Public API ────────────────────────────────────────────────────────────

    def parse_pdf(self, path: str | Path, output_path: Optional[str | Path] = None) -> str:
        """Parse a PDF to markdown using Docling + Gemini."""
        self._vlm_calls = 0
        pdf_path = str(path)

        logger.info(f"═══ GeminiDoclingParser: {Path(pdf_path).name} ═══")

        logger.info("Step 1/3  Docling converting …")
        conv = self._build_converter().convert(pdf_path)
        doc = conv.document

        logger.info("Step 2/3  Grouping elements by page …")
        page_items: dict[int, list] = defaultdict(list)
        for item, _level in doc.iterate_items():
            if item.prov:
                page_items[item.prov[0].page_no].append(item)

        total_pages = len(doc.pages)
        total_items = sum(len(v) for v in page_items.values())
        logger.info(f"{total_pages} pages, {total_items} elements")

        logger.info("Step 3/3  Assembling pages …")
        pages_md = []
        out_file = None

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            out_file = open(output_path, "w", encoding="utf-8")

        try:
            for page_no in range(1, total_pages + 1):
                print(f"[{page_no}/{total_pages}] … ", end="", flush=True)
                try:
                    page_md = self._process_page(page_no=page_no, items=page_items.get(page_no, []), doc=doc)
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
        if output_path:
            logger.info(f"Saved → {output_path}")

        print(f"\nDone. Gemini calls: {self._vlm_calls}  |  pages: {total_pages}")
        return markdown

    def _parse_page_by_page(self, path: str | Path, output_path: Optional[str | Path] = None) -> str:
        """
        Alternative: converts one page at a time via docling page_range=(n, n).
        Lower peak memory, but significantly slower for large documents.
        Use only when memory is the bottleneck.
        """
        self._vlm_calls = 0
        pdf_path = str(path)

        total_pages = self._count_pages(pdf_path)
        logger.info(f"Total pages: {total_pages}")

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
        if output_path:
            logger.info(f"Saved → {output_path}")

        print(f"\nDone. Gemini calls: {self._vlm_calls}  |  pages: {total_pages}")
        return markdown
