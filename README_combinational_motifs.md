# Combinational Motifs Processor

This specialized processor is designed to extract chess diagrams from books with a 6-section grid layout, such as "Combinational Motifs". It divides each PDF page into 6 sections (2 columns × 3 rows), analyzes the bubbles above each chess diagram, and extracts FEN (Forsyth-Edwards Notation) positions using the ChessVision API.

## Features

- **6-Section Grid Division**: Automatically divides each page into 6 equal sections
- **Bubble Analysis**: Detects and analyzes circular bubbles above each diagram
- **Background Color Detection**: Identifies whether bubbles have white (outlined) or black (filled) backgrounds
- **Number Extraction**: Uses OCR to extract numbers from inside bubbles
- **FEN Extraction**: Uses ChessVision API to extract FEN positions from chess diagrams
- **Chessboard Detection**: Identifies which sections contain chess diagrams
- **Comprehensive Output**: Saves detailed information about each diagram, bubbles, and FEN positions

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements_combinational_motifs.txt
```

2. Install Tesseract OCR (required for bubble number extraction):
   - **macOS**: `brew install tesseract`
   - **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
   - **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki

## Usage

1. Place your PDF file in the `data_input` folder
2. Update the PDF path in `main_combinational_motifs.py` if needed
3. Run the processor:

```bash
python main_combinational_motifs.py
```

## Output

The processor generates:

1. **CSV File**: `data_output/combinational_motifs_fen_[filename].csv`
   - Page number and section number
   - Row and column position (0-2 for rows, 0-1 for columns)
   - Bubble count per diagram
   - Bubble numbers (comma-separated)
   - Bubble colors (white/black, comma-separated)
   - Detailed bubble information (JSON format)
   - **FEN position** (extracted from chess diagram)
   - **Turn indicator** (whose turn it is to move)
   - Section coordinates

2. **Section Images**: `data_output/section_images/`
   - Individual images of each detected chess diagram section
   - Useful for debugging and verification

## Configuration

The processor uses the `COMBINATIONAL_MOTIFS_CONFIG` in `config.py`:

```python
COMBINATIONAL_MOTIFS_CONFIG = {
    "diagram_structure": "grid_6_sections",
    "page_division": {
        "rows": 3,
        "columns": 2,
        "capture_bubbles": True,
        "bubble_analysis": {
            "detect_background_color": True,
            "count_bubbles": True,
            "extract_bubble_numbers": True,
            "bubble_color_mapping": {
                "white": "outlined",
                "black": "filled"
            }
        }
    },
    "image_processing": {
        "section_padding": 10,
        "bubble_area_height": 50,
        "chessboard_detection": True,
        "save_individual_sections": True
    }
}
```

## Example Output

For a page with 6 diagrams, the CSV will contain rows like:

| page_number | section_number | row | col | bubble_count | bubble_numbers | bubble_colors | fen | turn |
|-------------|----------------|-----|-----|--------------|----------------|---------------|-----|------|
| 1 | 1 | 0 | 0 | 2 | "1,1" | "white,black" | rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1 | white |
| 1 | 2 | 0 | 1 | 2 | "2,2" | "white,black" | rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1 | white |
| 1 | 3 | 1 | 0 | 2 | "4,2" | "white,black" | rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 1 | white |

## FEN Extraction

The processor uses the ChessVision API to extract FEN positions from each chess diagram:

1. **Image Processing**: Converts each section to the format required by ChessVision
2. **API Call**: Sends the image to ChessVision API with appropriate parameters
3. **FEN Parsing**: Extracts the FEN string and turn indicator from the API response
4. **Validation**: Only saves sections where FEN extraction was successful

## Bubble Analysis

The processor analyzes each bubble to determine:

1. **Count**: How many bubbles are above each diagram
2. **Numbers**: The numbers inside each bubble (extracted via OCR)
3. **Background Color**: 
   - White background = "outlined" bubbles
   - Black background = "filled" bubbles
4. **Position**: Coordinates of each bubble within the section

## Troubleshooting

- **No FEN detected**: Check if the ChessVision API is accessible and the image quality is sufficient
- **No bubbles detected**: Adjust the circle detection parameters in `detect_circles()`
- **Poor OCR results**: Ensure Tesseract is properly installed and try different preprocessing
- **Wrong section division**: Adjust the `section_padding` and `bubble_area_height` parameters
- **Missing chess diagrams**: Check the `detect_chessboard()` function parameters

## Customization

You can modify the processor behavior by:

1. Adjusting the grid layout (rows/columns) in the config
2. Changing bubble detection parameters
3. Modifying the OCR settings for better number extraction
4. Adjusting the ChessVision API parameters for better FEN extraction
5. Adding additional analysis features

## Dependencies

- **PyMuPDF**: PDF processing
- **OpenCV**: Image processing and computer vision
- **Pillow**: Image manipulation
- **pytesseract**: OCR for bubble number extraction
- **numpy**: Numerical operations
- **requests**: HTTP requests for ChessVision API
- **pandas**: Data processing (optional)

## File Structure

```
extract_FEN_from_chess_books/
├── config.py                           # Configuration file
├── combinational_motifs_processor.py   # Main processor
├── main_combinational_motifs.py        # Main script
├── chessvision_api.py                  # ChessVision API integration
├── requirements_combinational_motifs.txt # Dependencies
├── README_combinational_motifs.md      # This file
├── data_input/                         # Place PDF files here
└── data_output/                        # Output files
    ├── combinational_motifs_fen_*.csv  # Results with FEN
    └── section_images/                 # Debug images
``` 