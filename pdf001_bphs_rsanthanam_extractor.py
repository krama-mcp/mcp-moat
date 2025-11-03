#!/usr/bin/env python3
"""
PDF Text Extractor - English Content Only
Extracts English text from each page of a PDF and saves to individual text files
"""

import os
import re
import sys
from pathlib import Path

import PyPDF2
import langdetect
from langdetect import detect_langs, LangDetectException


def is_english_text(text, threshold=0.7):
    """
    Check if the text is primarily English
    Returns True if English content is above threshold
    """
    if not text or len(text.strip()) < 10:
        return False

    try:
        # Remove excessive whitespace and newlines
        clean_text = ' '.join(text.split())

        # Check for basic English characters
        english_chars = sum(1 for c in clean_text if c.isascii())
        total_chars = len(clean_text)

        if total_chars == 0:
            return False

        ascii_ratio = english_chars / total_chars

        # If text is mostly ASCII, likely English
        if ascii_ratio > 0.9:
            return True

        # Use language detection as secondary check
        langs = detect_langs(clean_text)
        for lang in langs:
            if lang.lang == 'en' and lang.prob > threshold:
                return True

    except LangDetectException:
        # If language detection fails, fall back to ASCII ratio
        return ascii_ratio > 0.8 if 'ascii_ratio' in locals() else False

    return False


def extract_english_content(text):
    """
    Extract only English content from mixed language text
    """
    if not text:
        return ""

    # Split text into lines
    lines = text.split('\n')
    english_lines = []

    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue

        # Split line into segments (in case of mixed content)
        # Check if line is primarily English
        if is_english_text(line):
            # Clean up the line
            cleaned_line = line.strip()
            # Remove excessive spaces
            cleaned_line = re.sub(r'\s+', ' ', cleaned_line)
            if cleaned_line:
                english_lines.append(cleaned_line)

    return '\n'.join(english_lines)


def process_pdf(pdf_path, output_dir=None):
    """
    Process PDF file and extract English content from each page
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        print(f"Error: PDF file not found at {pdf_path}")
        return False

    # Set output directory (same as PDF location if not specified)
    if output_dir is None:
        output_dir = pdf_path.parent
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing PDF: {pdf_path.name}")
    print(f"Output directory: {output_dir}")

    try:
        # Open PDF file
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)

            print(f"Total pages in PDF: {total_pages}")

            pages_with_content = 0

            for page_num in range(total_pages):
                print(f"Processing page {page_num + 1}/{total_pages}...", end=' ')

                # Extract text from page
                page = pdf_reader.pages[page_num]
                raw_text = page.extract_text()

                # Extract only English content
                english_content = extract_english_content(raw_text)

                if english_content:
                    # Create filename with page number (1-indexed)
                    output_file = output_dir / f"page_{page_num + 1:03d}.txt"

                    # Write content to file
                    with open(output_file, 'w', encoding='utf-8') as txt_file:
                        txt_file.write(english_content)

                    pages_with_content += 1
                    print(f"✓ (saved {len(english_content)} chars)")
                else:
                    print("✗ (no English content found)")

            print(f"\nExtraction complete!")
            print(f"Pages with English content: {pages_with_content}/{total_pages}")
            print(f"Text files saved in: {output_dir}")

            return True

    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return False


def main():
    # PDF file path
    pdf_file = "/Users/kiran.ramanna/Documents/github/mcp-moat/pdf-file/BPHS - 2 RSanthanam.pdf"

    # Process the PDF
    success = process_pdf(pdf_file)

    if success:
        print("\n✅ PDF processing completed successfully!")
    else:
        print("\n❌ PDF processing failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()