from pdf_parse import extract_sorted_blocks_from_pdf
import os

# === Config ===
PDF_PATH = "wp_method.pdf"  # Change this to your PDF filename
PAGE_START = None  # Set to specific page number to start from, or None for all pages
PAGE_END = None  # Set to specific page number to end at, or None for all pages
MAX_TEXT_LENGTH = 200  # Maximum characters to show for text blocks


def truncate_text(text, max_length=MAX_TEXT_LENGTH):
    """Truncate text if it's too long, adding ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def inspect_pdf_pages(pdf_path, page_start=None, page_end=None):
    """
    Inspect and display all elements from each page in the order they appear.
    """
    print(f"Inspecting PDF: {pdf_path}")
    print("=" * 80)

    try:
        # Extract all blocks using your existing function
        all_blocks_by_page = extract_sorted_blocks_from_pdf(pdf_path)

        # Handle page range
        if page_start or page_end:
            start_idx = (page_start - 1) if page_start else 0
            end_idx = page_end if page_end else len(all_blocks_by_page)
            all_blocks_by_page = all_blocks_by_page[start_idx:end_idx]
            actual_start_page = page_start or 1
        else:
            actual_start_page = 1

        print(f"Total pages to process: {len(all_blocks_by_page)}")
        print("=" * 80)

        # Process each page
        for page_idx, blocks in enumerate(all_blocks_by_page):
            page_number = page_idx + actual_start_page

            print(f"\n📄 PAGE {page_number}")
            print("-" * 60)
            print(f"Total blocks on this page: {len(blocks)}")
            print()

            if not blocks:
                print("   (No blocks found on this page)")
                continue

            # Display each block in order
            for block_idx, block in enumerate(blocks, 1):
                block_type = block['type']
                y0 = block['y0']
                x0 = block['x0']

                if block_type == 'text':
                    text = block['text'].strip()
                    text_preview = truncate_text(text.replace('\n', ' '))

                    print(f"   {block_idx:2d}. [TEXT] (y:{y0:.1f}, x:{x0:.1f})")
                    print(f"       📝 \"{text_preview}\"")

                    # Show full text if it's short
                    if len(text) <= 50:
                        print(f"       📄 Full text: \"{text}\"")

                elif block_type == 'image':
                    width = block.get('width', 'N/A')
                    height = block.get('height', 'N/A')
                    image_id = block.get('image_id', 'N/A')

                    print(f"   {block_idx:2d}. [IMAGE] (y:{y0:.1f}, x:{x0:.1f})")
                    print(f"       🖼️  Size: {width} x {height}, ID: {image_id}")

                print()  # Empty line between blocks

            print("-" * 60)

        print(f"\n✅ Inspection complete!")
        print(f"📊 Summary:")

        # Count totals
        total_text_blocks = 0
        total_image_blocks = 0

        for blocks in all_blocks_by_page:
            for block in blocks:
                if block['type'] == 'text':
                    total_text_blocks += 1
                elif block['type'] == 'image':
                    total_image_blocks += 1

        print(f"   - Total text blocks: {total_text_blocks}")
        print(f"   - Total image blocks: {total_image_blocks}")
        print(f"   - Total blocks: {total_text_blocks + total_image_blocks}")

    except FileNotFoundError:
        print(f"❌ Error: PDF file '{pdf_path}' not found!")
        print("Please make sure the file exists and the path is correct.")
    except Exception as e:
        print(f"❌ Error processing PDF: {e}")


def find_diagram_patterns(pdf_path, page_start=None, page_end=None):
    """
    Look for potential diagram patterns in the block sequence.
    """
    print(f"\n🔍 LOOKING FOR DIAGRAM PATTERNS")
    print("=" * 80)

    try:
        all_blocks_by_page = extract_sorted_blocks_from_pdf(pdf_path)

        # Handle page range
        if page_start or page_end:
            start_idx = (page_start - 1) if page_start else 0
            end_idx = page_end if page_end else len(all_blocks_by_page)
            all_blocks_by_page = all_blocks_by_page[start_idx:end_idx]
            actual_start_page = page_start or 1
        else:
            actual_start_page = 1

        for page_idx, blocks in enumerate(all_blocks_by_page):
            page_number = page_idx + actual_start_page

            print(f"\n📄 PAGE {page_number} - Pattern Analysis")
            print("-" * 40)

            # Look for sequences that might be diagrams
            for i in range(len(blocks)):
                if blocks[i]['type'] == 'image':
                    print(f"\n🖼️  Image found at position {i + 1}")

                    # Show context around the image
                    start_context = max(0, i - 2)
                    end_context = min(len(blocks), i + 3)

                    print("   Context sequence:")
                    for j in range(start_context, end_context):
                        block = blocks[j]
                        marker = ">>> " if j == i else "    "

                        if block['type'] == 'text':
                            text_preview = truncate_text(block['text'].replace('\n', ' '), 80)
                            print(f"{marker}{j + 1}. [TEXT] \"{text_preview}\"")
                        else:
                            print(f"{marker}{j + 1}. [IMAGE] {block.get('width', '?')}x{block.get('height', '?')}")

    except Exception as e:
        print(f"❌ Error analyzing patterns: {e}")


if __name__ == "__main__":
    # First, inspect the page structure
    inspect_pdf_pages(PDF_PATH, PAGE_START, PAGE_END)

    # Then, look for diagram patterns
    find_diagram_patterns(PDF_PATH, PAGE_START, PAGE_END)