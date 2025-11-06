#!/bin/bash

# Post to GitHub Pipeline
# This script runs step05 (generate LinkedIn posts) and step06 (push to GitHub)

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

# Parse command line arguments
INPUT_FOLDER=""
POST_OUTPUT=""
REPO_NAME="kiranramanna/thinkit"

usage() {
    echo "Usage: $0 [INPUT_FOLDER] [OPTIONS]"
    echo ""
    echo "Post to GitHub Pipeline - Generates LinkedIn posts and pushes them to GitHub"
    echo ""
    echo "Arguments:"
    echo "  INPUT_FOLDER             Input folder name or path (required)"
    echo "                           - If ends with -summarize: uses as-is, output is {name}-post"
    echo "                           - Otherwise: looks for {name}-summarize, output is {name}-post"
    echo ""
    echo "Options:"
    echo "  -o, --output DIR         Override post output directory (default: auto-generated with -post suffix)"
    echo "  -r, --repo NAME          GitHub repository (default: kiranramanna/thinkit)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  # With -summarize suffix (uses wisdomhatch-summarize → wisdomhatch-post)"
    echo "  $0 wisdomhatch-summarize"
    echo ""
    echo "  # Without -summarize suffix (looks for wisdomhatch-summarize → wisdomhatch-post)"
    echo "  $0 wisdomhatch"
    echo ""
    echo "  # Another example (looks for yc-startuppicker-summarize → yc-startuppicker-post)"
    echo "  $0 yc-startuppicker"
    echo ""
    echo "  # Push to custom repository"
    echo "  $0 wisdomhatch-summarize -r username/other-repo"
    echo ""
    echo "  # Specify custom output folder"
    echo "  $0 wisdomhatch-summarize -o my-posts"
    echo ""
    exit 1
}

