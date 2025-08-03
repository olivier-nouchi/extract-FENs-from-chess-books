# === Configuration File ===

import os

# Folder Structure
INPUT_FOLDER = "data_input"      # Folder containing PDF files
OUTPUT_FOLDER = "data_output"    # Folder for all output files
IMAGES_FOLDER = "extracted_images"  # Subfolder for images (inside OUTPUT_FOLDER)

# PDF Processing
PDF_PATH = "data_input/The Woodpecker Method 2 -- Axel Smith -- 2024.pdf"  # Path to PDF file
PAGE_START = 29  # Set to specific page number to start from, or None for beginning
PAGE_END = None    # Set to specific page number to end at, or None for end of document
MAX_DIAGRAMS = 25  # Maximum number of diagrams to extract, or None for all diagrams

# API Settings
USE_CHESSVISION_API = False
MIN_RAND_TIME = 1    # Minimum wait time before API call (seconds)
MAX_RAND_TIME = 5    # Maximum wait time before API call (seconds)
API_TIMEOUT = 10     # API request timeout (seconds)

# Image Saving Flags
SAVE_CHESSBOARD_IMAGES = False      # Save detected chessboard images
SAVE_NON_CHESSBOARD_IMAGES = False  # Save non-chessboard images for debugging
SAVE_ALL_IMAGES_FOR_DEBUG = True    # Save all images during processing for debugging

# Logging and Debug Flags
ENABLE_DETAILED_LOGGING = True      # Show detailed block processing and order
SHOW_BLOCK_INSPECTION = True        # Show block-by-block analysis on each page

# Search Parameters
MAX_SEARCH_DISTANCE = 30  # Maximum blocks to search for related components (increased for cross-page)

# === DIAGRAM STRUCTURE CONFIGURATION ===
# Define the expected structure of diagrams in your PDF
# Available structures:
# - "header_image_solution": Header text -> Image -> Solution text (default)
# - "image_header_solution": Image -> Header text -> Solution text
# - "header_solution_image": Header text -> Solution text -> Image
# - "flexible": Search for all components within MAX_SEARCH_DISTANCE

DIAGRAM_STRUCTURE = "header_image_solution"  # Default structure for most chess books

# PDF-specific patterns (customize these for different PDFs)
DIAGRAM_HEADER_PATTERN = r'(\d+)\.\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[–-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),.*?(\d{4})'
SOLUTION_PATTERN = r'(\d+)(\.{1,3})\s*([a-hRNBQKO0-9][^\s\.,!?\n]*[!?]?)'  # More flexible pattern

# Solution block detection
SOLUTION_TRIGGER_TEXT = "Show/Hide Solution"  # Text that indicates solution block follows

# Output - Generate filename based on input PDF
def get_output_csv_path():
    """Generate output CSV filename based on input PDF name."""
    if PDF_PATH:
        # Extract filename without extension
        pdf_filename = os.path.splitext(os.path.basename(PDF_PATH))[0]
        # Clean filename for use in output
        clean_filename = "".join(c for c in pdf_filename if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_filename = clean_filename.replace(' ', '_')
        return f"{OUTPUT_FOLDER}/extracted_diagrams_{clean_filename}.csv"
    else:
        return f"{OUTPUT_FOLDER}/extracted_diagrams.csv"

OUTPUT_CSV = get_output_csv_path()

# === PRESET CONFIGURATIONS FOR DIFFERENT PDF TYPES ===

# Woodpecker Method 2 (current default)
WOODPECKER_METHOD_CONFIG = {
    "diagram_structure": "header_image_solution",
    "header_pattern": r'(\d+)\.\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[–-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),.*?(\d{4})',
    "solution_pattern": r'(\d+)(\.{1,3})\s*([a-hRNBQKO0-9][^\s\.,!?\n]*[!?]?)',
    "solution_trigger": "Show/Hide Solution"
}

# Add more presets here for other book formats
# TACTICS_BOOK_CONFIG = {
#     "diagram_structure": "image_header_solution",
#     "header_pattern": r'Problem\s+(\d+):\s*([A-Z][a-z]+.*?)\s*vs\s*([A-Z][a-z]+.*?)\s*(\d{4})',
#     "solution_pattern": r'Solution:\s*(\d+)(\.{1,3})\s*([a-hRNBQKO0-9][^\n]*)'
# }