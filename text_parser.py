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


import re
import cv2
import numpy as np
from PIL import Image


def normalize_text(text):
    """
    Cleans OCR symbols and chess notation from text.
    """
    replacements = {
        '♔': 'K', '♕': 'Q', '♖': 'R', '♗': 'B', '♘': 'N', '♙': '',
        '♚': 'k', '♛': 'q', '♜': 'r', '♝': 'b', '♞': 'n', '♟': '',
        '†': '', '‡': '', '±': '+=', '→': '', 'ƒ': '+=', '=': '=',
        '≠': '+=', '≡': '+=', '\u2026': '...', '…': '...',
        '"': '"', '"': '"', ''': "'", ''': "'",
        # Add more chess symbols as needed
        '½': '1/2', '–': '-', '—': '-'
    }

    for symbol, replacement in replacements.items():
        text = text.replace(symbol, replacement)

    return text.strip()


def extract_players_and_year(text):
    """
    Extracts diagram number, players and year from strings like:
    '15. Alekhine – Cohn, Karlovy Vary 1911'

    Returns:
        tuple: (diagram_number, players_string, year)
    """
    # Try different patterns for player extraction
    patterns = [
        r'(?:(\d+)\.\s*)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[–-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)(?:,.*?)?(\d{4})',
        r'(?:(\d+)\.\s*)?([A-Z][a-z]+.*?)\s+[–-]\s+([A-Z][a-z]+.*?)(?:,.*?)?(\d{4})',
        r'(\d+)\.\s*([^–-]+)[–-]([^,]+),.*?(\d{4})'
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            if len(groups) >= 4:
                diagram_number = groups[0]
                white = groups[1].strip()
                black = groups[2].strip()
                year = groups[3]
                return diagram_number, f"{white} - {black}", year

    # Fallback: try to extract just year
    year_match = re.search(r'(\d{4})', text)
    year = year_match.group(1) if year_match else None

    # Try to extract diagram number
    diagram_match = re.search(r'^(\d+)\.', text.strip())
    diagram_number = diagram_match.group(1) if diagram_match else None

    return diagram_number, None, year


def extract_solution_move(text):
    """
    Extracts the first chess move from a solution block.

    Returns:
        tuple: (move, turn) where turn is 'white' or 'black'
    """
    # Pattern for chess moves: number followed by dots and move
    move_patterns = [
        r'(\d+)(\.{3})\s*([a-hRNBQKO0-9][^\s\.,!?]*[!?]?)',  # Black moves with ...
        r'(\d+)(\.)\s*([a-hRNBQKO0-9][^\s\.,!?]*[!?]?)',  # White moves with .
    ]

    for pattern in move_patterns:
        match = re.search(pattern, text)
        if match:
            move_number = match.group(1)
            dots = match.group(2)
            move = match.group(3)

            # Clean up the move notation
            move = move.rstrip('.,!? ')

            turn = 'black' if '...' in dots else 'white'
            return f"{move_number}{dots} {move}", turn

    # Fallback: look for any chess-like move
    simple_move = re.search(r'\b([a-hRNBQKO0-9]+[a-h1-8]*[+#!?]*)\b', text)
    if simple_move:
        return simple_move.group(1), None

    return None, None


def extract_diagram_info(text_blocks):
    """
    Extracts diagram information from a sequence of text blocks.

    Args:
        text_blocks: List of text blocks around a diagram

    Returns:
        dict: Contains diagram_number, players, year, solution_move, etc.
    """
    info = {
        'diagram_number': None,
        'players': None,
        'year': None,
        'solution_move': None,
        'solution_turn': None
    }

    # Process all text blocks to find relevant information
    for block in text_blocks:
        if block['type'] != 'text':
            continue

        text = normalize_text(block['text'])

        # Try to extract players and year
        if not info['players'] or not info['year']:
            diagram_num, players, year = extract_players_and_year(text)
            if players:
                info['players'] = players
            if year:
                info['year'] = year
            if diagram_num:
                info['diagram_number'] = diagram_num

        # Try to extract solution move
        if not info['solution_move']:
            move, turn = extract_solution_move(text)
            if move:
                info['solution_move'] = move
                info['solution_turn'] = turn

    return info