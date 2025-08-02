import fitz  # PyMuPDF


def extract_sorted_blocks_from_pdf(pdf_path):
    """
    Extracts all text and image blocks from a PDF, sorted top-to-bottom by y0 per page.

    Returns:
        A list of pages, where each page is a list of block dictionaries.
        Each block is either of type 'text' or 'image', with coordinates and content/size.
    """
    doc = fitz.open(pdf_path)
    all_pages = []

    for page_num, page in enumerate(doc, start=1):
        text_blocks = page.get_text("blocks")
        formatted_text_blocks = [
            {
                "type": "text",
                "y0": block[1],
                "x0": block[0],
                "x1": block[2],
                "y1": block[3],
                "text": block[4].strip()
            }
            for block in text_blocks if block[4].strip()
        ]

        raw_blocks = page.get_text("rawdict")["blocks"]
        formatted_image_blocks = []
        for block in raw_blocks:
            if "image" in block:
                x0, y0, x1, y1 = block["bbox"]
                formatted_image_blocks.append({
                    "type": "image",
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                    "image_id": block["image"][:10],
                    "width": x1 - x0,
                    "height": y1 - y0
                })

        page_blocks = formatted_text_blocks + formatted_image_blocks
        page_blocks.sort(key=lambda b: b["y0"])

        all_pages.append(page_blocks)

    return all_pages
