#!/usr/bin/env python3
"""
step4_summarizer_only.py

This script processes blog files from an input directory and extracts only the KEY TAKEAWAYS section,
saving the results to the specified output directory.

Usage:
    python step4_summarizer_only.py -i <input_directory> -o <output_directory>
"""

import os
import re
import shutil
import argparse
from pathlib import Path

def extract_key_takeaways(content):
    """
    Extract only the KEY TAKEAWAYS section from the content.
    Returns None if no KEY TAKEAWAYS section is found.
    """
    # Find the KEY TAKEAWAYS section - handle different formatting variations
    key_takeaways_match = re.search(r'KEY TAKEAWAYS:(?:\s*\*\*)?\s*(.*?)(?=\n\s*ORIGINAL TEXT:|$)', 
                                   content, re.DOTALL)
    
    if not key_takeaways_match:
        # Return None when no KEY TAKEAWAYS found
        return None
    
    # Get the key takeaways content
    key_takeaways = key_takeaways_match.group(1).strip()
    
    # Format the output
    return f"KEY TAKEAWAYS:\n{key_takeaways}"

def process_files(input_dir, output_dir):
    """
    Process all files in the input directory and extract KEY TAKEAWAYS to the output directory.
    
    Args:
        input_dir (str): Path to the input directory containing files to process
        output_dir (str): Path to the output directory where processed files will be saved
    """
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    files_processed = 0
    files_with_takeaways = 0
    
    # Process each file in the input directory
    for filename in os.listdir(input_dir):
        input_file_path = os.path.join(input_dir, filename)
        
        # Skip directories
        if not os.path.isfile(input_file_path):
            continue
            
        files_processed += 1
        
        # Read the content of the file
        with open(input_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Extract the key takeaways
        key_takeaways = extract_key_takeaways(content)
        
        # Only create output file if KEY TAKEAWAYS section was found
        if key_takeaways is not None:
            files_with_takeaways += 1
            
            # Write the key takeaways to the corresponding file in the output directory
            output_file_path = os.path.join(output_dir, filename)
            with open(output_file_path, 'w', encoding='utf-8') as file:
                file.write(key_takeaways)
    
    print(f"Processed {files_processed} files from '{input_dir}', extracted takeaways from {files_with_takeaways} files")

if __name__ == "__main__":
    # Set up command-line argument parser
    parser = argparse.ArgumentParser(description='Extract KEY TAKEAWAYS from blog files')
    parser.add_argument('-i', '--input', required=True, help='Input directory containing files to process')
    parser.add_argument('-o', '--output', required=True, help='Output directory for processed files')
    
    args = parser.parse_args()
    
    # Get absolute paths for input and output directories
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(base_dir, args.input)
    output_dir = os.path.join(base_dir, args.output)
    
    # Validate input directory
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist")
        exit(1)
    
    print(f"Processing files from '{input_dir}' to '{output_dir}'")
    
    # Process the files
    process_files(input_dir, output_dir)
    
    print("Processing complete!")
