# === Configuration File ===

import os

# Folder Structure
INPUT_FOLDER = "data_input"      # Folder containing PDF files
OUTPUT_FOLDER = "data_output"    # Folder for all output files
IMAGES_FOLDER = "extracted_images"  # Subfolder for images (inside OUTPUT_FOLDER)

# PDF Processing
PDF_PATH = "data_input/The Woodpecker Method 2 -- Axel Smith -- 2024.pdf"  # Path to PDF file
PAGE_START = 30  # Set to specific page number to start from, or None for beginning
PAGE_END = 32 #718    # Set to specific page number to end at, or None for end of document
MAX_DIAGRAMS = None  # Maximum number of diagrams to extract, or None for all diagrams

# API Settings
USE_CHESSVISION_API = False  # Enable ChessVision API for FEN extraction (disabled by default)
MIN_RAND_TIME = 1    # Minimum wait time before API call (seconds)
MAX_RAND_TIME = 5    # Maximum wait time before API call (seconds)
API_TIMEOUT = 10     # API request timeout (seconds)

# Image Saving Flags
SAVE_CHESSBOARD_IMAGES = True      # Save detected chessboard images
SAVE_NON_CHESSBOARD_IMAGES = True  # Save non-chessboard images for debugging
SAVE_ALL_IMAGES_FOR_DEBUG = True    # Save all images during processing for debugging
SAVE_ALL_PAGE_IMAGES = True        # Save ALL images found on each page for inspection

# Logging and Debug Flags
ENABLE_DETAILED_LOGGING = False      # Show detailed block processing and order (enabled for debugging)
SHOW_BLOCK_INSPECTION = True        # Show block-by-block analysis on each page

# Search Parameters
MAX_SEARCH_DISTANCE = 5  # Maximum blocks to search for related components (increased for cross-page)

# === DIAGRAM STRUCTURE CONFIGURATION ===
# Define the expected structure of diagrams in your PDF
# Available structures:
# - "header_image_solution": Header text -> Image -> Solution text (default)
# - "image_header_solution": Image -> Header text -> Solution text
# - "header_solution_image": Header text -> Solution text -> Image
# - "flexible": Search for all components within MAX_SEARCH_DISTANCE

DIAGRAM_STRUCTURE = "header_image_solution"  # Default structure for most chess books

# PDF-specific patterns (customize these for different PDFs)
# Simplified pattern that captures any name format between markers
DIAGRAM_HEADER_PATTERN = r'(\d+)\.\s*(.+?)\s*[–\-]\s*(.+?),\s*(.+?)\s+(\d{4})'
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

# Combinational Motifs Configuration
COMBINATIONAL_MOTIFS_CONFIG = {
    "diagram_structure": "grid_6_sections",  # Special structure for 6-section grid
    "page_division": {
        "rows": 3,
        "columns": 2,
        "capture_bubbles": True,  # Capture the small area above each diagram
        "bubble_analysis": {
            "detect_background_color": True,  # Detect white/black background
            "count_bubbles": True,  # Count number of bubbles per diagram
            "extract_bubble_numbers": True,  # Extract numbers inside bubbles
            "bubble_color_mapping": {
                "white": "white",  # White background
                "black": "black"   # Black background
            }
        }
    },
    "output_format": {
        "include_bubble_info": True,
        "bubble_columns": [
            "bubble_count",
            "bubble_numbers",  # Comma-separated list of numbers
            "bubble_colors",   # Comma-separated list of colors (white/black)
            "bubble_details"   # JSON-like format with full bubble info
        ]
    },
    "image_processing": {
        "section_padding": 20,  # Padding to avoid over-cropping
        "bubble_area_height": 0.15,  # 15% of section height for bubble detection
        "chessboard_detection": True,
        "save_individual_sections": True,
        "use_chessvision_api": False  # Deactivated for bubble detection focus
    }
}

# Add more presets here for other book formats
# TACTICS_BOOK_CONFIG = {
#     "diagram_structure": "image_header_solution",
#     "header_pattern": r'Problem\s+(\d+):\s*([A-Z][a-z]+.*?)\s*vs\s*([A-Z][a-z]+.*?)\s*(\d{4})',
#     "solution_pattern": r'Solution:\s*(\d+)(\.{1,3})\s*([a-hRNBQKO0-9][^\n]*)'
# }