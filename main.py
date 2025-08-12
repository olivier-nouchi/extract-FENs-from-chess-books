#!/usr/bin/env python3
"""
Chess Diagram Extractor v1.1
=============================

Clean rewrite of main processing script.
Extracts chess diagrams from PDF files with enhanced cross-page detection,
solution parsing, and configurable logging.

Usage:
    python main.py

Configuration:
    Edit config.py to customize settings
"""

import csv
import os
from pdf_parse import extract_sorted_blocks_from_pdf
from diagram_processor import (
    get_all_blocks_flattened,
    find_related_blocks_structured,
    process_diagram,
    save_all_page_images
)
from text_processing import is_diagram_header, extract_diagram_info
from config import (
    PDF_PATH, PAGE_START, PAGE_END, MAX_DIAGRAMS, OUTPUT_FOLDER, IMAGES_FOLDER,
    USE_CHESSVISION_API, SAVE_CHESSBOARD_IMAGES, SAVE_NON_CHESSBOARD_IMAGES,
    DIAGRAM_STRUCTURE, get_output_csv_path, ENABLE_DETAILED_LOGGING,
    SHOW_BLOCK_INSPECTION
)


def log_detailed(message):
    """Print message only if detailed logging is enabled."""
    if ENABLE_DETAILED_LOGGING:
        print(message)


def inspect_page_blocks(blocks, page_number):
    """Display detailed information about blocks on a page for debugging."""
    if not SHOW_BLOCK_INSPECTION:
        return

    print(f"\n📄 PAGE {page_number} BLOCK INSPECTION")
    print("-" * 60)
    print(f"Total blocks: {len(blocks)}")

    for i, block in enumerate(blocks):
        block_type = block['type']
        y0 = block.get('y0', 0)
        x0 = block.get('x0', 0)

        if block_type == 'text':
            text = block.get('text', '').strip()
            text_preview = text[:80] + "..." if len(text) > 80 else text
            text_preview = text_preview.replace('\n', ' ').replace('\r', ' ')

            print(f"  {i + 1:2d}. [TEXT] pos:({x0:.0f},{y0:.0f}) | \"{text_preview}\"")

            # Import here to avoid circular imports
            from text_processing import is_solution_trigger_block, is_solution_block

            # Check for special block types
            if is_diagram_header(text):
                print(f"      🏷️  DIAGRAM HEADER detected")
            elif is_solution_trigger_block(text):
                print(f"      🎯 SOLUTION TRIGGER detected")
            elif is_solution_block(text):
                print(f"      🎲 SOLUTION BLOCK detected")

        elif block_type == 'image':
            width = block.get('width', 'N/A')
            height = block.get('height', 'N/A')
            x1 = block.get('x1', 0)
            y1 = block.get('y1', 0)

            print(f"  {i + 1:2d}. [IMAGE] pos:({x0:.0f},{y0:.0f}) to ({x1:.0f},{y1:.0f}) | size:{width}x{height}")

    print("-" * 60)


def print_header():
    """Print application header and configuration."""
    print("=" * 80)
    print("🏁 Chess Diagram Extractor v1.1")
    print("=" * 80)
    print(f"📄 PDF: {PDF_PATH}")
    print(f"📊 Pages: {PAGE_START or 'Start'} to {PAGE_END or 'End'}")
    print(f"🎯 Max diagrams: {MAX_DIAGRAMS or 'All'}")
    print(f"🏗️  Diagram structure: {DIAGRAM_STRUCTURE}")
    print(f"📁 Output file: {get_output_csv_path()}")
    print(f"🌐 Chessvision API: {'✅ Enabled' if USE_CHESSVISION_API else '❌ Disabled'}")
    print(f"💾 Save chessboards: {'✅ Yes' if SAVE_CHESSBOARD_IMAGES else '❌ No'}")
    print(f"💾 Save non-chessboards: {'✅ Yes' if SAVE_NON_CHESSBOARD_IMAGES else '❌ No'}")
    print(f"🔍 Detailed logging: {'✅ Enabled' if ENABLE_DETAILED_LOGGING else '❌ Disabled'}")
    print(f"📋 Block inspection: {'✅ Enabled' if SHOW_BLOCK_INSPECTION else '❌ Disabled'}")
    print(f"📝 CSV encoding: UTF-8 with BOM")
    print("=" * 80)


