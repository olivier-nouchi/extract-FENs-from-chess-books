import os
from PIL import Image
import io
import fitz
from utils import is_chessboard_like
from text_processing import (
    extract_diagram_info, extract_solution_details, is_diagram_header,
    is_solution_block, is_solution_trigger_block, find_solution_after_trigger
)
from chessvision_api import send_image_to_chessvision
from config import (
    SAVE_CHESSBOARD_IMAGES, SAVE_NON_CHESSBOARD_IMAGES,
    OUTPUT_FOLDER, IMAGES_FOLDER, USE_CHESSVISION_API, MAX_SEARCH_DISTANCE,
    DIAGRAM_STRUCTURE, ENABLE_DETAILED_LOGGING, SHOW_BLOCK_INSPECTION,
    SAVE_ALL_IMAGES_FOR_DEBUG, SAVE_ALL_PAGE_IMAGES
)


def get_image_from_pdf_block(pdf_path, page_num, image_block):
    """
    Extract image data directly from PDF block without saving to disk.
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]  # Convert to 0-indexed

        # Get all images on the page with their positions
        image_list = page.get_images(full=True)

        if not image_list:
            print(f"⚠️  No images found on page {page_num}")
            doc.close()
            return None

        # Get the bounding box of our target image block
        target_x0, target_y0 = image_block.get('x0', 0), image_block.get('y0', 0)
        target_x1, target_y1 = image_block.get('x1', 0), image_block.get('y1', 0)
        target_width = target_x1 - target_x0
        target_height = target_y1 - target_y0

        print(f"🎯 Target: ({target_x0:.0f}, {target_y0:.0f}) to ({target_x1:.0f}, {target_y1:.0f}) = {target_width:.0f}x{target_height:.0f}")

        # Find the best matching image based on position AND size
        best_match = None
        best_score = -1

        for img_idx, img_info in enumerate(image_list):
            try:
                # Get image reference
                img_xref = img_info[0]

                # Find this image's position on the page
                blocks = page.get_text("rawdict")["blocks"]
                for block in blocks:
                    if "image" in block:
                        block_bbox = block["bbox"]
                        block_x0, block_y0, block_x1, block_y1 = block_bbox
                        block_width = block_x1 - block_x0
                        block_height = block_y1 - block_y0

                        # Calculate position similarity
                        center_x = (block_x0 + block_x1) / 2
                        center_y = (block_y0 + block_y1) / 2
                        target_center_x = (target_x0 + target_x1) / 2
                        target_center_y = (target_y0 + target_y1) / 2

                        position_distance = ((center_x - target_center_x) ** 2 + (center_y - target_center_y) ** 2) ** 0.5

                        # Calculate size similarity
                        size_similarity = 1.0
                        if target_width > 0 and target_height > 0:
                            width_ratio = min(block_width, target_width) / max(block_width, target_width)
                            height_ratio = min(block_height, target_height) / max(block_height, target_height)
                            size_similarity = width_ratio * height_ratio

                        # Combined score (position + size)
                        position_score = max(0, 100 - position_distance)  # Higher score for closer positions
                        size_score = size_similarity * 100  # Higher score for similar sizes
                        total_score = position_score * 0.6 + size_score * 0.4  # Weight position more than size

                        print(f"📍 Image {img_idx}: pos({block_x0:.0f},{block_y0:.0f}) size({block_width:.0f}x{block_height:.0f}) pos_dist={position_distance:.1f} size_sim={size_similarity:.2f} score={total_score:.1f}")

                        # Update best match if this score is better
                        if total_score > best_score:
                            best_score = total_score
                            best_match = img_xref
                            print(f"✅ New best match: Image {img_idx} (score: {total_score:.1f})")

            except Exception as e:
                print(f"⚠️  Error processing image {img_idx}: {e}")
                continue

        # Extract the best matching image
        if best_match is not None and best_score > 50:  # Higher score threshold to force fallback
            base_image = doc.extract_image(best_match)
            image_bytes = base_image["image"]

            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_bytes))

            print(f"🖼️  Extracted image {best_match} (score: {best_score:.1f})")

            # Special check for page 30: if extracted image is too small, use fallback
            if page_num == 30 and (image.size[0] < 100 or image.size[1] < 100):
                print(f"⚠️  Page 30: Extracted image too small ({image.size[0]}x{image.size[1]}), forcing fallback")
                # Continue to fallback instead of returning None
                best_match = None
                best_score = -1
                # Don't return here, continue to fallback
            else:
                doc.close()
                return image
        
        # If we get here, either no good match or page 30 fallback needed
        if best_match is None or best_score <= 50:
            print(f"⚠️  No good match found (best score: {best_score:.1f}), trying fallback")

            # Fallback: try to find any image with reasonable size
            print(f"🔄 Trying fallback extraction...")
            for img_idx, img_info in enumerate(image_list):
                try:
                    img_xref = img_info[0]
                    base_image = doc.extract_image(img_xref)
                    image_bytes = base_image["image"]
                    image = Image.open(io.BytesIO(image_bytes))
                    
                    print(f"🔄 Fallback image {img_idx}: {image.size[0]}x{image.size[1]} pixels")
                    
                    # Check if this image has reasonable size (prefer larger images)
                    if image.size[0] >= 200 and image.size[1] >= 200:
                        print(f"✅ Fallback success: Using image {img_idx} with size {image.size[0]}x{image.size[1]}")
                        doc.close()
                        return image
                        
                except Exception as e:
                    print(f"⚠️  Error in fallback image {img_idx}: {e}")
                    continue

            print(f"❌ No suitable fallback image found")
            doc.close()
            return None

    except Exception as e:
        print(f"❌ Error extracting image from PDF page {page_num}: {e}")
        return None


def save_image_if_needed(image, filename, is_chessboard, force_save=False):
    """
    Save image to disk based on configuration flags.
    """
    should_save = force_save or \
                  (is_chessboard and SAVE_CHESSBOARD_IMAGES) or \
                  (not is_chessboard and SAVE_NON_CHESSBOARD_IMAGES) or \
                  SAVE_ALL_IMAGES_FOR_DEBUG

    if should_save:
        # Create output directories if they don't exist
        output_images_dir = os.path.join(OUTPUT_FOLDER, IMAGES_FOLDER)
        if not os.path.exists(output_images_dir):
            os.makedirs(output_images_dir)

        filepath = os.path.join(output_images_dir, filename)
        image.save(filepath)

        if ENABLE_DETAILED_LOGGING:
            print(f"💾 Saved image: {filepath}")
        elif force_save or SAVE_ALL_IMAGES_FOR_DEBUG:
            print(f"🖼️  Saved debug image: {filepath}")

        return filepath

    return None


def save_all_page_images(pdf_path, page_number):
    """
    Save ALL images found on a specific page for inspection.
    """
    if not SAVE_ALL_PAGE_IMAGES:
        return
    
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_number - 1]  # Convert to 0-indexed
        
        # Get all images on the page
        image_list = page.get_images(full=True)
        
        if not image_list:
            print(f"⚠️  No images found on page {page_number}")
            doc.close()
            return
        
        print(f"📄 Found {len(image_list)} images on page {page_number}")
        
        # Create output directory
        output_images_dir = os.path.join(OUTPUT_FOLDER, IMAGES_FOLDER)
        if not os.path.exists(output_images_dir):
            os.makedirs(output_images_dir)
        
        # Extract and save each image
        for img_idx, img_info in enumerate(image_list):
            try:
                img_xref = img_info[0]
                base_image = doc.extract_image(img_xref)
                image_bytes = base_image["image"]
                
                # Convert to PIL Image
                image = Image.open(io.BytesIO(image_bytes))
                width, height = image.size
                
                # Save with descriptive filename
                filename = f"page_{page_number}_image_{img_idx:02d}_{width}x{height}.png"
                filepath = os.path.join(output_images_dir, filename)
                image.save(filepath)
                
                print(f"💾 Saved page image: {filename} ({width}x{height} pixels)")
                
            except Exception as e:
                print(f"⚠️  Error extracting image {img_idx} from page {page_number}: {e}")
                continue
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Error saving page images for page {page_number}: {e}")


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
    Find blocks using Header -> Image -> Solution structure.
    Focus on size and dimensions as primary criteria for chessboard detection.
    """
    image_block = None
    image_page = None
    solution_block = None

    header_block = flattened_blocks[header_idx]
    header_page = header_block['page_number']

    # Check if header is near the end of its page (likely cross-page scenario)
    blocks_on_same_page = [b for b in flattened_blocks[header_idx:] if b['page_number'] == header_page]
    header_position_on_page = next(i for i, b in enumerate(blocks_on_same_page) if b == header_block)
    is_near_page_end = header_position_on_page >= len(blocks_on_same_page) - 3  # Within last 3 blocks

    if is_near_page_end:
        print(f"🔄 Header appears near end of page {header_page} - extending search for cross-page diagram")
        search_range = 30  # Extended range for cross-page
    else:
        search_range = 20  # Normal range

    # Extended search range for cross-page scenarios
    search_end = min(len(flattened_blocks), header_idx + search_range + 1)

    print(f"🔍 Searching for image after header on page {header_page} (blocks {header_idx + 1} to {search_end - 1})")

    # Collect all image blocks first to examine them all
    image_blocks = []
    for idx in range(header_idx + 1, search_end):
        block = flattened_blocks[idx]
        if block['type'] == 'image':
            image_blocks.append((idx, block))
    
    print(f"🔍 Found {len(image_blocks)} image blocks to examine")
    
    # Show all image blocks found
    for i, (idx, block) in enumerate(image_blocks):
        width = block.get('width', 0)
        height = block.get('height', 0)
        print(f"  Image {i+1}: Block {idx}, Size: {width}x{height}")
        
        # Highlight potential chessboards
        if width == height and 200 <= width <= 400:
            print(f"    🎯 Potential chessboard candidate")
    
    # Examine all image blocks to find the best chessboard candidate
    chessboard_candidates = []
    
    for idx, block in image_blocks:
        print(f"\n--- Examining Image Block {idx} ---")
        print(f"🖼️  Examining image block {idx} on page {block['page_number']}")
        print(f"📍 Image position: ({block.get('x0', 0):.0f}, {block.get('y0', 0):.0f}) to ({block.get('x1', 0):.0f}, {block.get('y1', 0):.0f})")
        print(f"📏 Image size: {block.get('width', 'N/A')}x{block.get('height', 'N/A')}")

        # Extract image and check if it's a chessboard
        image = get_image_from_pdf_block(pdf_path, block['page_number'], block)

        if image:
            actual_width, actual_height = image.size
            print(f"✅ Extracted: {actual_width}x{actual_height} pixels")
            
            # Check if extracted image size matches block size
            if actual_width != block.get('width', 0) or actual_height != block.get('height', 0):
                print(f"⚠️  Size mismatch: Block says {block.get('width', 0)}x{block.get('height', 0)}, extracted is {actual_width}x{actual_height}")

            # Save image for debugging if enabled
            if SAVE_ALL_IMAGES_FOR_DEBUG:
                debug_filename = f"debug_page_{block['page_number']}_block_{idx}_{actual_width:.0f}x{actual_height:.0f}.png"
                save_image_if_needed(image, debug_filename, False, force_save=True)

            print(f"🔍 Testing chessboard detection...")
            is_chessboard = is_chessboard_like(image)

            if is_chessboard:
                # Store this as a candidate
                candidate = {
                    'block': block,
                    'page': block['page_number'],
                    'distance': abs(idx - header_idx),
                    'width': actual_width,
                    'height': actual_height,
                }
                chessboard_candidates.append(candidate)
                print(f"✅ CHESSBOARD CANDIDATE: {actual_width:.0f}x{actual_height:.0f} pixels")
            else:
                print(f"❌ Not a chessboard - detection failed")
        else:
            print(f"❌ Failed to extract image from page {block['page_number']}")

    # Select the best chessboard candidate
    if chessboard_candidates:
        print(f"\n🎯 Found {len(chessboard_candidates)} chessboard candidates:")
        for i, candidate in enumerate(chessboard_candidates):
            print(f"  {i+1}. {candidate['width']:.0f}x{candidate['height']:.0f} pixels, distance: {candidate['distance']} blocks")
        
        # Select the best candidate (prefer larger squares, closer to header)
        best_candidate = max(chessboard_candidates, key=lambda c: (c['width'], -c['distance']))
        
        image_block = best_candidate['block']
        image_page = best_candidate['page']
        distance = best_candidate['distance']
        
        print(f"🏆 Selected best candidate: {best_candidate['width']:.0f}x{best_candidate['height']:.0f} pixels")
        
        if image_page != header_page:
            print(f"🖼️  Found chessboard on page {image_page} (cross-page: header on {header_page}, distance: {distance} blocks)")
            print(f"📄 Successfully handled cross-page layout: {header_page} → {image_page}")
        else:
            print(f"🖼️  Found chessboard on page {image_page} (same page, distance: {distance} blocks)")
    
    # If we found a chessboard, look for solution
    if image_block:
        # Now look for solution after the image
        # First, look for "Show/Hide Solution" trigger
        sol_search_end = min(len(flattened_blocks), idx + 21)
        print(f"🔍 Searching for solution after image (blocks {idx + 1} to {sol_search_end - 1})")

        trigger_found = False
        for sol_idx in range(idx + 1, sol_search_end):
            sol_block = flattened_blocks[sol_idx]

            if sol_block['type'] == 'text':
                # Check for solution trigger first
                if is_solution_trigger_block(sol_block['text']):
                    print(f"🎯 Found solution trigger on page {sol_block['page_number']}")
                    # Look for actual solution after trigger
                    solution_block = find_solution_after_trigger(flattened_blocks, sol_idx)
                    trigger_found = True
                    break
                # If no trigger found, check for direct solution
                elif not trigger_found and is_solution_block(sol_block['text']):
                    solution_block = sol_block
                    sol_distance = abs(sol_idx - idx)
                    print(f"🎲 Found solution on page {sol_block['page_number']} (distance: {sol_distance} blocks from image)")
                    break

    if image_block is None and is_near_page_end:
        print(f"⚠️  No image found despite header at page end - may need manual inspection")

    return image_block, solution_block, image_page


