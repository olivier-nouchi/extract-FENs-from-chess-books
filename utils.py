import cv2
import numpy as np
import re


def is_chessboard_like(image):
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 10, 50)
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    squares = 0
    for cnt in contours:
        approx = cv2.approxPolyDP(cnt, 0.03 * cv2.arcLength(cnt, True), True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            ar = w / float(h)
            if 0.4 < ar < 1.8 and w > 5 and h > 5:
                squares += 1
    return squares >= 4


def normalize_text(text):
    replacements = {
        '♔': 'K', '♕': 'Q', '♖': 'R', '♗': 'B', '♘': 'N', '♙': '',
        '♚': 'k', '♛': 'q', '♜': 'r', '♝': 'b', '♞': 'n', '♟': '',
        '†': '', '‡': '', '±': '+=', '→': '', 'ƒ': '+=', '=': '=',
        '≠': '+=', '≡': '+=', '\u2026': '...', '…': '...', '“': '"', '”': '"', '‘': "'", '’': "'"
    }
    for symbol, replacement in replacements.items():
        text = text.replace(symbol, replacement)
    return text


def extract_players_and_year(text):
    """Extracts players and year from strings like '15. Alekhine – Cohn, Karlovy Vary 1911'"""
    match = re.search(r'(?:(\d+)\.\s*)?([A-Z][a-z]+.*?)\s+–\s+([A-Z][a-z]+.*?),.*?(\d{4})', text)
    if match:
        diagram_number = match.group(1)
        white = match.group(2).strip()
        black = match.group(3).strip()
        year = match.group(4)
        return diagram_number, f"{white} - {black}", year
    return None, None, None


def extract_solution_move(text):
    """Extracts the first move (with or without ... for Black) from a solution block"""
    match = re.search(r'(\d+)(\.{1,3})\s*([a-hRNBQKO0-9][^\s]*)', text)
    if match:
        move_prefix = match.group(2)
        move = match.group(3)
        return move, ('black' if '...' in move_prefix else 'white')
    return None, None
