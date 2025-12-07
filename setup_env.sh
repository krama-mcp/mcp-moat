#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}$1${NC}"
}

# Check for system dependencies
echo "Checking system dependencies..."

# Check for tesseract (required for OCR)
if ! command -v tesseract &> /dev/null; then
    print_error "tesseract not found. Required for PDF OCR."
    echo "Install with: brew install tesseract"
    MISSING_DEPS=true
fi

# Check for poppler (required for pdf2image)
if ! command -v pdfinfo &> /dev/null; then
    print_error "poppler not found. Required for PDF processing."
    echo "Install with: brew install poppler"
    MISSING_DEPS=true
fi

if [ "$MISSING_DEPS" = true ]; then
    echo ""
    print_info "Install missing dependencies and run this script again."
    exit 1
fi

print_success "All system dependencies found"

# Create virtual environment with Python 3.11
echo ""
echo "Creating virtual environment '.venv' with Python 3.11..."
python3.11 -m venv .venv

# Activate the environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing requirements from requirements.txt..."
pip install -r requirements.txt

echo ""
print_success "Environment setup complete!"
echo ""
echo "To activate the environment, run:"
echo "  source .venv/bin/activate"
