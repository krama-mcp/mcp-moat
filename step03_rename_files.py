import os
import re
import argparse
import logging
from pathlib import Path
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def natural_sort_key(s):
    """Key function for natural sorting of strings with numbers"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def get_session_number(filename):
    """Extract session number from filename"""
    match = re.search(r'Live Session ([IVX]+)', filename)
    if match:
        session_num = match.group(1)
        # Convert Roman numerals to integers
        roman_values = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10}
        return roman_values.get(session_num, 0)
    return 0

def get_part_number(filename):
    """Extract part number from filename"""
    match = re.search(r'Part (\d+)', filename)
    return int(match.group(1)) if match else 0

def get_subpart_number(filename):
    """Extract subpart number from filename"""
    match = re.search(r'--part(\d+)', filename)
    return int(match.group(1)) if match else 0

def rename_files(input_folder=None):
    """Rename files with proper extensions and serial numbers"""
    # Get the path to the blog directory
    if input_folder is None:
        blog_dir = Path("wisdomhatch-blog")
    else:
        blog_dir = Path(input_folder)
        
    logger.info(f"Input folder: {blog_dir}")
    
    # Ensure the directory exists
    if not blog_dir.exists():
        logger.error(f"Input directory does not exist: {blog_dir}")
        raise FileNotFoundError(f"Directory not found: {blog_dir}")
    
    # Get all text files (either .md or .txt)
    files = [f for f in os.listdir(blog_dir) if f.endswith('.txt') or f.endswith('.md')]
    
    # Extract base names and part numbers for sorting
    file_info = []
    for file in files:
        # Remove any existing serial prefix
        base_name = re.sub(r'^\d+-', '', file)
        
        # Extract base name without part number
        part_match = re.search(r'_part(\d+)', base_name)
        part_num = int(part_match.group(1)) if part_match else 0
        main_name = base_name.split('_part')[0] if part_match else base_name
        
        file_info.append({
            'file_name': file,
            'main_name': main_name,
            'part_num': part_num
        })
    
    # Sort files by main name first, then by part number
    file_info.sort(key=lambda x: (x['main_name'], x['part_num']))
    
    # Counter for serial numbering
    serial_number = 1
    
    # Process files in sorted order
    for info in file_info:
        old_name = info['file_name']
        
        # Create the new name with serial number prefix
        serial_prefix = f"{serial_number:03d}-"  # Format as 001, 002, etc.
        
        # Remove any existing serial prefix
        base_name = re.sub(r'^\d+-', '', old_name)
        
        # Create the new name
        new_name = f"{serial_prefix}{base_name}"
        
        # Skip if the file already has the correct name
        if old_name == new_name:
            serial_number += 1
            continue
        
        # Get the full paths
        old_path = os.path.join(blog_dir, old_name)
        new_path = os.path.join(blog_dir, new_name)
        
        try:
            os.rename(old_path, new_path)
            logger.info(f"Renamed: {old_name} -> {new_name}")
            serial_number += 1
        except Exception as e:
            logger.error(f"Error renaming {old_name}: {e}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Rename blog files with proper serial numbers')
    parser.add_argument('-i', '--input', dest='input_folder', 
                        help='Input folder containing blog files to rename')
    return parser.parse_args()

def main():
    """Main function to run the file renaming process"""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Run rename process with provided argument
        rename_files(input_folder=args.input_folder)
        logger.info("File renaming process completed")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main() 