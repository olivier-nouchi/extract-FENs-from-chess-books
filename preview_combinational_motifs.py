
"""
Preview script for Combinational Motifs book
Shows how images (diagrams, diagram numbers, and bubbles) look for a given range of pages
Includes interactive visualization and parameter adjustment capabilities
"""

import os
import sys
import fitz  # PyMuPDF
import cv2
import numpy as np
from typing import List, Dict, Tuple
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import json
import argparse

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import COMBINATIONAL_MOTIFS_CONFIG
from combinational_motifs_processor import create_combinational_motifs_processor


class CombinationalMotifsPreview:
    """Preview functionality for Combinational Motifs book format with interactive features"""
    
    def __init__(self, pdf_path: str, config: Dict = None):
        self.pdf_path = pdf_path
        self.config = config or COMBINATIONAL_MOTIFS_CONFIG
        self.processor = create_combinational_motifs_processor(config)
        
        # Create preview output directory
        self.preview_dir = "data_output/preview_images"
        os.makedirs(self.preview_dir, exist_ok=True)
        
        # Store current parameters for adjustment
        self.current_params = self.config.copy()
        
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
    
    def create_detailed_preview_image(self, page_image: np.ndarray, sections: List[Dict], page_number: int) -> np.ndarray:
        """Create a detailed preview image showing all detected elements with coordinates"""
        # Convert BGR to RGB for matplotlib
        rgb_image = cv2.cvtColor(page_image, cv2.COLOR_BGR2RGB)
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(30, 15))
        
        # Left subplot: Full page with annotations
        ax1.imshow(rgb_image)
        ax1.set_title(f'Page {page_number} - Full Page View', fontsize=16, fontweight='bold')
        
        # Right subplot: Detailed detection view
        ax2.imshow(rgb_image)
        ax2.set_title(f'Page {page_number} - Detection Details', fontsize=16, fontweight='bold')
        
        # Process each section
        for section in sections:
            x1, y1, x2, y2 = section["coordinates"]
            
            # Draw section boundaries on both plots
            rect1 = Rectangle((x1, y1), x2-x1, y2-y1, 
                           linewidth=2, edgecolor='red', facecolor='none')
            rect2 = Rectangle((x1, y1), x2-x1, y2-y1, 
                           linewidth=2, edgecolor='red', facecolor='none')
            ax1.add_patch(rect1)
            ax2.add_patch(rect2)
            
            # Add section number
            ax1.text(x1 + 10, y1 + 30, f'S{section["section_number"]}', 
                    fontsize=12, color='red', fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
            
            # Add detailed information on right plot
            info_y = y1 + 30
            line_height = 25
            
            # Section info
            ax2.text(x1 + 10, info_y, f'S{section["section_number"]} (R{section["row"]},C{section["col"]})', 
                    fontsize=10, color='red', fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
            info_y += line_height
            
            # Diagram number if detected
            if section.get("diagram_number"):
                ax2.text(x1 + 10, info_y, f'Diagram: {section["diagram_number"]}', 
                        fontsize=10, color='blue', fontweight='bold',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.8))
                info_y += line_height
            
            # Numbers above diagram information
            numbers_info = section.get("numbers_above_diagram", {})
            if numbers_info.get("count", 0) > 0:
                numbers_text = f'Numbers: {numbers_info["count"]}'
                if numbers_info.get("numbers"):
                    numbers_list = ",".join(numbers_info["numbers"])
                    numbers_text += f' ({numbers_list})'
                ax2.text(x1 + 10, info_y, numbers_text, 
                        fontsize=9, color='blue', fontweight='bold',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
                info_y += line_height
                
                # Show number coordinates if available
                if numbers_info.get("coordinates"):
                    for i, (nx, ny, nw, nh) in enumerate(numbers_info["coordinates"]):
                        number_rect = Rectangle((nx, ny), nw, nh, 
                                             linewidth=1, edgecolor='blue', facecolor='none')
                        ax2.add_patch(number_rect)
                        ax2.text(nx + 5, ny + 15, f'N{i+1}', 
                                fontsize=8, color='blue', fontweight='bold',
                                bbox=dict(boxstyle="round,pad=0.2", facecolor="lightblue", alpha=0.8))
            
            # Chessboard detection status with confidence
            if section.get("chessboard_detected"):
                confidence = section.get("chessboard_confidence", "N/A")
                ax2.text(x2 - 120, y1 + 30, f'CHESS ✓ ({confidence})', 
                        fontsize=10, color='green', fontweight='bold',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgreen", alpha=0.8))
            else:
                ax2.text(x2 - 120, y1 + 30, 'NO CHESS ✗', 
                        fontsize=10, color='red', fontweight='bold',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightcoral", alpha=0.8))
        
        # Add legend
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, facecolor='none', edgecolor='red', linewidth=2, label='Section Boundary'),
            plt.Rectangle((0, 0), 1, 1, facecolor='lightgreen', alpha=0.8, label='Chessboard Detected'),
            plt.Rectangle((0, 0), 1, 1, facecolor='lightcoral', alpha=0.8, label='No Chessboard'),
            plt.Rectangle((0, 0), 1, 1, facecolor='yellow', alpha=0.8, label='Diagram Number'),
            plt.Rectangle((0, 0), 1, 1, facecolor='green', alpha=0.8, label='Bubble Detection')
        ]
        ax1.legend(handles=legend_elements, loc='upper right', fontsize=10)
        ax2.legend(handles=legend_elements, loc='upper right', fontsize=10)
        
        # Remove axes
        ax1.set_xticks([])
        ax1.set_yticks([])
        ax2.set_xticks([])
        ax2.set_yticks([])
        
        # Convert matplotlib figure to numpy array
        fig.canvas.draw()
        
        # Get the RGBA buffer from the figure
        w, h = fig.canvas.get_width_height()
        buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8)
        buf.shape = (h, w, 4)
        
        # Convert ARGB to RGB
        buf = np.roll(buf, 3, axis=2)
        img_data = buf[:, :, :3]
        
        plt.close(fig)
        
        # Convert RGB to BGR for OpenCV
        bgr_image = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
        
        return bgr_image
    
    def create_parameter_adjustment_interface(self, page_image: np.ndarray, sections: List[Dict], page_number: int):
        """Create an interactive interface for parameter adjustment"""
        # Convert BGR to RGB for matplotlib
        rgb_image = cv2.cvtColor(page_image, cv2.COLOR_BGR2RGB)
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(25, 20))
        
        # Top left: Original image
        axes[0, 0].imshow(rgb_image)
        axes[0, 0].set_title(f'Page {page_number} - Original', fontsize=14, fontweight='bold')
        
        # Top right: Current detection results
        axes[0, 1].imshow(rgb_image)
        axes[0, 1].set_title(f'Page {page_number} - Current Detection', fontsize=14, fontweight='bold')
        
        # Bottom left: Section grid
        axes[1, 0].imshow(rgb_image)
        axes[1, 0].set_title(f'Page {page_number} - Section Grid', fontsize=14, fontweight='bold')
        
        # Bottom right: Parameter info
        axes[1, 1].text(0.1, 0.9, 'Current Parameters:', fontsize=12, fontweight='bold')
        
        param_y = 0.8
        for key, value in self.current_params.items():
            if isinstance(value, dict):
                axes[1, 1].text(0.1, param_y, f'{key}:', fontsize=10, fontweight='bold')
                param_y -= 0.05
                for sub_key, sub_value in value.items():
                    axes[1, 1].text(0.2, param_y, f'  {sub_key}: {sub_value}', fontsize=9)
                    param_y -= 0.04
            else:
                axes[1, 1].text(0.1, param_y, f'{key}: {value}', fontsize=10)
                param_y -= 0.05
        
        # Add detection results
        axes[1, 1].text(0.1, 0.3, 'Detection Results:', fontsize=12, fontweight='bold')
        chess_detected = sum(1 for s in sections if s.get("chessboard_detected"))
        total_bubbles = sum(s.get("bubble_info", {}).get("count", 0) for s in sections)
        diagram_numbers = [s.get("diagram_number") for s in sections if s.get("diagram_number")]
        
        axes[1, 1].text(0.1, 0.25, f'Sections: {len(sections)}', fontsize=10)
        axes[1, 1].text(0.1, 0.2, f'Chessboards: {chess_detected}', fontsize=10)
        axes[1, 1].text(0.1, 0.15, f'Bubbles: {total_bubbles}', fontsize=10)
        if diagram_numbers:
            axes[1, 1].text(0.1, 0.1, f'Diagrams: {", ".join(diagram_numbers)}', fontsize=10)
        
        # Draw section boundaries and annotations
        for section in sections:
            x1, y1, x2, y2 = section["coordinates"]
            
            # Draw on current detection plot
            rect = Rectangle((x1, y1), x2-x1, y2-y1, 
                           linewidth=2, edgecolor='red', facecolor='none')
            axes[0, 1].add_patch(rect)
            
            # Add section number
            axes[0, 1].text(x1 + 10, y1 + 30, f'S{section["section_number"]}', 
                           fontsize=10, color='red', fontweight='bold',
                           bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
            
            # Draw on section grid plot
            grid_rect = Rectangle((x1, y1), x2-x1, y2-y1, 
                                linewidth=1, edgecolor='blue', facecolor='none')
            axes[1, 0].add_patch(grid_rect)
            axes[1, 0].text(x1 + 5, y1 + 20, f'R{section["row"]},C{section["col"]}', 
                           fontsize=8, color='blue', fontweight='bold',
                           bbox=dict(boxstyle="round,pad=0.2", facecolor="lightblue", alpha=0.8))
            
            # Add chessboard detection status
            if section.get("chessboard_detected"):
                axes[0, 1].text(x2 - 80, y1 + 30, 'CHESS ✓', 
                               fontsize=8, color='green', fontweight='bold',
                               bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgreen", alpha=0.8))
            else:
                axes[0, 1].text(x2 - 80, y1 + 30, 'NO CHESS ✗', 
                               fontsize=8, color='red', fontweight='bold',
                               bbox=dict(boxstyle="round,pad=0.3", facecolor="lightcoral", alpha=0.8))
        
        # Remove axes
        for ax in axes.flat:
            ax.set_xticks([])
            ax.set_yticks([])
        
        # Convert matplotlib figure to numpy array
        fig.canvas.draw()
        
        # Get the RGBA buffer from the figure
        w, h = fig.canvas.get_width_height()
        buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8)
        buf.shape = (h, w, 4)
        
        # Convert ARGB to RGB
        buf = np.roll(buf, 3, axis=2)
        img_data = buf[:, :, :3]
        
        plt.close(fig)
        
        # Convert RGB to BGR for OpenCV
        bgr_image = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
        
        return bgr_image
    
    def adjust_parameters(self, param_name: str, new_value):
        """Adjust processing parameters"""
        if param_name in self.current_params:
            self.current_params[param_name] = new_value
            print(f"Updated {param_name} to {new_value}")
            # Recreate processor with new parameters
            self.processor = create_combinational_motifs_processor(self.current_params)
        else:
            print(f"Parameter {param_name} not found in current configuration")
    
    def preview_pages(self, start_page: int = None, end_page: int = None, save_images: bool = True, 
                     detailed_view: bool = True, parameter_view: bool = False):
        """Preview pages in the given range with enhanced visualization options"""
        
        # Open PDF
        doc = fitz.open(self.pdf_path)
        
        # Determine page range
        if start_page is None:
            start_page = 17  # Start from page 18 (0-indexed = 17)
        if end_page is None:
            end_page = min(20, len(doc) - 1)  # Default to first few pages
        
        print(f"Creating preview for Combinational Motifs PDF: {self.pdf_path}")
        print(f"Page range: {start_page + 1} to {end_page + 1} (pages {start_page + 1}-{end_page + 1})")
        print(f"Total pages to preview: {end_page - start_page + 1}")
        print(f"Detailed view: {detailed_view}, Parameter view: {parameter_view}")
        
        for page_num in range(start_page, end_page + 1):
            try:
                page = doc[page_num]
                print(f"\nCreating preview for page {page_num + 1}...")
                
                # Extract page image
                page_image = self.extract_page_image(page)
                
                # Process page to get sections
                sections = self.processor.process_page(page_image, page_num + 1)
                
                # Create different types of previews
                if detailed_view:
                    detailed_preview = self.create_detailed_preview_image(page_image, sections, page_num + 1)
                    
                    if save_images:
                        detailed_filename = f"page_{page_num + 1}_detailed.png"
                        detailed_path = os.path.join(self.preview_dir, detailed_filename)
                        cv2.imwrite(detailed_path, detailed_preview)
                        print(f"  Saved detailed preview: {detailed_filename}")
                
                if parameter_view:
                    param_preview = self.create_parameter_adjustment_interface(page_image, sections, page_num + 1)
                    
                    if save_images:
                        param_filename = f"page_{page_num + 1}_parameters.png"
                        param_path = os.path.join(self.preview_dir, param_filename)
                        cv2.imwrite(param_path, param_preview)
                        print(f"  Saved parameter view: {param_filename}")
                
                # Print detailed section statistics
                chess_detected = sum(1 for s in sections if s.get("chessboard_detected"))
                total_numbers = sum(s.get("numbers_above_diagram", {}).get("count", 0) for s in sections)
                diagram_numbers = [s.get("diagram_number") for s in sections if s.get("diagram_number")]
                
                print(f"  Sections: {len(sections)}")
                print(f"  Chessboards detected: {chess_detected}")
                print(f"  Total numbers above diagrams: {total_numbers}")
                if diagram_numbers:
                    print(f"  Diagram numbers: {', '.join(diagram_numbers)}")
                
                # Print section details
                for section in sections:
                    print(f"    Section {section['section_number']} (R{section['row']},C{section['col']}): "
                          f"Chess={section.get('chessboard_detected', False)}, "
                          f"Numbers={section.get('numbers_above_diagram', {}).get('count', 0)}")
                    if section.get("diagram_number"):
                        print(f"      Diagram: {section['diagram_number']}")
                    if section.get("chessboard_confidence"):
                        print(f"      Chess confidence: {section['chessboard_confidence']}")
                    if section.get("numbers_above_diagram", {}).get("numbers"):
                        numbers_list = ",".join(section["numbers_above_diagram"]["numbers"])
                        print(f"      Numbers above: {numbers_list}")
                
            except Exception as e:
                print(f"Error creating preview for page {page_num + 1}: {e}")
                continue
        
        doc.close()
        
        print(f"\nPreview complete!")
        if save_images:
            print(f"Preview images saved to: {self.preview_dir}")


def main():
    """Main function to run the Combinational Motifs preview with command line options"""
    
    parser = argparse.ArgumentParser(description='Preview Combinational Motifs book processing')
    parser.add_argument('--start-page', type=int, default=17, 
                       help='Starting page number (0-indexed, default: 17 = page 18)')
    parser.add_argument('--end-page', type=int, default=21, 
                       help='Ending page number (0-indexed, default: 21 = page 22)')
    parser.add_argument('--pdf-path', type=str, 
                       default="data_input/Combinational Motifs (in Russian, English and Spanish) (Maxim Blokh).pdf",
                       help='Path to the PDF file')
    parser.add_argument('--no-save', action='store_true', 
                       help='Do not save preview images')
    parser.add_argument('--detailed-view', action='store_true', default=True,
                       help='Create detailed detection view')
    parser.add_argument('--parameter-view', action='store_true', default=False,
                       help='Create parameter adjustment interface view')
    
    args = parser.parse_args()
    
    # Check if PDF exists
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found at {args.pdf_path}")
        print("Please place the Combinational Motifs PDF in the data_input folder")
        return
    
    # Create preview
    preview = CombinationalMotifsPreview(args.pdf_path)
    
    # Preview pages with specified options
    preview.preview_pages(
        start_page=args.start_page, 
        end_page=args.end_page,
        save_images=not args.no_save,
        detailed_view=args.detailed_view,
        parameter_view=args.parameter_view
    )


if __name__ == "__main__":
    main() 