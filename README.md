# Chess Diagram Extractor v1.1

A modular and configurable pipeline that automatically parses chess books (PDF format), detects chessboard diagrams, extracts relevant metadata, and retrieves FEN (Forsyth-Edwards Notation) from diagrams using the Chessvision API.

## 🎯 Features

- **Cross-page diagram detection** - Handles diagrams split across pages
- **Smart chessboard detection** - Uses OpenCV contour analysis
- **Enhanced solution parsing** - Extracts pure moves and turn information
- **API rate limiting** - Random delays between Chessvision API calls
- **Modular architecture** - Easy to maintain and extend
- **Configurable patterns** - Adaptable to different PDF formats

## 📁 Project Architecture

```
chess-diagram-extractor/
├── main.py                    # Main application entry point
├── config.py                  # Configuration settings
├── setup_folders.py           # Folder structure setup script
├── chessvision_api.py         # Chessvision API handling with rate limiting
├── text_processing.py         # Enhanced text parsing and solution extraction
├── diagram_processor.py       # Core diagram processing logic
├── pdf_parse.py              # PDF parsing (extracts blocks from pages)
├── utils.py                  # Utility functions (chessboard detection)
├── image_extractor.py        # Image extraction utilities (optional)
├── inspect_pages.py          # Debug tool for page inspection (optional)
├── README.md                 # This file
├── data_input/               # Input folder for PDF files
│   └── your_chess_book.pdf   # Place PDF files here
└── data_output/              # Output folder for all results
    ├── extracted_diagrams.csv # Main results file
    └── extracted_images/     # Subfolder for saved images (if enabled)
        └── diagram_001.png   # Individual diagram images
```

### Core Files

| File | Purpose | Dependencies |
|------|---------|--------------|
| `main.py` | Application orchestration and CLI | All modules |
| `config.py` | Centralized configuration | None |
| `setup_folders.py` | Creates project folder structure | config.py |
| `pdf_parse.py` | PDF block extraction | PyMuPDF |
| `text_processing.py` | Text parsing and solution extraction | config.py |
| `diagram_processor.py` | Diagram assembly and processing | utils.py, text_processing.py, chessvision_api.py |
| `chessvision_api.py` | API communication with rate limiting | config.py |
| `utils.py` | Chessboard detection algorithms | OpenCV, PIL |

### Optional Files

| File | Purpose |
|------|---------|
| `image_extractor.py` | Standalone image extraction utility |
| `inspect_pages.py` | Debug tool for examining PDF structure |

## 🚀 Quick Start

### 1. Installation

```bash
# Install required dependencies
pip install PyMuPDF pillow opencv-python requests numpy
```

### 2. Setup Project Structure

```bash
# Create the folder structure
python setup_folders.py
```

This creates:
- `data_input/` - Place your PDF files here
- `data_output/` - All results will be saved here
- `data_output/extracted_images/` - Images (if saving is enabled)

### 3. Add Your PDF

```bash
# Copy your PDF to the input folder
cp your_chess_book.pdf data_input/
```

### 4. Configuration

Edit `config.py` to match your PDF:

```python
# PDF Processing
PDF_PATH = "data_input/The Woodpecker Method 2 -- Axel Smith -- 2024.pdf"
PAGE_START = 1        # Start from page 1 (or None for beginning)
PAGE_END = 10         # Process until page 10 (or None for end)
MAX_DIAGRAMS = 5      # Extract maximum 5 diagrams (or None for all)

# Diagram Structure (NEW!)
DIAGRAM_STRUCTURE = "header_image_solution"  # Default structure

# API Settings
USE_CHESSVISION_API = True
MIN_RAND_TIME = 1     # Minimum wait between API calls
MAX_RAND_TIME = 5     # Maximum wait between API calls

# Image Saving
SAVE_CHESSBOARD_IMAGES = False      # Don't save images by default
SAVE_NON_CHESSBOARD_IMAGES = False  # Don't save non-chessboard images
```     # Maximum wait between API calls