def find_image_header_solution_structure(flattened_blocks, header_idx, pdf_path):
    """
    Find blocks using Image -> Header -> Solution structure.
    """
    image_block = None
    image_page = None
    solution_block = None

    header_block = flattened_blocks[header_idx]
    header_page = header_block['page_number']

    # Look for image block before header (within previous 20 blocks for cross-page)
    search_start = max(0, header_idx - 21)

    print(f"🔍 Searching for image before header on page {header_page} (blocks {search_start} to {header_idx - 1})")

    for idx in range(search_start, header_idx):
        block = flattened_blocks[idx]

        if block['type'] == 'image':
            # Extract image and check if it's a chessboard
            image = get_image_from_pdf_block(pdf_path, block['page_number'], block)

            if image and is_chessboard_like(image):
                image_block = block
                image_page = block['page_number']
                distance = abs(idx - header_idx)

                if image_page != header_page:
                    print(f"🖼️  Found chessboard on page {image_page} (cross-page: header on {header_page}, distance: {distance} blocks before header)")
                else:
                    print(f"🖼️  Found chessboard on page {image_page} (same page, distance: {distance} blocks before header)")
                break

    # Look for solution after header (within next 15 blocks)
    sol_search_end = min(len(flattened_blocks), header_idx + 16)

    print(f"🔍 Searching for solution after header (blocks {header_idx + 1} to {sol_search_end - 1})")

    for idx in range(header_idx + 1, sol_search_end):
        block = flattened_blocks[idx]

        if block['type'] == 'text' and is_solution_block(block['text']):
            solution_block = block
            distance = abs(idx - header_idx)

            if block['page_number'] != header_page:
                print(f"🎲 Found solution on page {block['page_number']} (cross-page: header on {header_page}, distance: {distance} blocks)")
            else:
                print(f"🎲 Found solution on page {block['page_number']} (same page, distance: {distance} blocks)")
            break

    return image_block, solution_block, image_page