def extract_diagrams():
    """Main function to extract chess diagrams from PDF."""
    print_header()

    # Extract blocks from PDF
    print("📖 Extracting blocks from PDF...")
    all_blocks_by_page = extract_sorted_blocks_from_pdf(PDF_PATH)

    # Handle page range
    if PAGE_START or PAGE_END:
        start_idx = (PAGE_START - 1) if PAGE_START else 0
        end_idx = PAGE_END if PAGE_END else len(all_blocks_by_page)
        all_blocks_by_page = all_blocks_by_page[start_idx:end_idx]
        actual_start_page = PAGE_START or 1
    else:
        actual_start_page = 1

    # Flatten all blocks across pages for cross-page searching
    flattened_blocks = get_all_blocks_flattened(all_blocks_by_page, actual_start_page)

    print(f"📑 Processing {len(all_blocks_by_page)} pages with {len(flattened_blocks)} total blocks")

    # Show detailed block inspection if enabled
    if SHOW_BLOCK_INSPECTION:
        for page_idx, blocks in enumerate(all_blocks_by_page):
            page_number = page_idx + actual_start_page
            inspect_page_blocks(blocks, page_number)
    
    # Save all images from each page for inspection
    print("📸 Saving all page images for inspection...")
    for page_idx, blocks in enumerate(all_blocks_by_page):
        page_number = page_idx + actual_start_page
        save_all_page_images(PDF_PATH, page_number)
        
        # Check if we found the 360x360 image in the saved images
        if page_number == 30:
            print("🔍 Checking for 360x360 image in saved page images...")
            output_images_dir = os.path.join(OUTPUT_FOLDER, IMAGES_FOLDER)
            if os.path.exists(output_images_dir):
                saved_images = [f for f in os.listdir(output_images_dir) if f.startswith(f"page_{page_number}_image_")]
                for img_file in saved_images:
                    if "360x360" in img_file:
                        print(f"✅ Found 360x360 image: {img_file}")
                        # Test if our algorithm would detect this as a chessboard
                        print(f"🎯 360x360 image should be detected as chessboard (perfect square + ~67 KB)")
                        
                        # Test the detection criteria manually
                        print(f"🔍 Manual test of detection criteria:")
                        print(f"  - Is 360 == 360? {360 == 360}")
                        print(f"  - Is 200 <= 360 <= 400? {200 <= 360 <= 400}")
                        print(f"  - Expected file size ~67 KB, should be 45-85 KB range")
                        print(f"  - Should pass PRIORITY 1 if file size is in range")
                    else:
                        print(f"📄 Other image: {img_file}")

    results = []
    diagram_count = 0
    processed_headers = set()  # Track processed headers to avoid duplicates

    # Process each block looking for diagram headers
    for block_idx, block in enumerate(flattened_blocks):

        if block['type'] == 'text' and is_diagram_header(block['text']):
            diagram_number, players, year = extract_diagram_info(block['text'])
            header_key = f"{diagram_number}_{players}_{year}"

            # Skip if we already processed this header
            if header_key in processed_headers:
                continue

            processed_headers.add(header_key)

            if ENABLE_DETAILED_LOGGING:
                print(
                    f"\n🔍 Found diagram header on page {block['page_number']}: #{diagram_number} - {players} ({year})")
                print(f"🔍 Header block index: {block_idx}, global position in flattened blocks")
            else:
                print(
                    f"\n🔍 Found diagram header on page {block['page_number']}: #{diagram_number} - {players} ({year})")

            # Find related image and solution blocks using configured structure
            image_block, solution_block, image_page = find_related_blocks_structured(
                flattened_blocks, block_idx, PDF_PATH, DIAGRAM_STRUCTURE
            )

            if image_block:
                diagram_count += 1

                # Check if we've reached the maximum number of diagrams
                if MAX_DIAGRAMS and diagram_count > MAX_DIAGRAMS:
                    print(f"🎯 Reached maximum diagrams limit ({MAX_DIAGRAMS}). Stopping extraction.")
                    break

                # Process the complete diagram
                result = process_diagram(
                    header_block=block,
                    image_block=image_block,
                    solution_block=solution_block,
                    image_page=image_page,
                    diagram_count=diagram_count,
                    pdf_path=PDF_PATH
                )

                if result:
                    results.append(result)
                    print(f"✅ Diagram #{diagram_count} extracted successfully")

                    # Show cross-page info if applicable
                    cross_page_components = []
                    if image_page != block['page_number']:
                        cross_page_components.append(f"Image on page {image_page}")
                    if solution_block and solution_block['page_number'] != block['page_number']:
                        cross_page_components.append(f"Solution on page {solution_block['page_number']}")

                    if cross_page_components:
                        print(
                            f"📄 Cross-page diagram: Header on page {block['page_number']}, {', '.join(cross_page_components)}")

                    # Show progress if MAX_DIAGRAMS is set
                    if MAX_DIAGRAMS:
                        print(f"📈 Progress: {diagram_count}/{MAX_DIAGRAMS} diagrams extracted")

                else:
                    print(f"❌ Failed to process diagram #{diagram_number}")
            else:
                print(f"❌ No valid chessboard found for diagram #{diagram_number}")

        # Break outer loop if we've reached the maximum
        if MAX_DIAGRAMS and diagram_count >= MAX_DIAGRAMS:
            break

    return results