# Image Saving
SAVE_CHESSBOARD_IMAGES = False      # Don't save images by default
SAVE_NON_CHESSBOARD_IMAGES = False  # Don't save non-chessboard images
```

### 5. Run

```bash
python main.py
```

## 📊 Output

The tool generates `data_output/extracted_diagrams.csv` with the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| `page` | Page where diagram header was found | `5` |
| `diagram_number` | Diagram number from header | `"27"` |
| `players` | White and black players | `"Alekhine - Nimzowitsch"` |
| `year` | Game year | `"1927"` |
| `solution_move` | Pure chess move (cleaned) | `"f3"`, `"b5"` |
| `solution_move_with_notation` | Move with annotations | `"f3!"`, `"b5!"` |
| `solution_full_move` | Complete solution text | `"8.f3! A nice set-up against..."` |
| `solution_full_text` | Complete solution block (unlimited) | `"8.f3! A nice set-up against the bishops on b7 and b4, both of which fight for the e4-square. 8.e4?! is met by 8...Bb4+ and Black has a comfortable game."` |
| `solution_turn` | Who moves next | `"white"`, `"black"` |
| `fen` | Board position in FEN notation | `"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"` |
| `api_turn` | Turn from Chessvision API | `"white"`, `"black"` |
| `image_path` | Path to saved image (if enabled) | `"data_output/extracted_images/diagram_001.png"` |
| `image_page` | Page where image was found | `6` |
| `header_page` | Page where header was found | `5` |
| `solution_page` | Page where solution was found | `6` |

## 🎮 Expected Workflow

### Diagram Detection Pattern

The tool looks for this sequence (may span multiple pages):

1. **Header Text Block**: `"27. Alekhine – Nimzowitsch, New York 1927"`
   - Extracts: diagram number, players, year

2. **Image Block**: Chessboard diagram
   - Validates using contour analysis
   - Sends to Chessvision API for FEN extraction

3. **Solution Text Block**: `"8.f3! A nice set-up against the bishops..."`
   - Extracts: pure move, turn, full description

### Cross-Page Handling

The tool can find related components across pages:
- Header on page 5, image on page 6 ✅
- Image on page 3, solution on page 4 ✅
- All components within ±20 blocks of each other

## 🔧 Advanced Configuration

### For Different PDF Formats

Edit the regex patterns in `config.py`:

```python
# Current pattern for "27. Alekhine – Nimzowitsch, New York 1927"
DIAGRAM_HEADER_PATTERN = r'(\d+)\.\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[–-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),.*?(\d{4})'

# Current pattern for "8.f3! A nice set-up..."
SOLUTION_PATTERN = r'^\s*(\d+)(\.{1,3})\s*([a-hRNBQKO0-9][^\n]*)'
```

### Search Distance

Adjust how far to look for related components:

```python
MAX_SEARCH_DISTANCE = 20  # Look ±20 blocks from header
```

## 🏗️ Diagram Structure Configuration

The tool supports different diagram layouts found in various chess books:

### Available Structures

| Structure | Description | Example Books |
|-----------|-------------|---------------|
| `"header_image_solution"` | Header → Image → Solution (Default) | Woodpecker Method, most tactics books |
| `"image_header_solution"` | Image → Header → Solution | Some puzzle collections |
| `"header_solution_image"` | Header → Solution → Image | Analysis books |
| `"flexible"` | Search all directions | Mixed formats, unknown layouts |

### Structure Examples

#### Header → Image → Solution (Default)
```
27. Alekhine – Nimzowitsch, New York 1927
[CHESSBOARD IMAGE]
8.f3! A nice set-up against the bishops...
```

#### Image → Header → Solution
```
[CHESSBOARD IMAGE]
Problem 15: Kasparov vs Karpov, 1984
Solution: 22...Bxh2+! winning material
```

#### Header → Solution → Image
```
Position 12: Fischer – Spassky, Reykjavik 1972
The key move is 25.Rxf7! sacrificing the exchange
[CHESSBOARD IMAGE]
```

### Configuring for Your PDF

```python
# For Woodpecker Method (default)
DIAGRAM_STRUCTURE = "header_image_solution"

# For puzzle books with image first
DIAGRAM_STRUCTURE = "image_header_solution"

# For analysis books with solution before image
DIAGRAM_STRUCTURE = "header_solution_image"

