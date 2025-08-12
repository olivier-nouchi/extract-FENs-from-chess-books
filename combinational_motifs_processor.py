"""
Combinational Motifs Processor
Handles 6-section grid layout, bubble analysis, and chessboard detection
"""

import os
import cv2
import numpy as np
from typing import List, Dict, Tuple
import json
from PIL import Image
import io

from config import COMBINATIONAL_MOTIFS_CONFIG
from utils import is_chessboard_like
from text_processing import extract_diagram_info


class CombinationalMotifsProcessor:
    """Processor for Combinational Motifs book format with 6-section grid layout"""
    
    def __init__(self, config: Dict = None):
        self.config = config or COMBINATIONAL_MOTIFS_CONFIG
        self.grid_config = self.config.get("grid", {})
        self.bubble_config = self.config.get("bubble_detection", {})
        self.chess_config = self.config.get("chessboard_detection", {})
        
    def divide_page_into_sections(self, page_image: np.ndarray, page_number: int = None) -> List[Dict]:
        """Divide page into 6 equal sections (3 rows x 2 columns) and analyze each section"""
        height, width = page_image.shape[:2]
        
        # Calculate section dimensions - equal division
        section_width = width // 2  # 2 columns
        section_height = height // 3  # 3 rows
        
        # Add padding to avoid cutting off content
        padding = 20  # pixels of padding
        
        sections = []
        section_number = 1
        
        for row in range(3):
            for col in range(2):
                # Calculate section coordinates with padding
                x1 = max(0, col * section_width - padding)
                y1 = max(0, row * section_height - padding)
                x2 = min(width, (col + 1) * section_width + padding)
                y2 = min(height, (row + 1) * section_height + padding)
                
                # Extract section image
                section_image = page_image[y1:y2, x1:x2]
                
                # Analyze section
                section_data = self.analyze_section(
                    section_image, section_number, row, col, (x1, y1, x2, y2), page_number
                )
                
                sections.append(section_data)
                section_number += 1
        
        return sections
    
    def detect_diagram_positions(self, page_image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect actual positions of chess diagrams on the page"""
        try:
            height, width = page_image.shape[:2]
            gray = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
            
            # Use chessboard detection to find diagram positions
            positions = []
            
            # Try different grid divisions to find the best fit
            for rows in [2, 3]:
                for cols in [2, 3]:
                    section_width = width // cols
                    section_height = height // rows
                    
                    for row in range(rows):
                        for col in range(cols):
                            x1 = col * section_width
                            y1 = row * section_height
                            x2 = x1 + section_width
                            y2 = y1 + section_height
                            
                            section_image = page_image[y1:y2, x1:x2]
                            if is_chessboard_like(section_image):
                                positions.append((x1, y1, x2, y2))
            
            # Sort positions by row, then by column
            positions.sort(key=lambda pos: (pos[1], pos[0]))
            
            return positions[:6]  # Return top 6 positions
            
        except Exception as e:
            print(f"Error detecting diagram positions: {e}")
            return []
    
    def create_sections_from_detected_positions(self, page_image: np.ndarray, 
                                              positions: List[Tuple[int, int, int, int]]) -> List[Dict]:
        """Create sections based on detected diagram positions"""
        sections = []
        height, width = page_image.shape[:2]
        
        # Sort positions by row, then by column for consistent ordering
        positions.sort(key=lambda pos: (pos[1], pos[0]))
        
        for i, (x1, y1, x2, y2) in enumerate(positions[:6]):
            section_image = page_image[y1:y2, x1:x2]
            
            # Determine row and column based on actual position
            # Calculate relative position within the page
            rel_x = x1 / width
            rel_y = y1 / height
            
            # Determine row (0 or 1)
            row = 0 if rel_y < 0.5 else 1
            
            # Determine column (0, 1, or 2)
            if rel_x < 0.33:
                col = 0
            elif rel_x < 0.67:
                col = 1
            else:
                col = 2
            
            section_data = self.analyze_section(
                section_image, i + 1, row, col, (x1, y1, x2, y2)
            )
            
            sections.append(section_data)
        
        return sections
    
    def create_equal_sections(self, page_image: np.ndarray) -> List[Dict]:
        """Create 6 equal sections (2 rows x 3 columns)"""
        height, width = page_image.shape[:2]
        
        # Calculate section dimensions - equal division
        section_width = width // 3  # 3 columns
        section_height = height // 2  # 2 rows
        
        sections = []
        section_number = 1
        
        for row in range(2):
            for col in range(3):
                # Calculate section coordinates - equal spacing
                x1 = col * section_width
                y1 = row * section_height
                x2 = x1 + section_width
                y2 = y1 + section_height
                
                # Extract section image
                section_image = page_image[y1:y2, x1:x2]
                
                # Analyze section
                section_data = self.analyze_section(
                    section_image, section_number, row, col, (x1, y1, x2, y2)
                )
                
                sections.append(section_data)
                section_number += 1
        
        return sections
    
    def analyze_section(self, section_image: np.ndarray, section_number: int, 
                       row: int, col: int, coordinates: Tuple[int, int, int, int], page_number: int = None) -> Dict:
        """Analyze a single section for chessboards, bubbles, and diagram numbers"""
        
        # Basic section info
        section_data = {
            "section_number": section_number,
            "row": row,
            "col": col,
            "coordinates": coordinates,
            "image": section_image
        }
        
        # Detect chessboard
        chessboard_result = self.detect_chessboard(section_image)
        section_data.update(chessboard_result)
        
        # Detect bubbles above the chessboard
        bubbles_result = self.detect_bubbles_above_diagram(section_image)
        section_data["bubbles_above_diagram"] = bubbles_result
        
        # Assign diagram number based on position in 3x2 grid (column-major order)
        # Left column: 1, 2, 3
        # Right column: 4, 5, 6
        # Then increment by 6 for each page
        base_number = 0
        if page_number:
            # Start from page 18 = diagrams 1-6, page 19 = diagrams 7-12, etc.
            base_number = (page_number - 18) * 6  # Adjust for starting page
            print(f"Page {page_number}: base_number = {base_number}")
        
        if col == 0:  # Left column
            if row == 0:
                diagram_number = str(base_number + 1)
            elif row == 1:
                diagram_number = str(base_number + 2)
            elif row == 2:
                diagram_number = str(base_number + 3)
        else:  # Right column
            if row == 0:
                diagram_number = str(base_number + 4)
            elif row == 1:
                diagram_number = str(base_number + 5)
            elif row == 2:
                diagram_number = str(base_number + 6)
        
        section_data["diagram_number"] = diagram_number
        
        return section_data
    
    def detect_chessboard(self, section_image: np.ndarray) -> Dict:
        """Detect chessboard in section image"""
        try:
            # Convert to grayscale for processing
            gray = cv2.cvtColor(section_image, cv2.COLOR_BGR2GRAY)
            
            # Use the chessboard detection from utils
            is_chess = is_chessboard_like(section_image)
            
            result = {
                "chessboard_detected": is_chess,
                "chessboard_confidence": 1.0 if is_chess else 0.0
            }
            
            return result
            
        except Exception as e:
            print(f"Error detecting chessboard: {e}")
            return {
                "chessboard_detected": False,
                "chessboard_confidence": 0.0
            }
    
    def detect_bubbles_above_diagram(self, section_image: np.ndarray) -> Dict:
        """Detect numbers from left to right above the chessboard diagram"""
        try:
            height, width = section_image.shape[:2]
            
            # Define the area above the chessboard (top 35% of the section)
            strip_height = int(height * 0.35)
            strip_roi = section_image[0:strip_height, :]
            
            # Convert to grayscale
            gray = cv2.cvtColor(strip_roi, cv2.COLOR_BGR2GRAY)
            
            # First, detect the diagram number (large, bold number on the left)
            diagram_number = self.detect_diagram_number_improved(gray)
            
            # Then, detect bubble numbers (circular elements with numbers inside)
            bubble_numbers = self.detect_bubble_numbers_improved(gray)
            
            # Debug output
            if bubble_numbers:
                print(f"  Detected {len(bubble_numbers)} bubbles: {[b.get('number', '?') for b in bubble_numbers]}")
            if diagram_number:
                print(f"  Detected diagram number: {diagram_number.get('number', '?')}")
            
            return {
                "count": len(bubble_numbers),
                "bubbles": bubble_numbers,
                "diagram_number": diagram_number
            }
            
        except Exception as e:
            print(f"Error detecting numbers above diagram: {e}")
            return {"count": 0, "bubbles": [], "diagram_number": None}
    
    def detect_diagram_number_improved(self, gray_image: np.ndarray) -> Dict:
        """Detect the large diagram number on the left side - improved approach"""
        try:
            # Look for large, bold numbers on the left side (first 25% of width)
            left_region = gray_image[:, :gray_image.shape[1]//4]
            
            # Apply preprocessing specifically for large text
            processed_images = [
                (left_region, cv2.THRESH_BINARY),
                (cv2.GaussianBlur(left_region, (3, 3), 0), cv2.THRESH_BINARY),
                (cv2.adaptiveThreshold(left_region, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2), cv2.THRESH_BINARY)
            ]
            
            best_number = None
            best_confidence = 0
            
            for processed_img, threshold_type in processed_images:
                # Apply thresholds for dark text
                thresholds = [(80, 255, cv2.THRESH_BINARY), (120, 255, cv2.THRESH_BINARY)]
                
                for threshold_val, max_val, thresh_type in thresholds:
                    _, thresh = cv2.threshold(processed_img, threshold_val, max_val, thresh_type)
                    
                    # Apply morphological operations to connect text
                    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
                    
                    # Find contours
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    for contour in contours:
                        area = cv2.contourArea(contour)
                        
                        # Look for larger numbers (diagram numbers are bigger and bolder)
                        if 150 < area < 1200:
                            x, y, w, h = cv2.boundingRect(contour)
                            
                            # Check aspect ratio for numbers
                            aspect_ratio = w / h
                            if 0.2 < aspect_ratio < 2.5:
                                # Extract ROI for number detection
                                roi = gray_image[y:y+h, x:x+w]
                                
                                # Detect the number
                                number = self.extract_single_number_enhanced(roi, True)  # Dark text
                                if number and number in "0123456789":
                                    confidence = self.calculate_confidence(roi, number)
                                    # Bonus confidence for larger numbers (diagram numbers are bigger)
                                    if area > 300:
                                        confidence *= 1.5
                                    if confidence > best_confidence:
                                        best_confidence = confidence
                                        best_number = {
                                            "x": x,
                                            "y": y,
                                            "number": number,
                                            "background_color": "white",
                                            "text_color": "black",
                                            "area": area,
                                            "width": w,
                                            "height": h,
                                            "confidence": confidence
                                        }
            
            return best_number
            
        except Exception as e:
            print(f"Error detecting diagram number: {e}")
            return None
    
    def detect_bubble_numbers_improved(self, gray_image: np.ndarray) -> List[Dict]:
        """Detect circular bubbles with numbers inside - improved approach"""
        try:
            bubble_numbers = []
            
            # Focus on the right side of the image (after the diagram number)
            right_region = gray_image[:, gray_image.shape[1]//4:]
            
            # Apply multiple preprocessing steps
            processed_images = [
                (right_region, cv2.THRESH_BINARY),
                (cv2.GaussianBlur(right_region, (3, 3), 0), cv2.THRESH_BINARY),
                (cv2.adaptiveThreshold(right_region, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2), cv2.THRESH_BINARY),
                (cv2.adaptiveThreshold(right_region, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2), cv2.THRESH_BINARY_INV),
                (cv2.adaptiveThreshold(right_region, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2), cv2.THRESH_BINARY),
                (cv2.adaptiveThreshold(right_region, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 11, 2), cv2.THRESH_BINARY_INV)
            ]
            
            for processed_img, threshold_type in processed_images:
                # Apply multiple thresholds to find both dark and light text
                thresholds = [
                    (60, 255, cv2.THRESH_BINARY),      # Dark text on light background (white bubbles)
                    (100, 255, cv2.THRESH_BINARY),     # Dark text on light background (more sensitive)
                    (140, 255, cv2.THRESH_BINARY_INV), # Light text on dark background (black bubbles)
                    (180, 255, cv2.THRESH_BINARY_INV), # Light text on dark background (more sensitive)
                ]
                
                for threshold_val, max_val, thresh_type in thresholds:
                    # Apply threshold
                    _, thresh = cv2.threshold(processed_img, threshold_val, max_val, thresh_type)
                    
                    # Apply morphological operations to clean up the image
                    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
                    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
                    
                    # Find contours
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    for contour in contours:
                        area = cv2.contourArea(contour)
                        
                        # Filter for bubble-sized contours (smaller than diagram numbers)
                        if 30 < area < 500:
                            x, y, w, h = cv2.boundingRect(contour)
                            
                            # Check if contour is roughly circular (bubble characteristic)
                            perimeter = cv2.arcLength(contour, True)
                            if perimeter > 0:
                                circularity = 4 * np.pi * area / (perimeter * perimeter)
                                
                                # Check aspect ratio for numbers
                                aspect_ratio = w / h
                                if 0.3 < aspect_ratio < 2.0 and circularity > 0.2:  # More lenient
                                    # Extract ROI for number detection
                                    roi = gray_image[y:y+h, x + gray_image.shape[1]//4:x+w + gray_image.shape[1]//4]
                                    
                                    # Determine if this is dark text on light background or vice versa
                                    is_dark_text = thresh_type == cv2.THRESH_BINARY
                                    
                                    # Detect the number with multiple methods
                                    number = self.extract_single_number_enhanced(roi, is_dark_text)
                                    if number and number != "?" and number in "0123456789":
                                        # Determine bubble color based on text color
                                        bubble_color = "white" if is_dark_text else "black"
                                        
                                        # Additional filtering: check if the number is in a reasonable position
                                        if y > 5 and y < gray_image.shape[0] - 10:
                                            bubble_numbers.append({
                                                "x": x + gray_image.shape[1]//4,  # Adjust x coordinate
                                                "y": y,
                                                "number": number,
                                                "background_color": bubble_color,
                                                "text_color": "black" if is_dark_text else "white",
                                                "area": area,
                                                "width": w,
                                                "height": h,
                                                "confidence": self.calculate_confidence(roi, number),
                                                "circularity": circularity
                                            })
            
            # Remove duplicates based on position and keep only the best candidates
            unique_bubbles = []
            for bubble_info in bubble_numbers:
                is_duplicate = False
                for existing in unique_bubbles:
                    if abs(bubble_info['x'] - existing['x']) < 25:  # More lenient
                        # If we have a duplicate, keep the one with higher confidence
                        if bubble_info['confidence'] > existing['confidence']:
                            unique_bubbles.remove(existing)
                            unique_bubbles.append(bubble_info)
                        is_duplicate = True
                        break
                if not is_duplicate:
                    unique_bubbles.append(bubble_info)
            
            # Sort by x-coordinate and limit to max 2 bubbles
            unique_bubbles.sort(key=lambda n: n['x'])
            
            # Only keep the first 2 bubbles
            if len(unique_bubbles) > 2:
                unique_bubbles = unique_bubbles[:2]
            
            return unique_bubbles
            
        except Exception as e:
            print(f"Error detecting bubble numbers: {e}")
            return []
    
    def extract_all_numbers_simple(self, gray_image: np.ndarray) -> List[Dict]:
        """Extract all numbers from the image with their colors - improved approach"""
        try:
            numbers_found = []
            
            # Apply multiple preprocessing steps
            processed_images = self.preprocess_for_text_detection(gray_image)
            
            for processed_img, threshold_type in processed_images:
                # Apply multiple thresholds to find both dark and light text
                thresholds = [
                    (80, 255, cv2.THRESH_BINARY),      # Dark text on light background
                    (120, 255, cv2.THRESH_BINARY),     # Dark text on light background (more sensitive)
                    (160, 255, cv2.THRESH_BINARY_INV), # Light text on dark background
                    (200, 255, cv2.THRESH_BINARY_INV)  # Light text on dark background (more sensitive)
                ]
                
                for threshold_val, max_val, thresh_type in thresholds:
                    # Apply threshold
                    _, thresh = cv2.threshold(processed_img, threshold_val, max_val, thresh_type)
                    
                    # Apply morphological operations to clean up the image
                    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
                    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
                    
                    # Find contours
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    for contour in contours:
                        area = cv2.contourArea(contour)
                        
                        # Filter for text-sized contours
                        if 40 < area < 800:
                            x, y, w, h = cv2.boundingRect(contour)
                            
                            # Check aspect ratio for numbers
                            aspect_ratio = w / h
                            if 0.2 < aspect_ratio < 2.5:
                                # Extract ROI for number detection
                                roi = gray_image[y:y+h, x:x+w]
                                
                                # Determine if this is dark text on light background or vice versa
                                is_dark_text = thresh_type == cv2.THRESH_BINARY
                                
                                # Detect the number with multiple methods
                                number = self.extract_single_number_enhanced(roi, is_dark_text)
                                if number and number != "?" and number in "0123456789":
                                    # Determine bubble color based on text color
                                    bubble_color = "white" if is_dark_text else "black"
                                    
                                    # Additional filtering: check if the number is in a reasonable position
                                    if x > 5 and y > 5:
                                        numbers_found.append({
                                            "x": x,
                                            "y": y,
                                            "number": number,
                                            "background_color": bubble_color,
                                            "text_color": "black" if is_dark_text else "white",
                                            "area": area,
                                            "width": w,
                                            "height": h,
                                            "confidence": self.calculate_confidence(roi, number)
                                        })
            
            # Remove duplicates based on position and keep only the best candidates
            unique_numbers = []
            for number_info in numbers_found:
                is_duplicate = False
                for existing in unique_numbers:
                    if abs(number_info['x'] - existing['x']) < 25:
                        # If we have a duplicate, keep the one with higher confidence
                        if number_info['confidence'] > existing['confidence']:
                            unique_numbers.remove(existing)
                            unique_numbers.append(number_info)
                        is_duplicate = True
                        break
                if not is_duplicate:
                    unique_numbers.append(number_info)
            
            # Sort by x-coordinate and limit to reasonable number of results
            unique_numbers.sort(key=lambda n: n['x'])
            
            # Only keep the first few numbers (diagram number + max 2 bubbles)
            if len(unique_numbers) > 3:
                unique_numbers = unique_numbers[:3]
            
            return unique_numbers
            
        except Exception as e:
            print(f"Error extracting all numbers: {e}")
            return []
    
    def preprocess_for_text_detection(self, gray_image: np.ndarray) -> List[Tuple[np.ndarray, int]]:
        """Preprocess image for better text detection"""
        processed_images = []
        
        # Original image
        processed_images.append((gray_image, cv2.THRESH_BINARY))
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray_image, (3, 3), 0)
        processed_images.append((blurred, cv2.THRESH_BINARY))
        
        # Apply adaptive thresholding
        adaptive_thresh = cv2.adaptiveThreshold(gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        processed_images.append((adaptive_thresh, cv2.THRESH_BINARY))
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray_image)
        processed_images.append((enhanced, cv2.THRESH_BINARY))
        
        return processed_images
    
    def extract_single_number_enhanced(self, roi: np.ndarray, is_dark_text: bool) -> str:
        """Extract a single number from ROI - enhanced approach"""
        try:
            # Resize for consistent processing
            resized = cv2.resize(roi, (30, 40))
            
            # Apply threshold based on text type
            if is_dark_text:
                # For dark text, look for dark pixels
                _, thresh = cv2.threshold(resized, 127, 255, cv2.THRESH_BINARY)
            else:
                # For light text, look for light pixels
                _, thresh = cv2.threshold(resized, 127, 255, cv2.THRESH_BINARY_INV)
            
            # Count white pixels (the digit)
            white_pixels = np.sum(thresh == 255)
            total_pixels = thresh.size
            
            # If there's not enough content, return None
            if white_pixels / total_pixels < 0.03:
                return None
            
            # Try multiple digit recognition methods
            number = self.enhanced_digit_recognition(thresh)
            if number and number in "0123456789":
                return number
            
            # Fallback to template matching
            number = self.template_matching_enhanced(thresh)
            if number and number in "0123456789":
                return number
            
            return None
            
        except Exception as e:
            print(f"Error extracting single number: {e}")
            return None
    
    def enhanced_digit_recognition(self, digit_img: np.ndarray) -> str:
        """Enhanced digit recognition using multiple pattern analysis methods"""
        try:
            height, width = digit_img.shape
            
            # Define more precise regions
            top_quarter = digit_img[0:height//4, :]
            upper_middle = digit_img[height//4:height//2, :]
            lower_middle = digit_img[height//2:3*height//4, :]
            bottom_quarter = digit_img[3*height//4:, :]
            
            left_quarter = digit_img[:, 0:width//4]
            left_middle = digit_img[:, width//4:width//2]
            right_middle = digit_img[:, width//2:3*width//4]
            right_quarter = digit_img[:, 3*width//4:]
            
            # Calculate densities
            top_density = np.sum(top_quarter == 255) / top_quarter.size
            upper_middle_density = np.sum(upper_middle == 255) / upper_middle.size
            lower_middle_density = np.sum(lower_middle == 255) / lower_middle.size
            bottom_density = np.sum(bottom_quarter == 255) / bottom_quarter.size
            
            left_density = np.sum(left_quarter == 255) / left_quarter.size
            left_middle_density = np.sum(left_middle == 255) / left_middle.size
            right_middle_density = np.sum(right_middle == 255) / right_middle.size
            right_density = np.sum(right_quarter == 255) / right_quarter.size
            
            # Enhanced classification logic
            if left_middle_density > 0.5 and top_density < 0.15 and bottom_density < 0.15:
                return "1"  # Strong vertical line
            elif top_density > 0.4 and bottom_density > 0.4 and upper_middle_density < 0.1:
                return "2"  # Top and bottom curves
            elif top_density > 0.3 and upper_middle_density > 0.3 and lower_middle_density > 0.3 and bottom_density > 0.3:
                return "3"  # Four horizontal segments
            elif left_middle_density > 0.4 and lower_middle_density > 0.4 and bottom_density < 0.1:
                return "4"  # Vertical and middle horizontal
            elif top_density > 0.3 and lower_middle_density > 0.2 and bottom_density > 0.3:
                return "5"  # Top, middle, bottom
            elif left_middle_density > 0.4 and top_density > 0.3 and lower_middle_density > 0.3 and bottom_density > 0.3:
                return "6"  # Vertical and three horizontal
            elif top_density > 0.4 and upper_middle_density < 0.05 and lower_middle_density < 0.05:
                return "7"  # Top horizontal only
            elif top_density > 0.3 and upper_middle_density > 0.3 and lower_middle_density > 0.3 and bottom_density > 0.3 and left_middle_density > 0.3:
                return "8"  # All segments
            elif top_density > 0.3 and upper_middle_density > 0.3 and lower_middle_density > 0.3 and bottom_density > 0.3 and left_middle_density > 0.3:
                return "9"  # Similar to 8
            elif top_density > 0.3 and bottom_density > 0.3 and left_middle_density > 0.3 and right_middle_density > 0.3:
                return "0"  # Oval shape
            
            return None
            
        except Exception as e:
            print(f"Error in enhanced digit recognition: {e}")
            return None
    
    def template_matching_enhanced(self, digit_img: np.ndarray) -> str:
        """Enhanced template matching for digit recognition"""
        try:
            # Define enhanced templates for each digit
            templates = {
                "1": np.array([[0, 0, 1, 0, 0],
                              [0, 0, 1, 0, 0],
                              [0, 0, 1, 0, 0],
                              [0, 0, 1, 0, 0],
                              [0, 0, 1, 0, 0]]),
                "2": np.array([[1, 1, 1, 1, 1],
                              [0, 0, 0, 0, 1],
                              [1, 1, 1, 1, 1],
                              [1, 0, 0, 0, 0],
                              [1, 1, 1, 1, 1]]),
                "3": np.array([[1, 1, 1, 1, 1],
                              [0, 0, 0, 0, 1],
                              [1, 1, 1, 1, 1],
                              [0, 0, 0, 0, 1],
                              [1, 1, 1, 1, 1]]),
                "4": np.array([[1, 0, 0, 0, 1],
                              [1, 0, 0, 0, 1],
                              [1, 1, 1, 1, 1],
                              [0, 0, 0, 0, 1],
                              [0, 0, 0, 0, 1]]),
                "5": np.array([[1, 1, 1, 1, 1],
                              [1, 0, 0, 0, 0],
                              [1, 1, 1, 1, 1],
                              [0, 0, 0, 0, 1],
                              [1, 1, 1, 1, 1]]),
                "6": np.array([[1, 1, 1, 1, 1],
                              [1, 0, 0, 0, 0],
                              [1, 1, 1, 1, 1],
                              [1, 0, 0, 0, 1],
                              [1, 1, 1, 1, 1]]),
                "7": np.array([[1, 1, 1, 1, 1],
                              [0, 0, 0, 0, 1],
                              [0, 0, 0, 1, 0],
                              [0, 0, 1, 0, 0],
                              [0, 1, 0, 0, 0]]),
                "8": np.array([[1, 1, 1, 1, 1],
                              [1, 0, 0, 0, 1],
                              [1, 1, 1, 1, 1],
                              [1, 0, 0, 0, 1],
                              [1, 1, 1, 1, 1]]),
                "9": np.array([[1, 1, 1, 1, 1],
                              [1, 0, 0, 0, 1],
                              [1, 1, 1, 1, 1],
                              [0, 0, 0, 0, 1],
                              [1, 1, 1, 1, 1]]),
                "0": np.array([[1, 1, 1, 1, 1],
                              [1, 0, 0, 0, 1],
                              [1, 0, 0, 0, 1],
                              [1, 0, 0, 0, 1],
                              [1, 1, 1, 1, 1]])
            }
            
            # Resize digit image to 5x5 for template matching
            resized = cv2.resize(digit_img, (5, 5))
            
            # Convert to binary
            _, binary = cv2.threshold(resized, 127, 1, cv2.THRESH_BINARY)
            
            best_match = None
            best_score = 0
            
            for digit, template in templates.items():
                # Calculate correlation
                correlation = np.sum(binary * template)
                if correlation > best_score:
                    best_score = correlation
                    best_match = digit
            
            # Only return if we have a good match
            if best_score > 8:
                return best_match
            
            return None
            
        except Exception as e:
            print(f"Error in template matching: {e}")
            return None
    
    def calculate_confidence(self, roi: np.ndarray, number: str) -> float:
        """Calculate confidence score for the detected number"""
        try:
            # Resize for analysis
            resized = cv2.resize(roi, (20, 30))
            
            # Apply threshold
            _, thresh = cv2.threshold(resized, 127, 255, cv2.THRESH_BINARY)
            
            # Count white pixels
            white_pixels = np.sum(thresh == 255)
            total_pixels = thresh.size
            
            # Base confidence on pixel density
            density = white_pixels / total_pixels
            
            # Additional confidence based on number characteristics
            if number == "1":
                # Check for vertical line pattern
                center_col = thresh[:, thresh.shape[1]//2-1:thresh.shape[1]//2+1]
                center_density = np.sum(center_col == 255) / center_col.size
                return density * center_density
            elif number in "0235689":
                # Check for closed shapes
                return density * 1.2
            else:
                return density
            
        except Exception as e:
            return 0.5  # Default confidence
    
    def process_page(self, page_image: np.ndarray, page_number: int) -> List[Dict]:
        """Process a single page and return all sections with analysis"""
        sections = self.divide_page_into_sections(page_image, page_number)
        
        # Add page information
        for section in sections:
            section["page_number"] = page_number
        
        return sections
    
    def save_section_images(self, sections: List[Dict], output_dir: str, page_number: int):
        """Save individual section images for debugging"""
        try:
            page_dir = os.path.join(output_dir, f"page_{page_number}")
            os.makedirs(page_dir, exist_ok=True)
            
            for section in sections:
                section_num = section["section_number"]
                filename = f"section_{section_num}.png"
                filepath = os.path.join(page_dir, filename)
                
                cv2.imwrite(filepath, section["image"])
                
        except Exception as e:
            print(f"Error saving section images: {e}")
    
    def format_output_row(self, section: Dict, page_number: int) -> Dict:
        """Format a section into a CSV row"""
        bubbles_info = section.get("bubbles_above_diagram", {})
        bubbles = bubbles_info.get("bubbles", [])
        detected_diagram_number = bubbles_info.get("diagram_number")
        
        # Debug output
        print(f"    Formatting section: bubbles_info={bubbles_info}")
        print(f"    Bubbles found: {len(bubbles)}")
        print(f"    Diagram number: {detected_diagram_number}")
        
        # Extract bubble information
        bubble_numbers = []
        bubble_colors = []
        bubble_details = []
        
        for bubble in bubbles:
            if isinstance(bubble, dict):
                bubble_numbers.append(bubble.get("number", ""))
                bubble_colors.append(bubble.get("background_color", ""))
                bubble_details.append(f"{bubble.get('number', '')}_{bubble.get('background_color', '')}")
        
        # Extract diagram number properly
        if detected_diagram_number and isinstance(detected_diagram_number, dict):
            diagram_number = detected_diagram_number.get("number", "")
        else:
            diagram_number = section.get("diagram_number", "")
        
        result = {
            "page_number": page_number,
            "section_number": section.get("section_number", ""),
            "row": section.get("row", ""),
            "col": section.get("col", ""),
            "chessboard_detected": section.get("chessboard_detected", False),
            "chessboard_confidence": section.get("chessboard_confidence", 0.0),
            "bubble_count": bubbles_info.get("count", 0),
            "bubble_numbers": ",".join(bubble_numbers),
            "bubble_colors": ",".join(bubble_colors),
            "bubble_details": ",".join(bubble_details),
            "detected_diagram_number": diagram_number,
            "calculated_diagram_number": section.get("diagram_number", ""),
            "coordinates": f"{section.get('coordinates', (0,0,0,0))}"
        }
        
        print(f"    Result: bubble_count={result['bubble_count']}, bubble_numbers='{result['bubble_numbers']}'")
        
        return result


def create_combinational_motifs_processor(config: Dict = None) -> CombinationalMotifsProcessor:
    """Factory function to create a CombinationalMotifsProcessor instance"""
    return CombinationalMotifsProcessor(config)


if __name__ == "__main__":
    # Test the processor
    processor = create_combinational_motifs_processor()
    print("Combinational Motifs Processor created successfully!") 