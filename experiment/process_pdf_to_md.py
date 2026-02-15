import fitz  # PyMuPDF
import pandas as pd
import os


def process_page_to_markdown(doc: fitz.Document, page_num: int) -> str:
    """
    Process a PDF page to markdown with custom formatting for headers,
    tables, and images.
    """
    page = doc[page_num]

    # 1. IDENTIFY TABLES
    # ------------------
    # We find tables first to get their bounding boxes.
    # This helps us avoid duplicating text that is already inside a table.
    tables = page.find_tables()
    table_bboxes = [tab.bbox for tab in tables]

    # 2. EXTRACT ALL BLOCKS (Text & Images)
    # -------------------------------------
    # get_text("dict") provides detailed layout info.
    # flags=fitz.TEXT_PRESERVE_IMAGES ensures image blocks are included.
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_IMAGES)["blocks"]

    # List to store all content items with their Y-position for sorting
    items = []

    # 3. PROCESS TEXT AND IMAGE BLOCKS
    # --------------------------------
    for block in blocks:
        block_bbox = block["bbox"]
        block_rect = fitz.Rect(block_bbox)

        # Check if block is inside a table (intersection check)
        # If a text block is mostly inside a table area, skip it
        is_in_table = False
        for i, tab_bbox in enumerate(table_bboxes):
            tab_rect = fitz.Rect(tab_bbox)

            # Use & operator for intersection to get the Intersection Rect
            intersection = tab_rect & block_rect

            # Calculate area manually to avoid version issues
            # Area = width * height
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

            # Reconstruct text and find max font size in this block
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
                "content": content
            })

        # --- Handle Image Blocks (Type 1) ---
        elif block["type"] == 1:
            items.append({
                "y0": block_rect.y0,
                "x0": block_rect.x0,
                "type": "image",
                "content": "<image> image <image>"
            })

    # 4. PROCESS TABLE BLOCKS
    # -----------------------
    for i, table in enumerate(tables):
        # Convert table to pandas DataFrame for easy string formatting
        df = table.to_pandas()

        # Format as requested: <table> content <table>
        if not df.empty:
            table_content = df.to_markdown(index=False)
            formatted_table = f"<table>\n{table_content}\n<table>"

            items.append({
                "y0": table.bbox[1],  # Use top Y coordinate
                "x0": table.bbox[0],
                "type": "table",
                "content": formatted_table
            })

    # 5. SORT AND COMPILE
    # -------------------
    # Sort items by vertical position (y0), then horizontal (x0)
    items.sort(key=lambda x: (x["y0"], x["x0"]))

    # Build final string
    markdown_output = f"[Page {page_num + 1}]\n\n"
    for item in items:
        markdown_output += item["content"] + "\n\n"

    return markdown_output


if __name__ == "__main__":
    # --- EXECUTION: Convert full PDF and Write to File ---
    file_path = r"D:\Books\2-Aurélien-Géron-Hands-On-Machine-Learning-with-Scikit-Learn-Keras-and-Tensorflow_-Concepts-Tools-and-Techniques-to-Build-Intelligent-Systems-O’Reilly-Media-2019.pdf"
    output_file = "output_markdown.md"

    if os.path.exists(file_path):
        print(f"Opening PDF: {file_path}")
        doc = fitz.open(file_path)
        full_markdown = ""

        total_pages = len(doc)
        print(f"Processing {total_pages} pages. This might take a while...")

        for page_num in range(min(10, len(doc))):
            try:
                # Add a separator between pages
                full_markdown += process_page_to_markdown(
                    doc, page_num) + "\n\n---\n\n"

                # Progress update
                if (page_num + 1) % 50 == 0:
                    print(f"Processed {page_num + 1}/{total_pages} pages...")

            except Exception as e:
                print(f"Error processing page {page_num}: {e}")

        # Write to file
        print(f"Writing output to {output_file}...")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_markdown)

        print(f"Successfully saved markdown to {output_file}")
        doc.close()
    else:
        print(f"PDF file not found at: {file_path}")
