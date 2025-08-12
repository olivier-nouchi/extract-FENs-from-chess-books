"""
Main script for processing Combinational Motifs book
Handles 6-section grid layout, bubble analysis, and FEN extraction
"""

import os
import sys
import csv
import fitz  # PyMuPDF
import cv2
import numpy as np
from typing import List, Dict
import json
from PIL import Image

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import COMBINATIONAL_MOTIFS_CONFIG
from combinational_motifs_processor import create_combinational_motifs_processor
# from chessvision_api import send_image_to_chessvision  # Deactivated


class CombinationalMotifsExtractor:
    """Main extractor for Combinational Motifs book format with bubble detection"""
    
    def __init__(self, pdf_path: str, config: Dict = None):
        self.pdf_path = pdf_path
        self.config = config or COMBINATIONAL_MOTIFS_CONFIG
        self.processor = create_combinational_motifs_processor(config)
        
        # Create output directories
        self.output_dir = "data_output"
        self.images_dir = os.path.join(self.output_dir, "extracted_images")
        self.sections_dir = os.path.join(self.output_dir, "section_images")
        
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.sections_dir, exist_ok=True)
        
        # Generate output CSV filename
        self.output_csv = self._generate_output_filename()
        
    def _generate_output_filename(self) -> str:
        """Generate output CSV filename based on input PDF name"""
        pdf_filename = os.path.splitext(os.path.basename(self.pdf_path))[0]
        clean_filename = "".join(c for c in pdf_filename if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_filename = clean_filename.replace(' ', '_')
        return f"{self.output_dir}/combinational_motifs_bubbles_{clean_filename}.csv"
    
    def extract_page_image(self, page) -> np.ndarray:
        """Extract image from PDF page"""
        # Get page matrix for rendering
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
        
        # Render page to pixmap
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to numpy array
        img_data = pix.tobytes("png")
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return img
    
    def process_pdf(self, start_page: int = None, end_page: int = None) -> List[Dict]:
        """Process the entire PDF and extract all sections with bubble information"""
        
        # Open PDF
        doc = fitz.open(self.pdf_path)
        
        # Determine page range
        if start_page is None:
            start_page = 0
        if end_page is None:
            end_page = len(doc) - 1
        
        all_sections = []
        page_count = 0
        
        print(f"Processing Combinational Motifs PDF: {self.pdf_path}")
        print(f"Page range: {start_page} to {end_page}")
        print(f"Total pages to process: {end_page - start_page + 1}")
        print("Extracting bubble information from chess diagrams...")
        
        for page_num in range(start_page, end_page + 1):
            try:
                page = doc[page_num]
                print(f"Processing page {page_num + 1}...")
                
                # Extract page image
                page_image = self.extract_page_image(page)
                
                # Process page with 6-section grid and bubble detection
                sections = self.processor.process_page(page_image, page_num + 1)
                
                # Save section images for debugging
                self.processor.save_section_images(sections, self.sections_dir, page_num + 1)
                
                # Format sections for output
                formatted_sections = []
                for section in sections:
                    formatted_section = self.processor.format_output_row(section, page_num + 1)
                    formatted_sections.append(formatted_section)
                
                # Save CSV after each page (append mode after first page)
                if page_count == 0:
                    self.save_to_csv(formatted_sections, self.output_csv)
                else:
                    self.append_to_csv(formatted_sections, self.output_csv)
                
                all_sections.extend(formatted_sections)
                page_count += 1
                
                # Print bubble detection results for this page
                bubble_count = sum(s.get("bubble_count", 0) for s in sections)
                print(f"  Found {len(sections)} chess diagrams, {bubble_count} bubbles detected")
                print(f"  Progress: {page_count}/{end_page - start_page + 1} pages completed")
                
            except Exception as e:
                print(f"Error processing page {page_num + 1}: {e}")
                continue
        
        doc.close()
        
        print(f"\nTotal sections extracted: {len(all_sections)}")
        return all_sections
    
    def save_to_csv(self, sections: List[Dict], filename: str):
        """Save sections to CSV file"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    "page_number",
                    "section_number",
                    "row",
                    "col",
                    "chessboard_detected",
                    "chessboard_confidence",
                    "bubble_count",
                    "bubble_numbers",
                    "bubble_colors",
                    "bubble_details",
                    "detected_diagram_number",
                    "calculated_diagram_number",
                    "coordinates"
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for section in sections:
                    row = self.processor.format_output_row(section, section.get("page_number", 0))
                    writer.writerow(row)
                    
        except Exception as e:
            print(f"Error saving to CSV: {e}")
    
    def append_to_csv(self, sections: List[Dict], filename: str):
        """Append sections to existing CSV file"""
        try:
            with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    "page_number",
                    "section_number",
                    "row",
                    "col",
                    "chessboard_detected",
                    "chessboard_confidence",
                    "bubble_count",
                    "bubble_numbers",
                    "bubble_colors",
                    "bubble_details",
                    "detected_diagram_number",
                    "calculated_diagram_number",
                    "coordinates"
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                for section in sections:
                    row = self.processor.format_output_row(section, section.get("page_number", 0))
                    writer.writerow(row)
                    
        except Exception as e:
            print(f"Error appending to CSV: {e}")
    
    def print_summary(self, sections: List[Dict]):
        """Print a summary of extracted data including bubble statistics"""
        if not sections:
            print("No sections extracted")
            return
        
        print("\n=== EXTRACTION SUMMARY ===")
        print(f"Total sections: {len(sections)}")
        
        # Count sections with chessboards
        sections_with_chessboards = sum(1 for s in sections if s.get("chessboard_detected"))
        print(f"Sections with chessboards: {sections_with_chessboards}")
        
        # Count bubbles
        total_bubbles = 0
        sections_with_bubbles = 0
        
        for section in sections:
            bubble_count = section.get("bubble_count", 0)
            total_bubbles += bubble_count
            if bubble_count > 0:
                sections_with_bubbles += 1
        
        print(f"Total bubbles detected: {total_bubbles}")
        print(f"Sections with bubbles: {sections_with_bubbles}")
        
        # Show sample bubble details
        print("\nSample extracted data:")
        for i, section in enumerate(sections[:3]):  # Show first 3 sections
            print(f"  Section {section['section_number']}: {section['bubble_count']} bubbles")
            print(f"    Numbers: {section['bubble_numbers']}")
            print(f"    Colors: {section['bubble_colors']}")
            print(f"    Details: {section['bubble_details']}")
            print(f"    Diagram: {section.get('diagram_number', 'N/A')}")


def main():
    """Main function to run the Combinational Motifs extractor with bubble detection"""
    
    # Configuration for Combinational Motifs book
    pdf_path = "data_input/Combinational Motifs (in Russian, English and Spanish) (Maxim Blokh).pdf"
    
    # Check if PDF exists
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        print("Please place the Combinational Motifs PDF in the data_input folder")
        return
    
    # Create extractor
    extractor = CombinationalMotifsExtractor(pdf_path)
    
    # Process PDF (test on a smaller range first)
    sections = extractor.process_pdf(start_page=17, end_page=20)  # Process pages 18-21 (0-indexed)
    
    # CSV is already saved incrementally during processing
    # extractor.save_to_csv(sections)
    
    # Print summary
    extractor.print_summary(sections)
    
    print("\nProcessing complete!")
    print(f"Check the output CSV file: {extractor.output_csv}")
    print(f"Check section images in: {extractor.sections_dir}")


if __name__ == "__main__":
    main() 