def find_header_solution_image_structure(flattened_blocks, header_idx, pdf_path):
    """
    Find blocks using Header -> Solution -> Image structure.
    """
    image_block = None
    image_page = None
    solution_block = None

    header_block = flattened_blocks[header_idx]
    header_page = header_block['page_number']

    # Look for solution after header first (within next 15 blocks)
    sol_search_end = min(len(flattened_blocks), header_idx + 16)

    print(f"🔍 Searching for solution after header on page {header_page} (blocks {header_idx + 1} to {sol_search_end - 1})")

    for idx in range(header_idx + 1, sol_search_end):
        block = flattened_blocks[idx]

        if block['type'] == 'text' and is_solution_block(block['text']) and solution_block is None:
            solution_block = block
            distance = abs(idx - header_idx)

            if block['page_number'] != header_page:
                print(f"🎲 Found solution on page {block['page_number']} (cross-page: header on {header_page}, distance: {distance} blocks)")
            else:
                print(f"🎲 Found solution on page {block['page_number']} (same page, distance: {distance} blocks)")

            # Now look for image after solution (within next 15 blocks)
            img_search_end = min(len(flattened_blocks), idx + 16)

            print(f"🔍 Searching for image after solution (blocks {idx + 1} to {img_search_end - 1})")

            for img_idx in range(idx + 1, img_search_end):
                img_block = flattened_blocks[img_idx]

                if img_block['type'] == 'image':
                    # Extract image and check if it's a chessboard
                    image = get_image_from_pdf_block(pdf_path, img_block['page_number'], img_block)

                    if image and is_chessboard_like(image):
                        image_block = img_block
                        image_page = img_block['page_number']
                        img_distance = abs(img_idx - idx)

                        if image_page != block['page_number']:
                            print(f"🖼️  Found chessboard on page {image_page} (cross-page: solution on {block['page_number']}, distance: {img_distance} blocks from solution)")
                        else:
                            print(f"🖼️  Found chessboard on page {image_page} (same page, distance: {img_distance} blocks from solution)")
                        break

            break  # Found solution, stop looking

    return image_block, solution_block, image_page


