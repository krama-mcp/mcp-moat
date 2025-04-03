import os
import re
from pathlib import Path
from collections import defaultdict

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

def rename_files():
    """Rename files with proper extensions and serial numbers"""
    # Get the path to the blog directory
    blog_dir = Path("wisdomhatch-blog")
    
    # Get all md files
    files = [f for f in os.listdir(blog_dir) if f.endswith('.md')]
    
    # Group files by session
    session_files = defaultdict(list)
    for file in files:
        session_num = get_session_number(file)
        session_files[session_num].append(file)
    
    # Sort files within each session
    for session_num in session_files:
        session_files[session_num].sort(key=lambda x: (get_part_number(x), get_subpart_number(x)))
    
    # Counter for serial numbering
    serial_number = 1
    
    # Process files in session order
    for session_num in sorted(session_files.keys()):
        for old_name in session_files[session_num]:
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
                print(f"Renamed: {old_name}\n -> {new_name}")
                serial_number += 1
            except Exception as e:
                print(f"Error renaming {old_name}: {e}")

if __name__ == "__main__":
    rename_files() 