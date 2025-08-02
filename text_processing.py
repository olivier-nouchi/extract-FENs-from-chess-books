import re
import string
import cv2
import numpy as np
from PIL import Image
from config import DIAGRAM_HEADER_PATTERN, SOLUTION_PATTERN


def normalize_text(text):
    """
    Cleans OCR symbols and chess notation from text while preserving readability.
    """
    replacements = {
        # Chess pieces - convert to readable text
        '♔': 'K', '♕': 'Q', '♖': 'R', '♗': 'B', '♘': 'N', '♙': 'P',
        '♚': 'k', '♛': 'q', '♜': 'r', '♝': 'b', '♞': 'n', '♟': 'p',

        # Chess annotations - keep readable versions
        '†': '+', '‡': '++',
        '±': '+=', '∓': '-+', '±': '+/-', '∞': 'inf',
        '→': '->', '≠': '!=', '≡': '=',

        # Evaluation symbols (convert to text)
        '⊕': '+', '⊖': '-', '⊗': 'x', '⊙': 'o',
        '△': 'triangle', '▲': 'up', '▼': 'down',
        '↑': 'up', '↓': 'down', '↗': 'ne', '↘': 'se',
        '↙': 'sw', '↖': 'nw', '⇄': 'exchange',

        # Time and evaluation
        '⊕': 'with-idea', '⌚': 'time', '∞': 'infinity',

        # Punctuation and quotes
        '\u2026': '...', '…': '...',
        '"': '"', '"': '"', ''': "'", ''': "'",
        '–': '-', '—': '-', '½': '1/2',

        # Remove problematic characters but keep content
        'ƒ': 'f', 'μ': 'u'
    }

    for symbol, replacement in replacements.items():
        text = text.replace(symbol, replacement)

    return text.strip()


def extract_diagram_info(text):
    """
    Extract diagram number, players, and year from header text.

    Args:
        text: Text like "27. Alekhine – Nimzowitsch, New York 1927"

    Returns:
        tuple: (diagram_number, players, year) or (None, None, None)
    """
    text = normalize_text(text)
    match = re.search(DIAGRAM_HEADER_PATTERN, text)

    if match:
        diagram_number = match.group(1)
        white_player = match.group(2).strip()
        black_player = match.group(3).strip()
        year = match.group(4)
        players = f"{white_player} - {black_player}"
        return diagram_number, players, year

    return None, None, None


def clean_chess_move(move_text):
    """
    Clean a chess move by removing annotations and invalid characters.

    Args:
        move_text: Raw move text like "f3!" or "b5μ"

    Returns:
        str: Clean move like "f3" or "b5"
    """
    # Extended list of chess symbols to remove (from the chess notation reference)
    symbols_to_remove = [
        # Basic annotations
        '!', '?', '+', '#', '=',

        # Evaluation symbols
        '±', '∓', '∞', '†', '‡', '≠', '≡', '½',

        # OCR artifacts and variants
        'μ', 'u', 'inf', '+=', '-+', '+/-',

        # Additional chess notation symbols
        '!!', '??', '!?', '?!', '□', '○',

        # Strategic symbols from the reference image
        '↑', '↓', '→', '←', '↗', '↘', '↙', '↖',
        '⇄', '⊕', '⊖', '⊗', '⊙', '△', '▲', '▼',
        '⌚', 'N',  # N for novelty, ⌚ for time trouble

        # Text equivalents we might have converted
        'up', 'down', 'ne', 'se', 'sw', 'nw', 'exchange',
        'with-idea', 'time', 'infinity', 'triangle'
    ]

    move_only = move_text
    for symbol in symbols_to_remove:
        move_only = move_only.replace(symbol, '')

    # Keep only valid chess notation characters
    valid_chars = string.ascii_letters + string.digits + 'x-='
    move_only = ''.join(c for c in move_only if c in valid_chars)

    return move_only


