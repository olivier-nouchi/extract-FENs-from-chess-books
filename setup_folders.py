#!/usr/bin/env python3
"""
Setup script to create the proper folder structure for Chess Diagram Extractor.

Run this script once to set up the project folders:
    python setup_folders.py
"""

import os
from config import INPUT_FOLDER, OUTPUT_FOLDER, IMAGES_FOLDER


def create_folder_structure():
    """
    Create the required folder structure for the project.
    """
    print("🗂️  Setting up Chess Diagram Extractor folder structure...")

    folders_to_create = [
        INPUT_FOLDER,  # data_input/
        OUTPUT_FOLDER,  # data_output/
        os.path.join(OUTPUT_FOLDER, IMAGES_FOLDER),  # data_output/extracted_images/
    ]

    for folder in folders_to_create:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"✅ Created folder: {folder}/")
        else:
            print(f"📁 Folder already exists: {folder}/")

    # Create sample .gitkeep files to preserve empty folders in git
    gitkeep_paths = [
        os.path.join(INPUT_FOLDER, ".gitkeep"),
        os.path.join(OUTPUT_FOLDER, IMAGES_FOLDER, ".gitkeep"),
    ]

    for gitkeep_path in gitkeep_paths:
        if not os.path.exists(gitkeep_path):
            with open(gitkeep_path, 'w') as f:
                f.write("# This file ensures the folder is tracked by git\n")
            print(f"📝 Created .gitkeep: {gitkeep_path}")

    print(f"\n🎉 Folder structure created successfully!")
    print(f"\n📂 Project Structure:")
    print(f"   {INPUT_FOLDER}/          <- Place your PDF files here")
    print(f"   {OUTPUT_FOLDER}/         <- All outputs will be saved here")
    print(f"   {OUTPUT_FOLDER}/{IMAGES_FOLDER}/ <- Extracted images (if enabled)")
    print(f"\n📝 Next steps:")
    print(f"   1. Copy your PDF file to {INPUT_FOLDER}/")
    print(f"   2. Update PDF_PATH in config.py")
    print(f"   3. Run: python main.py")


if __name__ == "__main__":
    create_folder_structure()