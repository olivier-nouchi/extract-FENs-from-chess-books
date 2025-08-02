#!/usr/bin/env python3
"""
Chess Diagram Extractor v1.1
=============================

Modular and configurable pipeline that automatically parses chess books (PDF format),
detects chessboard diagrams, extracts metadata, and retrieves FEN notation.

Key Features:
- Cross-page diagram component detection
- Random API call delays for rate limiting
- Enhanced solution move extraction with proper encoding
- CSV-safe text processing for chess notation
- UTF-8 encoding with BOM for Excel compatibility
- Modular architecture for easy maintenance
- Configurable patterns for different PDF formats
- Organized folder structure for inputs and outputs

Usage:
    python main.py

Configuration:
    Edit config.py to customize settings

Folder Structure:
    data_input/     - Place PDF files here
    data_output/    - All outputs go here
"""

import csv
import os
from pdf_parse import extract_sorted_blocks_from_pdf
from diagram_processor import (
    get_all_blocks_flattened,
    find_related_blocks_structured,
    process_diagram
)
from text_processing import is_diagram_header, extract_diagram_info
from config import (
    PDF_PATH, PAGE_START, PAGE_END, MAX_DIAGRAMS, OUTPUT_CSV, OUTPUT_FOLDER,
    USE_CHESSVISION_API, SAVE_CHESSBOARD_IMAGES, SAVE_NON_CHESSBOARD_IMAGES,
    DIAGRAM_STRUCTURE
)


def print_header():
    """Print application header and configuration."""
    print("=" * 80)
    print("🏁 Chess Diagram Extractor v1.1")
    print("=" * 80)
    print(f"📄 PDF: {PDF_PATH}")
    print(f"📊 Pages: {PAGE_START or 'Start'} to {PAGE_END or 'End'}")
    print(f"🎯 Max diagrams: {MAX_DIAGRAMS or 'All'}")
    print(f"🏗️  Diagram structure: {DIAGRAM_STRUCTURE}")
    print(f"🌐 Chessvision API: {'✅ Enabled' if USE_CHESSVISION_API else '❌ Disabled'}")
    print(f"💾 Save chessboards: {'✅ Yes' if SAVE_CHESSBOARD_IMAGES else '❌ No'}")
    print(f"💾 Save non-chessboards: {'✅ Yes' if SAVE_NON_CHESSBOARD_IMAGES else '❌ No'}")
    print(f"📝 CSV encoding: UTF-8 with BOM")
    print("=" * 80)


def extract_diagrams():
    """
    Main function to extract chess diagrams from PDF.

    Returns:
        list: List of extracted diagram dictionaries
    """
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

            print(f"\n🔍 Found diagram header on page {block['page_number']}: #{diagram_number} - {players} ({year})")

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
                    if image_page != block['page_number']:
                        print(
                            f"📄 Cross-page diagram: Header on page {block['page_number']}, Image on page {image_page}")

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
    """
    Save results to CSV file with enhanced columns and proper encoding.

    Args:
        results: List of diagram dictionaries
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    fieldnames = [
        # Basic information
        "page", "diagram_number", "players", "year",

        # Solution information (enhanced in v2.0)
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
    with open(OUTPUT_CSV, "w", newline="", encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(results)

    print(f"💾 Results saved to: {OUTPUT_CSV}")
    print(f"📊 CSV encoding: UTF-8 with BOM for Excel compatibility")


def print_summary(results):
    """
    Print processing summary and statistics.

    Args:
        results: List of diagram dictionaries
    """
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
    """
    Main application entry point.
    """
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
    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()