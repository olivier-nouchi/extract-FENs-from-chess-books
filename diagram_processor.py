import os
from PIL import Image
import io
import fitz
from utils import is_chessboard_like
from text_processing import extract_diagram_info, extract_solution_details, is_diagram_header, is_solution_block
from chessvision_api import send_image_to_chessvision
from config import (
    SAVE_CHESSBOARD_IMAGES, SAVE_NON_CHESSBOARD_IMAGES,
    OUTPUT_FOLDER, IMAGES_FOLDER, USE_CHESSVISION_API, MAX_SEARCH_DISTANCE,
    DIAGRAM_STRUCTURE
)


def get_image_from_pdf_block(pdf_path, page_num, image_block):
    """
    Extract image data directly from PDF block without saving to disk.

    Returns:
        PIL Image object or None
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]  # Convert to 0-indexed

        # Get all images on the page
        image_list = page.get_images(full=True)

        if image_list:
            # For now, take the first image found on the page
            # TODO: Better matching by position/size
            img_index = image_list[0][0]
            base_image = doc.extract_image(img_index)
            image_bytes = base_image["image"]

            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            doc.close()
            return image

        doc.close()
        return None

    except Exception as e:
        print(f"Error extracting image from PDF: {e}")
        return None


def save_image_if_needed(image, filename, is_chessboard):
    """
    Save image to disk based on configuration flags.
    """
    should_save = (is_chessboard and SAVE_CHESSBOARD_IMAGES) or \
                  (not is_chessboard and SAVE_NON_CHESSBOARD_IMAGES)

    if should_save:
        # Create output directories if they don't exist
        output_images_dir = os.path.join(OUTPUT_FOLDER, IMAGES_FOLDER)
        if not os.path.exists(output_images_dir):
            os.makedirs(output_images_dir)

        filepath = os.path.join(output_images_dir, filename)
        image.save(filepath)
        print(f"💾 Saved image: {filepath}")
        return filepath

    return None


def get_all_blocks_flattened(all_blocks_by_page, actual_start_page):
    """
    Flatten all blocks from all pages into a single list with page references.
    """
    flattened_blocks = []

    for page_idx, blocks in enumerate(all_blocks_by_page):
        page_number = page_idx + actual_start_page

        for block_idx, block in enumerate(blocks):
            block_with_page = block.copy()
            block_with_page['page_number'] = page_number
            block_with_page['original_page_idx'] = page_idx
            block_with_page['original_block_idx'] = block_idx
            block_with_page['global_idx'] = len(flattened_blocks)
            flattened_blocks.append(block_with_page)

    return flattened_blocks


def find_related_blocks_structured(flattened_blocks, header_idx, pdf_path, structure_type):
    """
    Find image and solution blocks using structured search based on diagram layout.

    Args:
        flattened_blocks: List of all blocks across pages
        header_idx: Index of the diagram header block
        pdf_path: Path to PDF file for image extraction
        structure_type: Type of structure ("header_image_solution", "flexible", etc.)

    Returns:
        tuple: (image_block, solution_block, image_page) or (None, None, None)
    """
    if structure_type == "header_image_solution":
        return find_header_image_solution_structure(flattened_blocks, header_idx, pdf_path)
    elif structure_type == "image_header_solution":
        return find_image_header_solution_structure(flattened_blocks, header_idx, pdf_path)
    elif structure_type == "header_solution_image":
        return find_header_solution_image_structure(flattened_blocks, header_idx, pdf_path)
    else:  # flexible or unknown
        return find_related_blocks(flattened_blocks, header_idx, pdf_path)


def find_header_image_solution_structure(flattened_blocks, header_idx, pdf_path):
    """
    Find blocks using Header -> Image -> Solution structure (default for most chess books).
    """
    image_block = None
    image_page = None
    solution_block = None

    # Look for image block after header (within next 10 blocks)
    for idx in range(header_idx + 1, min(len(flattened_blocks), header_idx + 11)):
        block = flattened_blocks[idx]

        if block['type'] == 'image' and image_block is None:
            # Extract image and check if it's a chessboard
            image = get_image_from_pdf_block(pdf_path, block['page_number'], block)

            if image and is_chessboard_like(image):
                image_block = block
                image_page = block['page_number']
                print(f"🖼️  Found chessboard on page {image_page} (distance: {abs(idx - header_idx)} blocks)")

                # Now look for solution after the image (within next 10 blocks)
                for sol_idx in range(idx + 1, min(len(flattened_blocks), idx + 11)):
                    sol_block = flattened_blocks[sol_idx]

                    if sol_block['type'] == 'text' and is_solution_block(sol_block['text']):
                        solution_block = sol_block
                        print(
                            f"🎲 Found solution on page {sol_block['page_number']} (distance: {abs(sol_idx - idx)} blocks from image)")
                        break

                break  # Found image, stop looking

    return image_block, solution_block, image_page


def find_image_header_solution_structure(flattened_blocks, header_idx, pdf_path):
    """
    Find blocks using Image -> Header -> Solution structure.
    Note: In this case, header_idx actually points to the header, so we look backwards for image.
    """
    image_block = None
    image_page = None
    solution_block = None

    # Look for image block before header (within previous 10 blocks)
    for idx in range(max(0, header_idx - 10), header_idx):
        block = flattened_blocks[idx]

        if block['type'] == 'image':
            # Extract image and check if it's a chessboard
            image = get_image_from_pdf_block(pdf_path, block['page_number'], block)

            if image and is_chessboard_like(image):
                image_block = block
                image_page = block['page_number']
                print(
                    f"🖼️  Found chessboard on page {image_page} (distance: {abs(idx - header_idx)} blocks before header)")
                break

    # Look for solution after header
    for idx in range(header_idx + 1, min(len(flattened_blocks), header_idx + 11)):
        block = flattened_blocks[idx]

        if block['type'] == 'text' and is_solution_block(block['text']):
            solution_block = block
            print(f"🎲 Found solution on page {block['page_number']} (distance: {abs(idx - header_idx)} blocks)")
            break

    return image_block, solution_block, image_page


def find_header_solution_image_structure(flattened_blocks, header_idx, pdf_path):
    """
    Find blocks using Header -> Solution -> Image structure.
    """
    image_block = None
    image_page = None
    solution_block = None

    # Look for solution after header first
    for idx in range(header_idx + 1, min(len(flattened_blocks), header_idx + 11)):
        block = flattened_blocks[idx]

        if block['type'] == 'text' and is_solution_block(block['text']) and solution_block is None:
            solution_block = block
            print(f"🎲 Found solution on page {block['page_number']} (distance: {abs(idx - header_idx)} blocks)")

            # Now look for image after solution
            for img_idx in range(idx + 1, min(len(flattened_blocks), idx + 11)):
                img_block = flattened_blocks[img_idx]

                if img_block['type'] == 'image':
                    # Extract image and check if it's a chessboard
                    image = get_image_from_pdf_block(pdf_path, img_block['page_number'], img_block)

                    if image and is_chessboard_like(image):
                        image_block = img_block
                        image_page = img_block['page_number']
                        print(
                            f"🖼️  Found chessboard on page {image_page} (distance: {abs(img_idx - idx)} blocks from solution)")
                        break

            break  # Found solution, stop looking

    return image_block, solution_block, image_page


def find_related_blocks(flattened_blocks, header_idx, pdf_path):
    """
    Find image and solution blocks related to a diagram header using flexible search.
    Searches both forwards and backwards within max_distance blocks.

    Args:
        flattened_blocks: List of all blocks across pages
        header_idx: Index of the diagram header block
        pdf_path: Path to PDF file for image extraction

    Returns:
        tuple: (image_block, solution_block, image_page) or (None, None, None)
    """
    start_search = max(0, header_idx - MAX_SEARCH_DISTANCE)
    end_search = min(len(flattened_blocks), header_idx + MAX_SEARCH_DISTANCE + 1)

    image_block = None
    image_page = None
    solution_block = None

    # Search in both directions, but prioritize forward direction
    search_indices = list(range(header_idx + 1, end_search)) + list(range(start_search, header_idx))

    for idx in search_indices:
        block = flattened_blocks[idx]

        # Look for image block (chessboard)
        if block['type'] == 'image' and image_block is None:
            # Extract image and check if it's a chessboard
            image = get_image_from_pdf_block(pdf_path, block['page_number'], block)

            if image and is_chessboard_like(image):
                image_block = block
                image_page = block['page_number']
                print(f"🖼️  Found chessboard on page {image_page} (distance: {abs(idx - header_idx)} blocks)")

        # Look for solution block
        if block['type'] == 'text' and solution_block is None:
            if is_solution_block(block['text']):
                solution_block = block
                print(f"🎲 Found solution on page {block['page_number']} (distance: {abs(idx - header_idx)} blocks)")

        # Stop searching if we found both
        if image_block and solution_block:
            break

    return image_block, solution_block, image_page


def process_diagram(header_block, image_block, solution_block, image_page, diagram_count, pdf_path):
    """
    Process a complete diagram (header + image + solution) and extract all information.

    Returns:
        dict: Complete diagram information or None if processing fails
    """
    # Extract header information
    diagram_number, players, year = extract_diagram_info(header_block['text'])

    # Extract and process image
    image = get_image_from_pdf_block(pdf_path, image_page, image_block)
    if not image:
        print(f"❌ Failed to extract image for diagram #{diagram_number}")
        return None

    # Save image if needed
    filename = f"diagram_{diagram_count:03d}_page_{image_page}.png"
    image_path = save_image_if_needed(image, filename, True)

    # Get FEN from Chessvision if enabled
    fen = None
    api_turn = None
    if USE_CHESSVISION_API:
        fen, api_turn = send_image_to_chessvision(image)

    # Extract solution information
    solution_details = None
    if solution_block:
        solution_details = extract_solution_details(solution_block['text'])
        if solution_details:
            print(f"🎲 Solution: {solution_details['move_only']} ({solution_details['turn']} to move)")

    # Compile result
    result = {
        "page": header_block['page_number'],  # Page where header was found
        "diagram_number": diagram_number,
        "players": players,
        "year": year,

        # Solution details
        "solution_move": solution_details['move_only'] if solution_details else None,
        "solution_move_with_notation": solution_details['move_with_notation'] if solution_details else None,
        "solution_full_move": solution_details['full_move'] if solution_details else None,
        "solution_full_text": solution_details['full_text'] if solution_details else None,
        # Complete text without limits
        "solution_turn": solution_details['turn'] if solution_details else None,

        # API results
        "fen": fen,
        "api_turn": api_turn,

        # File paths and page references
        "image_path": image_path,
        "image_page": image_page,
        "header_page": header_block['page_number'],
        "solution_page": solution_block['page_number'] if solution_block else None
    }

    return result