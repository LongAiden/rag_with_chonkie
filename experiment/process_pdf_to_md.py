import fitz  # PyMuPDF
import pandas as pd
import os
from typing import Optional


def process_page_to_markdown(
    doc: fitz.Document,
    page_num: int,
    last_table_headers: Optional[list] = None,
    continuation_y_threshold: float = 100.0,
) -> tuple:
    """
    Process a PDF page to markdown with custom formatting for headers,
    tables, and images.

    Cross-page table continuation is handled by passing `last_table_headers`
    from the previous page. If a table appears near the top of the page AND
    its column count matches the saved headers, all its rows are treated as
    data rows and the saved headers are applied.

    Args:
        doc: The open fitz Document.
        page_num: Zero-based page index.
        last_table_headers: Column headers from the last table seen on the
            previous page (None if no prior table or after a reset).
        continuation_y_threshold: Max y0 (pixels from top) for a table to be
            considered a cross-page continuation.

    Returns:
        (markdown_string, updated_last_table_headers)
    """
    page = doc[page_num]

    # 1. IDENTIFY TABLES
    # ------------------
    tables = page.find_tables()
    table_bboxes = [tab.bbox for tab in tables]

    # 2. EXTRACT ALL BLOCKS (Text & Images)
    # -------------------------------------
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_IMAGES)["blocks"]

    # List to store all content items with their Y-position for sorting
    items = []

    # 3. PROCESS TEXT AND IMAGE BLOCKS
    # --------------------------------
    for block in blocks:
        block_bbox = block["bbox"]
        block_rect = fitz.Rect(block_bbox)

        # Check if block is inside a table (intersection check)
        is_in_table = False
        for tab_bbox in table_bboxes:
            tab_rect = fitz.Rect(tab_bbox)
            intersection = tab_rect & block_rect
            intersect_area = max(0, intersection.x1 - intersection.x0) * \
                max(0, intersection.y1 - intersection.y0)
            block_area = max(0, block_rect.x1 - block_rect.x0) * \
                max(0, block_rect.y1 - block_rect.y0)
            if block_area > 0 and (intersect_area / block_area) > 0.5:
                is_in_table = True
                break

        if is_in_table:
            continue

        # --- Handle Text Blocks (Type 0) ---
        if block["type"] == 0:
            block_text = ""
            max_size = 0
            for line in block["lines"]:
                for span in line["spans"]:
                    block_text += span["text"] + " "
                    if span["size"] > max_size:
                        max_size = span["size"]

            block_text = block_text.strip()
            if not block_text:
                continue

            # Heuristic for Headers based on font size
            if max_size > 18:
                content = f"# {block_text}"
            elif max_size > 14:
                content = f"## {block_text}"
            else:
                content = block_text

            items.append({
                "y0": block_rect.y0,
                "x0": block_rect.x0,
                "type": "text",
                "content": content,
            })

        # --- Handle Image Blocks (Type 1) ---
        elif block["type"] == 1:
            items.append({
                "y0": block_rect.y0,
                "x0": block_rect.x0,
                "type": "image",
                "content": "<image> image <image>",
            })

    # 4. PROCESS TABLE BLOCKS
    # -----------------------
    # We use table.extract() (raw list-of-lists) instead of to_pandas() so we
    # can decide ourselves which row is the header.
    current_last_table_headers = last_table_headers

    for table in tables:
        cells = table.extract()  # list[list[str | None]]

        if not cells or not cells[0]:
            continue

        # Normalise None → empty string in every cell
        cells = [
            [str(c) if c is not None else "" for c in row]
            for row in cells
        ]

        col_count = len(cells[0])
        table_y0 = table.bbox[1]

        # ----------------------------------------------------------------
        # Detect cross-page continuation:
        #   • The table starts near the top of the page (y0 < threshold)
        #   • Its column count matches the headers saved from the prev page
        # ----------------------------------------------------------------
        is_continuation = (
            current_last_table_headers is not None
            and len(current_last_table_headers) == col_count
            and table_y0 < continuation_y_threshold
        )

        if is_continuation:
            # Every extracted row is data; overlay the saved headers.
            df = pd.DataFrame(cells, columns=current_last_table_headers)
            # current_last_table_headers stays the same - the table may
            # continue onto yet another page.
        else:
            # Normal table: first row is the header.
            if len(cells) > 1:
                df = pd.DataFrame(cells[1:], columns=cells[0])
            else:
                df = pd.DataFrame(cells)
            # Save this table's headers so the next page can detect a
            # continuation.
            current_last_table_headers = cells[0]

        if df.empty:
            continue

        table_content = df.to_markdown(index=False)
        formatted_table = f"<table>\n{table_content}\n<table>"

        items.append({
            "y0": table_y0,
            "x0": table.bbox[0],
            "type": "table",
            "content": formatted_table,
        })

    # 5. SORT AND COMPILE
    # -------------------
    items.sort(key=lambda x: (x["y0"], x["x0"]))

    markdown_output = f"[Page {page_num + 1}]\n\n"
    for item in items:
        markdown_output += item["content"] + "\n\n"

    return markdown_output, current_last_table_headers


if __name__ == "__main__":
    # --- EXECUTION: Convert full PDF and Write to File ---
    file_path = r"D:\Books\2-Aurélien-Géron-Hands-On-Machine-Learning-with-Scikit-Learn-Keras-and-Tensorflow_-Concepts-Tools-and-Techniques-to-Build-Intelligent-Systems-O'Reilly-Media-2019.pdf"
    output_file = "output_markdown.md"

    if os.path.exists(file_path):
        print(f"Opening PDF: {file_path}")
        doc = fitz.open(file_path)
        full_markdown = ""

        total_pages = len(doc)
        print(f"Processing {total_pages} pages. This might take a while...")

        last_table_headers = None  # Carries headers across page boundaries

        for page_num in range(min(10, len(doc))):
            try:
                page_markdown, last_table_headers = process_page_to_markdown(
                    doc, page_num, last_table_headers
                )
                full_markdown += page_markdown + "\n\n---\n\n"

                if (page_num + 1) % 50 == 0:
                    print(f"Processed {page_num + 1}/{total_pages} pages...")

            except Exception as e:
                print(f"Error processing page {page_num}: {e}")
                last_table_headers = None  # Reset on error to avoid bad state

        print(f"Writing output to {output_file}...")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_markdown)

        print(f"Successfully saved markdown to {output_file}")
        doc.close()
    else:
        print(f"PDF file not found at: {file_path}")
