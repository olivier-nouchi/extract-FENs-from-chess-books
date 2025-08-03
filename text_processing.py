import re
import string
import cv2
import numpy as np
from PIL import Image
from config import DIAGRAM_HEADER_PATTERN, SOLUTION_PATTERN


def normalize_text(text):
    """
    Cleans OCR symbols and chess notation from text while preserving readability.
    Enhanced to handle chess pieces in solution blocks like "*N*d2±"
    """
    replacements = {
        # Chess pieces - convert to readable text (including starred versions)
        '♔': 'K', '♕': 'Q', '♖': 'R', '♗': 'B', '♘': 'N', '♙': 'P',
        '♚': 'k', '♛': 'q', '♜': 'r', '♝': 'b', '♞': 'n', '♟': 'p',

        # Handle starred chess pieces (common in some chess books)
        '*♔*': 'K', '*♕*': 'Q', '*♖*': 'R', '*♗*': 'B', '*♘*': 'N', '*♙*': 'P',
        '*♚*': 'k', '*♛*': 'q', '*♜*': 'r', '*♝*': 'b', '*♞*': 'n', '*♟*': 'p',

        # Handle letter representations with stars (fallback)
        '*K*': 'K', '*Q*': 'Q', '*R*': 'R', '*B*': 'B', '*N*': 'N', '*P*': 'P',
        '*k*': 'k', '*q*': 'q', '*r*': 'r', '*b*': 'b', '*n*': 'n', '*p*': 'p',

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


def is_solution_block(text):
    """
    Check if text block is a solution block.
    Now looks for chess move patterns anywhere in the text, not just at the start.
    """
    solution_details = extract_solution_details(text)
    return solution_details is not None


def extract_solution_details(text):
    """
    Extract detailed solution information from text.
    Handles various formats including starred pieces like "17.*N*d2±"

    Args:
        text: Solution text that may contain move notation anywhere

    Returns:
        dict: Solution details with extracted move information
    """
    # Normalize text but preserve readability for full_text
    normalized_text = normalize_text(text).strip()

    # Enhanced patterns to handle starred pieces and various formats
    move_patterns = [
        # Black moves with ... (including starred pieces)
        r'(\d+)(\.{3})\s*(\*?[a-hRNBQKO0-9♔♕♖♗♘♙♚♛♜♝♞♟]\*?[^\s\.,!?\n]*[!?]?)',
        # White moves with . (including starred pieces)
        r'(\d+)(\.)\s*(\*?[a-hRNBQKO0-9♔♕♖♗♘♙♚♛♜♝♞♟]\*?[^\s\.,!?\n]*[!?]?)',
    ]

    best_match = None
    best_position = len(normalized_text)  # Start with end of text

    # Find the FIRST occurrence of any move pattern
    for pattern in move_patterns:
        for match in re.finditer(pattern, normalized_text):
            if match.start() < best_position:
                best_match = match
                best_position = match.start()

    if not best_match:
        return None

    move_number = best_match.group(1)
    dots = best_match.group(2)
    move_text = best_match.group(3).strip()

    # Determine turn based on dots
    turn = 'black' if '...' in dots else 'white'

    # Clean the move notation
    move_with_notation = move_text
    move_only = clean_chess_move_precise(move_with_notation)

    # Full move notation
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


def clean_chess_move_precise(move_text):
    """
    Precisely clean a chess move by removing only annotations, keeping the core move intact.

    Examples:
    - "f5+" → "f5" (remove check)
    - "Na5+" → "Na5" (keep piece + square, remove check)
    - "Qxe5!" → "Qxe5" (keep capture notation)
    - "0-0-0" → "0-0-0" (keep castling intact)

    Args:
        move_text: Raw move text like "f5+" or "Na5!"

    Returns:
        str: Clean move like "f5" or "Na5"
    """
    move_only = move_text.strip()

    # Remove common chess annotations from the END only
    # This preserves piece notation like "Na5" while removing "+"
    annotations_to_remove = [
        '!', '?', '+', '#', '!!', '??', '!?', '?!',
        '±', '∓', '∞', '†', '‡', '≠', '≡', '½',
        'μ', 'u', 'inf', '+=', '-+', '+/-',
        '↑', '↓', '→', '←', '↗', '↘', '↙', '↖',
        '⇄', '⊕', '⊖', '⊗', '⊙', '△', '▲', '▼',
        '⌚', 'N', 'up', 'down', 'ne', 'se', 'sw', 'nw',
        'exchange', 'with-idea', 'time', 'infinity', 'triangle'
    ]

    # Remove annotations from the end
    for symbol in annotations_to_remove:
        if move_only.endswith(symbol):
            move_only = move_only[:-len(symbol)]

    # Remove any remaining non-chess characters but preserve standard notation
    # Keep: letters, numbers, castling (0), captures (x), promotion (=), hyphens (-)
    valid_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789x=-'
    move_only = ''.join(c for c in move_only if c in valid_chars)

    return move_only.strip()


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


def is_solution_trigger_block(text):
    """
    Check if text block contains the solution trigger text like "Show/Hide Solution".
    """
    from config import SOLUTION_TRIGGER_TEXT
    normalized_text = normalize_text(text).strip()
    return SOLUTION_TRIGGER_TEXT.lower() in normalized_text.lower()


def find_solution_after_trigger(flattened_blocks, trigger_idx):
    """
    Find the solution block that comes after a "Show/Hide Solution" trigger block.

    Args:
        flattened_blocks: List of all blocks across pages
        trigger_idx: Index of the trigger block

    Returns:
        dict: Solution block or None if not found
    """
    # Look for the next text block after the trigger
    for idx in range(trigger_idx + 1, min(len(flattened_blocks), trigger_idx + 5)):
        block = flattened_blocks[idx]

        if block['type'] == 'text':
            # Check if this block contains a chess move
            solution_details = extract_solution_details(block['text'])
            if solution_details:
                print(
                    f"🎯 Found solution after trigger on page {block['page_number']} (distance: {idx - trigger_idx} blocks)")
                return block

    return None


def is_chessboard_like(image):
    """
    Detects if an image contains a chessboard using multiple detection strategies.
    Enhanced with size-based heuristics and improved contour analysis.
    """
    try:
        from config import ENABLE_DETAILED_LOGGING

        if ENABLE_DETAILED_LOGGING:
            print(f"🔍 Analyzing image for chessboard detection...")
            print(f"📐 Image size: {image.size if hasattr(image, 'size') else 'Unknown'}")
            print(f"📊 Image mode: {image.mode if hasattr(image, 'mode') else 'Unknown'}")

        # Strategy 1: Size-based heuristics
        # Chessboards are typically square and reasonably large
        if hasattr(image, 'size'):
            width, height = image.size
            aspect_ratio = width / height if height > 0 else 0
            size_score = 0

            # Check if image is roughly square (chessboard characteristic)
            if 0.8 <= aspect_ratio <= 1.2:
                size_score += 30
                if ENABLE_DETAILED_LOGGING:
                    print(f"✅ Size heuristic: Square-like aspect ratio {aspect_ratio:.2f} (+30 points)")

            # Check if image is reasonably large (likely chessboard size)
            if width >= 200 and height >= 200:
                size_score += 25
                if ENABLE_DETAILED_LOGGING:
                    print(f"✅ Size heuristic: Large enough {width}x{height} (+25 points)")
            elif width >= 150 and height >= 150:
                size_score += 15
                if ENABLE_DETAILED_LOGGING:
                    print(f"✅ Size heuristic: Medium size {width}x{height} (+15 points)")

            # Very likely chessboard based on size alone
            if size_score >= 45:
                if ENABLE_DETAILED_LOGGING:
                    print(f"🎯 Size-based detection: {size_score} points >= 45 = ✅ LIKELY CHESSBOARD")
                return True

        # Strategy 2: Enhanced contour analysis
        # Convert PIL image to numpy array if needed
        if isinstance(image, Image.Image):
            image_array = np.array(image)
        else:
            image_array = image

        if ENABLE_DETAILED_LOGGING:
            print(f"🔢 Array shape: {image_array.shape}")

        # Convert to grayscale
        if len(image_array.shape) == 3:
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            if ENABLE_DETAILED_LOGGING:
                print(f"🎨 Converted RGB to grayscale")
        else:
            gray = image_array
            if ENABLE_DETAILED_LOGGING:
                print(f"⚪ Image already grayscale")

        # Multiple edge detection attempts with different parameters
        contour_scores = []

        # Attempt 1: Standard parameters
        blur1 = cv2.GaussianBlur(gray, (5, 5), 0)
        edges1 = cv2.Canny(blur1, 10, 50)
        contours1, _ = cv2.findContours(edges1, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        squares1 = count_valid_squares(contours1, "Standard")
        contour_scores.append(squares1)

        # Attempt 2: More sensitive parameters
        blur2 = cv2.GaussianBlur(gray, (3, 3), 0)
        edges2 = cv2.Canny(blur2, 5, 25)
        contours2, _ = cv2.findContours(edges2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        squares2 = count_valid_squares(contours2, "Sensitive")
        contour_scores.append(squares2)

        # Attempt 3: Less sensitive but more stable
        blur3 = cv2.GaussianBlur(gray, (7, 7), 0)
        edges3 = cv2.Canny(blur3, 20, 80)
        contours3, _ = cv2.findContours(edges3, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        squares3 = count_valid_squares(contours3, "Stable")
        contour_scores.append(squares3)

        # Take the best result from all attempts
        max_squares = max(contour_scores)

        if ENABLE_DETAILED_LOGGING:
            print(f"📊 Contour analysis results: {contour_scores}")
            print(f"🏆 Best result: {max_squares} squares")

        # Strategy 3: Combined scoring
        # Lower threshold for contour detection, but combine with size heuristics
        contour_threshold = 2  # Reduced from 4

        if max_squares >= contour_threshold:
            if ENABLE_DETAILED_LOGGING:
                print(f"🎯 Contour-based detection: {max_squares} >= {contour_threshold} = ✅ CHESSBOARD")
            return True

        # Strategy 4: Fallback for very geometric images
        # If we have a perfect square image of reasonable size, it's likely a chessboard
        if hasattr(image, 'size'):
            width, height = image.size
            if width == height and width >= 200:  # Perfect square, large enough
                if ENABLE_DETAILED_LOGGING:
                    print(f"🎯 Perfect square fallback: {width}x{height} = ✅ LIKELY CHESSBOARD")
                return True

        if ENABLE_DETAILED_LOGGING:
            print(f"🏁 Final result: ❌ NOT CHESSBOARD (max squares: {max_squares}, threshold: {contour_threshold})")

        return False

    except Exception as e:
        if ENABLE_DETAILED_LOGGING:
            print(f"❌ Error in chessboard detection: {e}")
            import traceback
            traceback.print_exc()
        else:
            print(f"Error in chessboard detection: {e}")
        return False


def count_valid_squares(contours, method_name):
    """Count valid square-like shapes in contours."""
    from config import ENABLE_DETAILED_LOGGING

    squares = 0
    analyzed_contours = 0

    for cnt in contours:
        analyzed_contours += 1

        # Approximate contour to polygon
        epsilon = 0.02 * cv2.arcLength(cnt, True)  # Slightly more flexible
        approx = cv2.approxPolyDP(cnt, epsilon, True)

        # Check if it's roughly rectangular (allow 4-6 sides for more flexibility)
        if 4 <= len(approx) <= 6:
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = w / float(h) if h > 0 else 0

            # More flexible size and ratio constraints
            if 0.3 < aspect_ratio < 3.0 and w > 3 and h > 3:
                squares += 1

                if ENABLE_DETAILED_LOGGING and squares <= 5:  # Log first 5 squares
                    print(
                        f"  ✅ {method_name} Square {squares}: size {w}x{h}, ratio {aspect_ratio:.2f}, sides {len(approx)}")

    if ENABLE_DETAILED_LOGGING:
        print(f"📊 {method_name} analysis: {squares} valid squares from {analyzed_contours} contours")

    return squares


# Legacy functions for backward compatibility
def extract_solution_move(text):
    """
    Legacy function - extracts solution move in old format.
    """
    details = extract_solution_details(text)
    if details:
        return details['full_move'], details['turn']
    return None, None