def extract_solution_details(text):
    """
    Extract detailed solution information from text.

    Args:
        text: Text like "8.f3! A nice set-up against the bishops..." or
              "22... b5! Winning the d5-square for a heavy piece..."

    Returns:
        dict: {
            'full_move': '8.f3! A nice set-up against...',
            'move_number': '8',
            'move_only': 'f3',
            'move_with_notation': 'f3!',
            'turn': 'white' or 'black',
            'full_text': original text (unlimited length, CSV-safe)
        }
    """
    # Normalize text but preserve readability for full_text
    normalized_text = normalize_text(text).strip()
    match = re.search(SOLUTION_PATTERN, normalized_text)

    if not match:
        return None

    move_number = match.group(1)
    dots = match.group(2)
    move_text = match.group(3).strip()

    # Determine turn based on dots
    turn = 'black' if '...' in dots else 'white'

    # Extract just the move (first word, may include annotations like !, ?, +, #)
    move_parts = move_text.split()
    if move_parts:
        move_with_notation = move_parts[0]  # e.g., "f3!", "b5!", "Nxe4+"
        move_only = clean_chess_move(move_with_notation)
    else:
        move_with_notation = move_text
        move_only = clean_chess_move(move_text)

    # Full move notation (preserve complete text without character limits)
    full_move = f"{move_number}{dots} {move_text}"

    # Prepare CSV-safe full text
    csv_safe_text = prepare_csv_text(normalized_text)

    return {
        'full_move': full_move,
        'move_number': move_number,
        'move_only': move_only,
        'move_with_notation': move_with_notation,
        'turn': turn,
        'full_text': csv_safe_text  # CSV-safe version of complete text
    }


def prepare_csv_text(text):
    """
    Prepare text for CSV output by handling special characters and formatting.

    Args:
        text: Raw text that may contain problematic characters

    Returns:
        str: CSV-safe text
    """
    # Replace problematic characters that don't display well in CSV
    csv_replacements = {
        '\n': ' ',  # Replace newlines with spaces
        '\r': ' ',  # Replace carriage returns with spaces
        '\t': ' ',  # Replace tabs with spaces
    }

    for char, replacement in csv_replacements.items():
        text = text.replace(char, replacement)

    # Normalize multiple spaces to single spaces
    import re
    text = re.sub(r'\s+', ' ', text)

    # Ensure text is properly encoded for CSV
    try:
        # Try to encode and decode to catch any problematic characters
        text = text.encode('utf-8', errors='replace').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # If there are still issues, use ASCII with replacement
        text = text.encode('ascii', errors='replace').decode('ascii')

    return text.strip()


def is_diagram_header(text):
    """
    Check if text block is a diagram header.
    """
    diagram_num, players, year = extract_diagram_info(text)
    return diagram_num is not None


def is_solution_block(text):
    """
    Check if text block is a solution block.
    """
    solution_details = extract_solution_details(text)
    return solution_details is not None


def is_chessboard_like(image):
    """
    Detects if an image contains a chessboard using contour analysis.
    """
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(image, Image.Image):
            image_array = np.array(image)
        else:
            image_array = image

        # Convert to grayscale
        if len(image_array.shape) == 3:
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_array

        # Apply blur and edge detection
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 10, 50)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Count square-like shapes
        squares = 0
        for cnt in contours:
            # Approximate contour to polygon
            epsilon = 0.03 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)

            # Check if it's roughly rectangular
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / float(h)

                # Filter by aspect ratio and size
                if 0.4 < aspect_ratio < 1.8 and w > 5 and h > 5:
                    squares += 1

        # Threshold for chessboard detection
        return squares >= 4

    except Exception as e:
        print(f"Error in chessboard detection: {e}")
        return False


# Legacy functions for backward compatibility
def extract_solution_move(text):
    """
    Legacy function - extracts solution move in old format.
    """
    details = extract_solution_details(text)
    if details:
        return details['full_move'], details['turn']
    return None, None