def find_related_blocks(flattened_blocks, header_idx, pdf_path):
    """
    Find image and solution blocks related to a diagram header using flexible search.
    """
    # Extended search distance for cross-page scenarios
    extended_search_distance = MAX_SEARCH_DISTANCE + 10  # Add extra for page breaks

    start_search = max(0, header_idx - extended_search_distance)
    end_search = min(len(flattened_blocks), header_idx + extended_search_distance + 1)

    header_block = flattened_blocks[header_idx]
    header_page = header_block['page_number']

    image_block = None
    image_page = None
    solution_block = None

    print(f"🔍 Flexible search around header on page {header_page} (±{extended_search_distance} blocks)")

    # Search in both directions, but prioritize forward direction for cross-page scenarios
    # Forward search with extended range for page breaks
    forward_indices = list(range(header_idx + 1, end_search))
    # Backward search with standard range
    backward_indices = list(range(start_search, header_idx))

    search_indices = forward_indices + backward_indices

    for idx in search_indices:
        block = flattened_blocks[idx]
        block_page = block['page_number']
        distance = abs(idx - header_idx)

        # Look for image block (chessboard)
        if block['type'] == 'image' and image_block is None:
            # Extract image and check if it's a chessboard
            image = get_image_from_pdf_block(pdf_path, block_page, block)

            if image and is_chessboard_like(image):
                image_block = block
                image_page = block_page

                if image_page != header_page:
                    print(f"🖼️  Found chessboard on page {image_page} (cross-page: header on {header_page}, distance: {distance} blocks)")
                else:
                    print(f"🖼️  Found chessboard on page {image_page} (same page, distance: {distance} blocks)")

        # Look for solution block
        if block['type'] == 'text' and solution_block is None:
            if is_solution_block(block['text']):
                solution_block = block

                if block_page != header_page:
                    print(f"🎲 Found solution on page {block_page} (cross-page: header on {header_page}, distance: {distance} blocks)")
                else:
                    print(f"🎲 Found solution on page {block_page} (same page, distance: {distance} blocks)")

        # Stop searching if we found both
        if image_block and solution_block:
            break

    return image_block, solution_block, image_page


def process_diagram(header_block, image_block, solution_block, image_page, diagram_count, pdf_path):
    """
    Process a complete diagram (header + image + solution) and extract all information.
    """
    print(f"🎯 PROCESSING DIAGRAM #{diagram_count}")
    
    # Extract header information
    diagram_number, players, year = extract_diagram_info(header_block['text'])
    print(f"📝 Header: #{diagram_number} - {players} ({year})")

    # Extract and process image
    image = get_image_from_pdf_block(pdf_path, image_page, image_block)
    if not image:
        print(f"❌ Failed to extract image for diagram #{diagram_number}")
        return None

    # Save image if needed
    filename = f"diagram_{diagram_count:03d}_page_{image_page}.png"
    print(f"💾 Saving diagram image: {filename}")
    image_path = save_image_if_needed(image, filename, True)
    print(f"📁 Image saved to: {image_path}")

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