def save_results(results):
    """Save results to CSV file with enhanced columns and proper encoding."""
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    # Get dynamic output filename
    output_file = get_output_csv_path()

    fieldnames = [
        # Basic information
        "page", "diagram_number", "players", "year",

        # Solution information
        "solution_move",  # Pure move like "f3", "b5" (cleaned)
        "solution_move_with_notation",  # Move with annotations like "f3!", "b5!"
        "solution_full_move",  # Full text like "8.f3! A nice set-up..."
        "solution_full_text",  # Complete solution block text (unlimited, CSV-safe)
        "solution_turn",  # "white" or "black"

        # API results
        "fen", "api_turn",

        # File and page references
        "image_path", "image_page", "header_page", "solution_page"
    ]

    # Use UTF-8 encoding with BOM for better Excel compatibility
    with open(output_file, "w", newline="", encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(results)

    print(f"💾 Results saved to: {output_file}")
    print(f"📊 CSV encoding: UTF-8 with BOM for Excel compatibility")


def print_summary(results):
    """Print processing summary and statistics."""
    print(f"\n🎉 Processing complete!")
    print(f"📊 Extracted {len(results)} diagrams")

    # Show limits info
    if PAGE_START or PAGE_END:
        print(f"📄 Page range: {PAGE_START or 'Start'} to {PAGE_END or 'End'}")
    if MAX_DIAGRAMS:
        print(
            f"🎯 Diagram limit: {len(results)}/{MAX_DIAGRAMS} {'(reached limit)' if len(results) >= MAX_DIAGRAMS else '(completed)'}")

    if results:
        # Cross-page statistics
        cross_page_count = sum(1 for r in results if r['image_page'] != r['header_page'])
        if cross_page_count > 0:
            print(f"🔄 Cross-page diagrams: {cross_page_count}")

        # Turn statistics
        white_moves = sum(1 for r in results if r.get('solution_turn') == 'white')
        black_moves = sum(1 for r in results if r.get('solution_turn') == 'black')
        print(f"♔ White to move: {white_moves}")
        print(f"♛ Black to move: {black_moves}")

        # API statistics
        if USE_CHESSVISION_API:
            successful_fens = sum(1 for r in results if r.get('fen'))
            print(f"🎯 FEN extractions: {successful_fens}/{len(results)}")

        # Page range statistics
        if results:
            pages_with_diagrams = set(r['header_page'] for r in results)
            print(f"📖 Pages with diagrams: {len(pages_with_diagrams)} pages")
            print(f"📍 Page range: {min(pages_with_diagrams)} to {max(pages_with_diagrams)}")


def main():
    """Main application entry point."""
    try:
        # Extract diagrams from PDF
        results = extract_diagrams()

        # Save results to CSV
        save_results(results)

        # Print summary
        print_summary(results)

        return results

    except FileNotFoundError:
        print(f"❌ Error: PDF file '{PDF_PATH}' not found!")
        print("Please check the file path in config.py")
        return []
    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == "__main__":
    main()