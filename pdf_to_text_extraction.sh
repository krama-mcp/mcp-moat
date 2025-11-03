#!/bin/bash

# PDF Text Extraction Pipeline
# This script extracts English text from PDF files, saving each page as a separate text file

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

# Parse command line arguments
PDF_FILE=""
OUTPUT_DIR=""

usage() {
    echo "Usage: $0 [PDF_FILE] [OPTIONS]"
    echo ""
    echo "PDF Text Extraction - Extracts English text from each page of a PDF"
    echo ""
    echo "Arguments:"
    echo "  PDF_FILE                 Input PDF file (required)"
    echo ""
    echo "Options:"
    echo "  -o, --output DIR         Output directory for text files (default: same as PDF)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Extract text from PDF to same directory"
    echo "  $0 ~/Documents/book.pdf"
    echo ""
    echo "  # Extract with custom output directory"
    echo "  $0 ~/Documents/book.pdf -o ~/Documents/book-text"
    echo ""
    echo "Note: Creates one text file per page (page_001.txt, page_002.txt, etc.)"
    exit 1
}

# Check if first argument is the PDF file (not an option)
if [[ $# -gt 0 && ! "$1" =~ ^- ]]; then
    PDF_FILE="$1"
    shift
fi

# Parse remaining arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Check if PDF file was provided
if [ -z "$PDF_FILE" ]; then
    print_error "PDF file is required"
    echo ""
    usage
fi

# Expand ~ and resolve the PDF file path
PDF_FILE="${PDF_FILE/#\~/$HOME}"
PDF_FILE="$(realpath "$PDF_FILE" 2>/dev/null || echo "$PDF_FILE")"

# Check if PDF file exists
if [ ! -f "$PDF_FILE" ]; then
    print_error "PDF file does not exist: $PDF_FILE"
    exit 1
fi

# Set output directory to same as PDF if not specified
if [ -z "$OUTPUT_DIR" ]; then
    OUTPUT_DIR="$(dirname "$PDF_FILE")"
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

echo "========================================="
echo "PDF Text Extraction Pipeline"
echo "========================================="
echo ""

# Check if conda is available
if ! command -v conda &> /dev/null; then
    print_error "Conda is not installed or not in PATH"
    echo "Please install Anaconda or Miniconda first."
    exit 1
fi

# Check if mcp-moat environment exists
if ! conda env list | grep -q "^mcp-moat "; then
    print_info "mcp-moat conda environment not found. Setting up environment..."

    # Check if setup_env.sh exists and use it, otherwise create environment directly
    if [ -f "setup_env.sh" ]; then
        # Run setup script
        print_info "Running setup_env.sh to create environment..."
        bash setup_env.sh || {
            print_error "Failed to run setup_env.sh"
            exit 1
        }
    else
        # Create conda environment directly
        print_info "Creating conda environment 'mcp-moat' with Python 3.11..."
        conda create -n mcp-moat python=3.11 -y || {
            print_error "Failed to create conda environment"
            exit 1
        }

        # Source conda.sh for proper activation
        if [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
            source "/opt/anaconda3/etc/profile.d/conda.sh"
        elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
            source "$HOME/anaconda3/etc/profile.d/conda.sh"
        elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
            source "$HOME/miniconda3/etc/profile.d/conda.sh"
        else
            source $(conda info --base)/etc/profile.d/conda.sh
        fi

        # Activate the environment
        conda activate mcp-moat || {
            print_error "Failed to activate conda environment"
            exit 1
        }

        # Install requirements
        if [ -f "requirements.txt" ]; then
            print_info "Installing packages from requirements.txt..."
            pip install -r requirements.txt || {
                print_warning "Some packages from requirements.txt may have failed"
            }
        fi

        # Ensure PDF-specific packages are installed
        print_info "Installing PDF extraction packages..."
        pip install PyPDF2 langdetect || {
            print_error "Failed to install required PDF packages"
            exit 1
        }
    fi
    print_success "Environment setup completed"
fi

# Source conda.sh for proper activation
if [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
    source "/opt/anaconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
else
    source $(conda info --base)/etc/profile.d/conda.sh 2>/dev/null || {
        print_error "Cannot find conda initialization script"
        echo "Please activate the environment manually: conda activate mcp-moat"
        echo "Then run this script again."
        exit 1
    }
fi

# Activate the mcp-moat environment
conda activate mcp-moat || {
    print_error "Failed to activate mcp-moat environment"
    echo "Try running: conda activate mcp-moat"
    echo "Then run this script again."
    exit 1
}

print_info "Configuration:"
echo "  PDF File: $PDF_FILE"
echo "  Output Directory: $OUTPUT_DIR"
echo "  Conda Environment: mcp-moat (active)"
echo ""

# Set the correct Python path for conda environment
PYTHON_CMD="/opt/anaconda3/envs/mcp-moat/bin/python"
if [ ! -f "$PYTHON_CMD" ]; then
    # Fallback to python3 in PATH
    PYTHON_CMD="python3"
fi

# Install required Python packages if not present
print_info "Checking and installing required Python packages..."
$PYTHON_CMD -c "import PyPDF2" 2>/dev/null || {
    print_info "Installing PyPDF2..."
    pip install PyPDF2 || {
        print_error "Failed to install PyPDF2"
        exit 1
    }
}

$PYTHON_CMD -c "import langdetect" 2>/dev/null || {
    print_info "Installing langdetect..."
    pip install langdetect || {
        print_error "Failed to install langdetect"
        exit 1
    }
}

print_success "All prerequisites checked and installed"
echo ""

# Find the PDF extraction script
PDF_SCRIPT=""
if [ -f "pdf001_bphs_rsanthanam_extractor.py" ]; then
    PDF_SCRIPT="pdf001_bphs_rsanthanam_extractor.py"
elif [ -f "pdf-file/pdf001_bphs_rsanthanam_extractor.py" ]; then
    PDF_SCRIPT="pdf-file/pdf001_bphs_rsanthanam_extractor.py"
else
    # Look for any pdf extraction script
    PDF_SCRIPT=$(find . -name "pdf001*.py" -type f | head -1)
fi

if [ -z "$PDF_SCRIPT" ]; then
    print_error "PDF extraction script not found (pdf001_*.py)"
    echo "Please ensure the PDF extraction Python script is in the current directory."
    exit 1
fi

# Run the PDF extraction
echo "Running PDF Text Extraction..."
echo "-----------------------------------------"
print_info "Using script: $PDF_SCRIPT"
print_info "Processing: $(basename "$PDF_FILE")"

# Run the PDF extraction script directly with parameters
$PYTHON_CMD -c "
import sys
import os

# Modify the script to use our custom paths
pdf_file = '$PDF_FILE'
output_dir = '$OUTPUT_DIR'

# Read and modify the extraction script
with open('$PDF_SCRIPT', 'r') as f:
    script_content = f.read()

# Replace the hardcoded path in main() function
script_content = script_content.replace(
    'pdf_file = \"/Users/kiran.ramanna/Documents/github/mcp-moat/pdf-file/BPHS - 2 RSanthanam.pdf\"',
    f'pdf_file = \"{pdf_file}\"'
)

# Execute the modified script
exec(script_content)
" || {
    print_error "PDF extraction failed"
    exit 1
}

print_success "PDF extraction completed"
echo ""

# Count extracted files
NUM_FILES=$(ls -1 "$OUTPUT_DIR"/page_*.txt 2>/dev/null | wc -l)

echo "========================================="
print_success "PDF text extraction completed!"
echo "========================================="
echo ""
echo "Results:"
echo "  PDF File: $(basename "$PDF_FILE")"
echo "  Output Directory: $OUTPUT_DIR"
echo "  Text Files Created: $NUM_FILES"
echo ""

if [ "$NUM_FILES" -gt 0 ]; then
    echo "Sample files created:"
    ls -1 "$OUTPUT_DIR"/page_*.txt 2>/dev/null | head -5 | while read -r file; do
        echo "  - $(basename "$file")"
    done
    if [ "$NUM_FILES" -gt 5 ]; then
        echo "  ... and $((NUM_FILES - 5)) more"
    fi
fi