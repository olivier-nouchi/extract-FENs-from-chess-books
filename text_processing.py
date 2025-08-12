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
        location = match.group(4).strip()  # Not used but captured
        year = match.group(5)
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
    Simple chessboard detection: Square dimensions + ~65 KB file size.
    """
    try:
        import io

        # Get image dimensions
        width, height = image.size if hasattr(image, 'size') else (0, 0)
        
        # Quick rejection for obviously wrong images
        if width < 50 or height < 50:
            return False

        # Check if image is square
        if width != height:
            return False

        # Check if size is reasonable for chessboard (200-400px)
        if not (200 <= width <= 400):
            return False

        # Check file size (~65 KB)
        try:
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG', optimize=True)
            file_size_kb = len(img_buffer.getvalue()) / 1024
            
            # Accept if file size is around 65 KB (allow some variance)
            if 50 <= file_size_kb <= 80:
                print(f"✅ Chessboard detected: {width}x{width} pixels, {file_size_kb:.1f} KB")
                return True
            else:
                print(f"❌ Wrong file size: {width}x{width} pixels, {file_size_kb:.1f} KB (expected ~65 KB)")
                return False
                
        except Exception as e:
            print(f"⚠️ Could not check file size: {e}")
            return False

    except Exception as e:
        print(f"❌ Error in chessboard detection: {e}")
        return False


def analyze_chessboard_patterns(gray_image, width, height):
    """
    Analyze image for chessboard-specific visual patterns.
    Looks for grid patterns, alternating squares, and chess piece characteristics.
    
    Args:
        gray_image: Grayscale numpy array
        width, height: Image dimensions
        
    Returns:
        int: Pattern score (0-100)
    """
    try:
        pattern_score = 0
        print(f"🔍 Pattern analysis for {width}x{height} image...")
        
        # Strategy 1: Grid pattern detection
        # Look for horizontal and vertical lines that form a grid
        edges_h = cv2.Sobel(gray_image, cv2.CV_64F, 0, 1, ksize=3)
        edges_v = cv2.Sobel(gray_image, cv2.CV_64F, 1, 0, ksize=3)
        
        # Count strong horizontal and vertical edges
        h_edges = np.sum(np.abs(edges_h) > 50)
        v_edges = np.sum(np.abs(edges_v) > 50)
        
        # Chessboards should have strong grid patterns
        if h_edges > width * 2 and v_edges > height * 2:
            pattern_score += 25
            print(f"✅ Grid pattern detected: {h_edges} horizontal, {v_edges} vertical edges (+25 points)")
        
        # Strategy 2: Check for alternating square patterns
        # Sample the image in a grid pattern to look for alternating light/dark squares
        grid_size = 8  # 8x8 chessboard
        cell_w, cell_h = width // grid_size, height // grid_size
        
        if cell_w > 5 and cell_h > 5:  # Ensure cells are large enough to analyze
            alternating_score = 0
            total_checks = 0
            
            for i in range(grid_size - 1):
                for j in range(grid_size - 1):
                    # Get average brightness of adjacent cells
                    cell1 = gray_image[j*cell_h:(j+1)*cell_h, i*cell_w:(i+1)*cell_w]
                    cell2 = gray_image[j*cell_h:(j+1)*cell_h, (i+1)*cell_w:(i+2)*cell_w]
                    cell3 = gray_image[(j+1)*cell_h:(j+2)*cell_h, i*cell_w:(i+1)*cell_w]
                    
                    if cell1.size > 0 and cell2.size > 0 and cell3.size > 0:
                        avg1 = np.mean(cell1)
                        avg2 = np.mean(cell2)
                        avg3 = np.mean(cell3)
                        
                        # Check if we have alternating pattern (light/dark/light or dark/light/dark)
                        if (avg1 > avg2 and avg2 < avg3) or (avg1 < avg2 and avg2 > avg3):
                            alternating_score += 1
                        total_checks += 1
            
            if total_checks > 0:
                alternating_ratio = alternating_score / total_checks
                if alternating_ratio > 0.6:  # At least 60% of cells show alternating pattern
                    pattern_score += 30
                    print(f"✅ Alternating square pattern detected: {alternating_ratio:.2f} ratio (+30 points)")
        
        # Strategy 3: Check for chess piece characteristics
        # Look for small, distinct objects that could be chess pieces
        # Use morphological operations to find small connected components
        kernel = np.ones((3,3), np.uint8)
        dilated = cv2.dilate(gray_image, kernel, iterations=1)
        eroded = cv2.erode(gray_image, kernel, iterations=1)
        piece_candidates = dilated - eroded
        
        # Count distinct small objects
        _, labels, stats, _ = cv2.connectedComponentsWithStats(piece_candidates.astype(np.uint8))
        
        # Look for objects of reasonable size for chess pieces
        piece_count = 0
        for stat in stats[1:]:  # Skip background
            area = stat[4]
            if 20 < area < 200:  # Reasonable size for chess pieces
                piece_count += 1
        
        if 10 <= piece_count <= 32:  # Reasonable number of chess pieces
            pattern_score += 25
            print(f"✅ Chess piece candidates detected: {piece_count} pieces (+25 points)")
        
        # Strategy 4: Check for board coordinates (a-h, 1-8)
        # This is more complex and would require OCR, but we can look for text-like patterns
        # For now, we'll use a simpler approach based on edge density in border areas
        
        # Check if there are text-like patterns in the border areas
        border_thickness = min(width, height) // 20
        top_border = gray_image[:border_thickness, :]
        left_border = gray_image[:, :border_thickness]
        
        # High edge density in borders might indicate coordinates
        top_edges = np.sum(cv2.Canny(top_border, 50, 150)) / top_border.size
        left_edges = np.sum(cv2.Canny(left_border, 50, 150)) / left_border.size
        
        if top_edges > 0.1 or left_edges > 0.1:  # Significant edge density in borders
            pattern_score += 20
            print(f"✅ Border patterns detected (possible coordinates) (+20 points)")
        
        return pattern_score
        
    except Exception as e:
        print(f"⚠️ Error in pattern analysis: {e}")
        return 0


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