# When you're not sure or mixed formats
DIAGRAM_STRUCTURE = "flexible"
```

## 🎮 Configuration Examples

### Process Specific Pages
```python
PAGE_START = 10       # Start from page 10
PAGE_END = 25         # Stop at page 25
MAX_DIAGRAMS = None   # Extract all diagrams in this range
```

### Extract Limited Diagrams
```python
PAGE_START = None     # Start from beginning
PAGE_END = None       # Go to end of document
MAX_DIAGRAMS = 20     # But only extract first 20 diagrams found
```

### Quick Testing
```python
PAGE_START = 1        # Start from page 1
PAGE_END = 5          # Only process first 5 pages
MAX_DIAGRAMS = 3      # Extract maximum 3 diagrams
USE_CHESSVISION_API = False  # Disable API for faster testing
DIAGRAM_STRUCTURE = "flexible"  # Try different structures
```

### Full Processing
```python
PAGE_START = None     # Process entire document
PAGE_END = None       # From start to finish
MAX_DIAGRAMS = None   # Extract all diagrams found
USE_CHESSVISION_API = True   # Get FEN for all diagrams
DIAGRAM_STRUCTURE = "header_image_solution"  # Standard structure
```

## 🎯 Chess Symbol Handling

The tool now handles all standard chess notation symbols:

### Evaluation Symbols
- `!` `?` `!!` `??` `!?` `?!` → Good/bad/brilliant/blunder moves
- `±` `∓` `+/-` `-+` → White/black advantage  
- `=` `∞` → Equal/unclear position
- `+-` `-+` → Winning advantage

### Strategic Symbols  
- `→` `↑` `↓` `↗` `↘` `↙` `↖` → Directional ideas
- `△` `▲` `▼` → Planning symbols
- `N` `⌚` → Novelty, time trouble
- `⊕` `⊖` `⊗` `⊙` → Special annotations

All these symbols are automatically cleaned from the `solution_move` field while being preserved in `solution_full_text` for context.

## 🛠️ Debug Tools

### Page Inspector

Use `inspect_pages.py` to examine PDF structure:

```bash
python inspect_pages.py
```

This shows you:
- All blocks on each page in order
- Text content preview
- Image dimensions and locations
- Pattern analysis for diagrams

### Configuration Testing

Test with a small page range first:

```python
PAGE_START = 1
PAGE_END = 3
USE_CHESSVISION_API = False  # Disable API for testing
```

## 📈 Performance

- **Processing Speed**: ~1-2 pages per second (without API)
- **API Calls**: 1-5 second delays between requests (configurable)
- **Memory Usage**: Processes images in memory, minimal disk usage
- **Cross-page Search**: Efficient flattened block structure

## 🐛 Troubleshooting

### Common Issues

1. **No diagrams found**
   - Try different `DIAGRAM_STRUCTURE` settings
   - Check pattern matching with `inspect_pages.py`
   - Verify `DIAGRAM_HEADER_PATTERN` matches your PDF format
   - Use `DIAGRAM_STRUCTURE = "flexible"` for unknown layouts

2. **Images not detected as chessboards**
   - Lower the threshold in `is_chessboard_like()` function
   - Enable `SAVE_NON_CHESSBOARD_IMAGES = True` to debug

3. **API timeouts**
   - Increase `API_TIMEOUT` in config
   - Check internet connection

4. **Missing solution moves**
   - Verify `SOLUTION_PATTERN` matches your solution format
   - Try different `DIAGRAM_STRUCTURE` options
   - Check if solutions are within `MAX_SEARCH_DISTANCE`

5. **Wrong diagram structure**
   - Use `inspect_pages.py` to see the actual layout
   - Try `DIAGRAM_STRUCTURE = "flexible"` first
   - Adjust to specific structure once you know the pattern

### Error Messages

| Error | Solution |
|-------|----------|
| `FileNotFoundError: PDF file not found` | Check `PDF_PATH` in config.py |
| `No module named 'fitz'` | Install PyMuPDF: `pip install PyMuPDF` |
| `API request timed out` | Increase `API_TIMEOUT` or check connection |

## 🔄 Version History

### v1.1 (Current)
- ✅ **Configurable diagram structures** for different PDF layouts
- ✅ **Enhanced chess symbol handling** (all standard notation symbols)
- ✅ **Updated for Woodpecker Method 2** (2024 edition)
- ✅ **Structured search algorithms** for better accuracy
- ✅ **Preset configurations** for common chess book formats
- ✅ Fixed CSV encoding issues with UTF-8-BOM
- ✅ Enhanced chess notation handling for readability
- ✅ Improved text normalization (♔→K, ±→+=, etc.)
- ✅ CSV-safe text processing with proper character handling
- ✅ Better Excel compatibility for viewing results
- ✅ Enhanced solution move extraction with character cleaning
- ✅ Unlimited text storage for solution blocks
- ✅ Organized folder structure (data_input/, data_output/)
- ✅ Modular architecture with setup script
- ✅ API rate limiting with random delays
- ✅ Cross-page diagram detection

### v1.0
- ✅ Basic diagram extraction
- ✅ Chessvision API integration
- ✅ Simple pattern matching

## 🤝 Contributing

1. Follow the modular architecture
2. Update this README when adding/removing files
3. Test with different PDF formats
4. Add configuration options for new features

## 📄 License

This project is provided as-is for educational and research purposes.