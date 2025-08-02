import fitz  # PyMuPDF
import os


def extract_images_from_pdf(pdf_path, output_dir="extracted_images", page_start=None, page_end=None):
    """
    Extracts all images from PDF and saves them to disk.
    Returns a mapping of image references to file paths.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted images
        page_start: Starting page number (1-indexed)
        page_end: Ending page number (1-indexed)

    Returns:
        dict: Mapping of image_id to file path
    """
    doc = fitz.open(pdf_path)
    image_paths = {}

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Handle page range
    start_page = (page_start - 1) if page_start else 0
    end_page = page_end if page_end else len(doc)

    for page_num in range(start_page, min(end_page, len(doc))):
        page = doc[page_num]
        actual_page_num = page_num + 1

        # Get all images on this page
        image_list = page.get_images(full=True)

        for img_index, img in enumerate(image_list):
            # Get image reference number
            xref = img[0]

            # Skip if we already extracted this image
            if xref in image_paths:
                continue

            try:
                # Extract image
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # Create filename
                image_filename = f"img_{xref}.{image_ext}"
                image_path = os.path.join(output_dir, image_filename)

                # Save image
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)

                image_paths[xref] = image_path
                print(f"Extracted image {xref} from page {actual_page_num}: {image_path}")

            except Exception as e:
                print(f"Error extracting image {xref} from page {actual_page_num}: {e}")
                continue

    doc.close()
    return image_paths