# Check if first argument is the input folder (not an option)
if [[ $# -gt 0 && ! "$1" =~ ^- ]]; then
    INPUT_FOLDER="$1"
    shift
fi

# Parse remaining arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            POST_OUTPUT="$2"
            shift 2
            ;;
        -r|--repo)
            REPO_NAME="$2"
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

# Check if input folder was provided
if [ -z "$INPUT_FOLDER" ]; then
    print_error "Input folder is required"
    echo ""
    usage
fi

# Expand ~ and resolve the input folder path
INPUT_FOLDER="${INPUT_FOLDER/#\~/$HOME}"

# Get the base name before resolving path (to check for -summarize suffix)
ORIGINAL_INPUT=$(basename "$INPUT_FOLDER")

# Handle -summarize suffix logic
if [[ "$ORIGINAL_INPUT" == *-summarize ]]; then
    # Input already has -summarize suffix, use it as-is
    ACTUAL_INPUT="$INPUT_FOLDER"
    CLEAN_NAME="${ORIGINAL_INPUT%-summarize}"
else
    # Input doesn't have -summarize suffix, append it to find source
    CLEAN_NAME="$ORIGINAL_INPUT"
    # If INPUT_FOLDER is just a basename, look in current directory
    if [[ "$INPUT_FOLDER" == "$ORIGINAL_INPUT" ]]; then
        ACTUAL_INPUT="${INPUT_FOLDER}-summarize"
    else
        # INPUT_FOLDER has a path, append -summarize to the basename
        PARENT_DIR=$(dirname "$INPUT_FOLDER")
        ACTUAL_INPUT="${PARENT_DIR}/${ORIGINAL_INPUT}-summarize"
    fi
fi

# Resolve the actual input path
ACTUAL_INPUT="$(realpath "$ACTUAL_INPUT" 2>/dev/null || echo "$ACTUAL_INPUT")"

# Check if actual input folder exists
if [ ! -d "$ACTUAL_INPUT" ]; then
    print_error "Input folder does not exist: $ACTUAL_INPUT"
    if [[ "$ORIGINAL_INPUT" != *-summarize ]]; then
        echo "Note: Since your input didn't end with -summarize, we looked for: ${ORIGINAL_INPUT}-summarize"
    fi
    exit 1
fi

# Check if folder has content (at least one .md file)
MD_FILES_IN_INPUT=$(find "$ACTUAL_INPUT" -maxdepth 1 -name "*.md" | wc -l)
if [ "$MD_FILES_IN_INPUT" -eq 0 ]; then
    print_error "No .md files found in input folder: $ACTUAL_INPUT"
    echo "Please ensure the folder contains markdown files to process."
    exit 1
fi

# Auto-generate post output directory if not specified
if [ -z "$POST_OUTPUT" ]; then
    POST_OUTPUT="${CLEAN_NAME}-post"
fi

echo "========================================="
echo "Post to GitHub Pipeline"
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

    # Check if setup_env.sh exists
    if [ ! -f "setup_env.sh" ]; then
        print_error "setup_env.sh not found in current directory"
        echo "Please ensure setup_env.sh is in the same directory as this script."
        exit 1
    fi

    # Run setup script
    print_info "Running setup_env.sh to create environment..."
    bash setup_env.sh || {
        print_error "Failed to run setup_env.sh"
        exit 1
    }
    print_success "Environment setup completed"
fi

# Check if we're in the correct conda environment
CURRENT_ENV=$(conda info --envs | grep "*" | awk '{print $1}')
if [ "$CURRENT_ENV" != "mcp-moat" ]; then
    print_info "Activating mcp-moat conda environment..."

    # Source conda.sh for proper activation
    if [ -f "/opt/anaconda3/bin/activate" ]; then
        source /opt/anaconda3/bin/activate mcp-moat
    elif [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
        source "/opt/anaconda3/etc/profile.d/conda.sh"
        conda activate mcp-moat
    elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/anaconda3/etc/profile.d/conda.sh"
        conda activate mcp-moat
    elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
        conda activate mcp-moat
    else
        print_error "Cannot find conda initialization script"
        echo "Please activate the environment manually: conda activate mcp-moat"
        echo "Then run this script again."
        exit 1
    fi

    if [ $? -ne 0 ]; then
        print_error "Failed to activate mcp-moat environment"
        echo "Try running: conda activate mcp-moat"
        echo "Then run this script again."
        exit 1
    fi
    print_success "Activated mcp-moat environment"
fi

print_info "Configuration:"
echo "  Input Folder: $ACTUAL_INPUT"
echo "  Post Output: $POST_OUTPUT"
echo "  GitHub Repo: $REPO_NAME"
echo "  Conda Environment: mcp-moat (active)"
echo ""

# Check for Python 3
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    print_error "Python 3 is not installed or not in PATH"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

print_success "All prerequisites checked"
echo ""

# Step 5: Generate LinkedIn Posts
echo "Step 1/2: Generating LinkedIn Posts..."
echo "-----------------------------------------"
if [ -f "step05_generate_linkedin_post.py" ]; then
    $PYTHON_CMD step05_generate_linkedin_post.py -i "$ACTUAL_INPUT" -o "$POST_OUTPUT"
    print_success "Step 1 completed"
else
    print_error "step05_generate_linkedin_post.py not found"
    exit 1
fi
echo ""

# Check if post output folder was created and has files
if [ ! -d "$POST_OUTPUT" ]; then
    print_error "Post output folder was not created: $POST_OUTPUT"
    exit 1
fi

# Count .md files in post output
MD_COUNT=$(find "$POST_OUTPUT" -maxdepth 1 -name "*.md" | wc -l)
if [ "$MD_COUNT" -eq 0 ]; then
    print_error "No .md files found in post output folder: $POST_OUTPUT"
    exit 1
fi

print_info "Generated $MD_COUNT post file(s)"
echo ""

# Step 6: Push to GitHub
echo "Step 2/2: Pushing to GitHub..."
echo "-----------------------------------------"
if [ -f "step06_push_to_github.py" ]; then
    $PYTHON_CMD step06_push_to_github.py -i "$POST_OUTPUT" -r "$REPO_NAME"
    print_success "Step 2 completed"
else
    print_error "step06_push_to_github.py not found"
    exit 1
fi
echo ""

echo "========================================="
print_success "Post to GitHub pipeline completed!"
echo "========================================="
echo ""
echo "Summary:"
echo "  Generated posts: $POST_OUTPUT"
echo "  Pushed to: https://github.com/$REPO_NAME"
