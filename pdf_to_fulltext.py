#!/usr/bin/env python3
"""
PDF to Full Text Converter
Extracts all text from a PDF and saves it as a single text file
"""

import os
import sys
from pathlib import Path
import PyPDF2
import pdfplumber
import argparse


def extract_text_with_pdfplumber(pdf_path: str) -> str:
    """Extract text using pdfplumber (better quality)."""
    full_text = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"Extracting {total_pages} pages using pdfplumber...")

            for i, page in enumerate(pdf.pages, 1):
                if i % 50 == 0:
                    print(f"  Processing page {i}/{total_pages}...")

                page_text = page.extract_text()
                if page_text:
                    # Add page marker
                    full_text.append(f"\n\n{'='*80}")
                    full_text.append(f"PAGE {i}")
                    full_text.append('='*80)
                    full_text.append(page_text)

        return '\n'.join(full_text)

    except Exception as e:
        print(f"pdfplumber error: {e}")
        return None


def extract_text_with_pypdf2(pdf_path: str) -> str:
    """Extract text using PyPDF2 (fallback)."""
    full_text = []

    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            print(f"Extracting {total_pages} pages using PyPDF2...")

            for i in range(total_pages):
                if (i + 1) % 50 == 0:
                    print(f"  Processing page {i + 1}/{total_pages}...")

                page = pdf_reader.pages[i]
                page_text = page.extract_text()

                if page_text:
                    # Add page marker
                    full_text.append(f"\n\n{'='*80}")
                    full_text.append(f"PAGE {i + 1}")
                    full_text.append('='*80)
                    full_text.append(page_text)

        return '\n'.join(full_text)

    except Exception as e:
        print(f"PyPDF2 error: {e}")
        return None


def process_pdf(pdf_path: str, output_path: str = None):
    """Process a single PDF file."""
    pdf_path = Path(pdf_path).resolve()

    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        return False

    if not pdf_path.suffix.lower() == '.pdf':
        print(f"Error: Not a PDF file: {pdf_path}")
        return False

    # Determine output path
    if output_path:
        output_file = Path(output_path)
    else:
        output_file = pdf_path.parent / f"{pdf_path.stem}_fulltext.txt"

    print(f"\nProcessing: {pdf_path.name}")
    print(f"Output file: {output_file}")
    print("-" * 80)

    # Try pdfplumber first (usually better quality)
    full_text = extract_text_with_pdfplumber(str(pdf_path))

    # Fallback to PyPDF2 if pdfplumber fails
    if not full_text:
        print("\nFalling back to PyPDF2...")
        full_text = extract_text_with_pypdf2(str(pdf_path))

    if not full_text:
        print("Error: Could not extract text from PDF")
        return False

    # Add header information
    header = []
    header.append("=" * 80)
    header.append(f"FULL TEXT EXTRACTION FROM: {pdf_path.name}")
    header.append("=" * 80)
    header.append(f"\nSource PDF: {pdf_path}")
    header.append(f"Extraction Date: {os.popen('date').read().strip()}")
    header.append(f"Total Characters: {len(full_text):,}")
    header.append(f"Total Words (approx): {len(full_text.split()):,}")
    header.append("\n" + "=" * 80)

    # Combine header and text
    final_text = '\n'.join(header) + '\n' + full_text

    # Save to file
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_text)

    # Report statistics
    file_size = os.path.getsize(output_file) / (1024 * 1024)  # Size in MB

    print("\n" + "=" * 80)
    print(f"✅ Successfully extracted text from PDF")
    print(f"📄 Output file: {output_file}")
    print(f"📊 File size: {file_size:.2f} MB")
    print(f"📝 Characters: {len(full_text):,}")
    print(f"📖 Words (approx): {len(full_text.split()):,}")

    return True


def process_folder(folder_path: str):
    """Process all PDFs in a folder."""
    folder = Path(folder_path).resolve()

    if not folder.exists() or not folder.is_dir():
        print(f"Error: Invalid folder path: {folder}")
        return

    pdf_files = list(folder.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in: {folder}")
        return

    print(f"\nFound {len(pdf_files)} PDF files in {folder}")
    print("=" * 80)

    success_count = 0
    for pdf_file in pdf_files:
        if process_pdf(str(pdf_file)):
            success_count += 1
        print()

    print("=" * 80)
    print(f"Processed {success_count}/{len(pdf_files)} PDFs successfully")


def main():
    parser = argparse.ArgumentParser(
        description="Extract full text from PDF files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s book.pdf                    # Extract text from single PDF
  %(prog)s /path/to/pdfs/              # Process all PDFs in folder
  %(prog)s book.pdf -o extracted.txt   # Custom output filename
        """
    )

    parser.add_argument(
        "input",
        help="PDF file or folder containing PDFs"
    )

    parser.add_argument(
        "-o", "--output",
        help="Custom output file path (for single PDF only)",
        default=None
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if input_path.is_file():
        process_pdf(str(input_path), args.output)
    elif input_path.is_dir():
        if args.output:
            print("Warning: --output flag is ignored when processing folders")
        process_folder(str(input_path))
    else:
        print(f"Error: Invalid input path: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()