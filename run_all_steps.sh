#!/bin/bash

# Video Transcription Pipeline
# This script runs all 4 steps to transcribe videos and generate summaries

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
VIDEO_DIR=""
TXT_OUTPUT=""
BLOG_OUTPUT=""
SUMMARIZE_OUTPUT=""
AUTO_GENERATE=true

usage() {
    echo "Usage: $0 [VIDEO_DIR] [OPTIONS]"
    echo ""
    echo "Video Transcription Pipeline - Transcribes videos and generates summaries"
    echo ""
    echo "Arguments:"
    echo "  VIDEO_DIR                Input video directory (required)"
    echo ""
    echo "Options:"
    echo "  -t, --txt-output DIR     Override text output directory (default: auto-generated)"
    echo "  -b, --blog-output DIR    Override blog output directory (default: auto-generated)"
    echo "  -s, --summarize-output DIR  Override summarize output directory (default: auto-generated)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Transcribe videos with auto-generated output directories"
    echo "  $0 ~/Desktop/my-videos"
    echo "    Creates: my-videos-txt, my-videos-blog, my-videos-summarize"
    echo ""
    echo "  $0 ~/Videos/lecture-recordings"
    echo "    Creates: lecture-recordings-txt, lecture-recordings-blog, lecture-recordings-summarize"
    echo ""
    echo "  # Transcribe with custom output directories"
    echo "  $0 ~/Desktop/conference-talks -t transcripts -b summaries"
    echo ""
    echo "Note: Output directories are created in the current working directory"
    exit 1
}

# Check if first argument is the video directory (not an option)
if [[ $# -gt 0 && ! "$1" =~ ^- ]]; then
    VIDEO_DIR="$1"
    shift
fi

# Parse remaining arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--txt-output)
            TXT_OUTPUT="$2"
            AUTO_GENERATE=false
            shift 2
            ;;
        -b|--blog-output)
            BLOG_OUTPUT="$2"
            AUTO_GENERATE=false
            shift 2
            ;;
        -s|--summarize-output)
            SUMMARIZE_OUTPUT="$2"
            AUTO_GENERATE=false
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

# Check if video directory was provided
if [ -z "$VIDEO_DIR" ]; then
    print_error "Video directory is required"
    echo ""
    usage
fi

# Expand ~ and resolve the video directory path
VIDEO_DIR="${VIDEO_DIR/#\~/$HOME}"
VIDEO_DIR="$(realpath "$VIDEO_DIR" 2>/dev/null || echo "$VIDEO_DIR")"

# Extract the base name from the video directory for auto-generation
if [ "$AUTO_GENERATE" = true ] || [ -z "$TXT_OUTPUT" ] || [ -z "$BLOG_OUTPUT" ] || [ -z "$SUMMARIZE_OUTPUT" ]; then
    # Get the base name of the video directory (last component of the path)
    BASE_NAME=$(basename "$VIDEO_DIR")

    # Remove common suffixes like numbers, dates, or "videos" to get cleaner names
    CLEAN_NAME=$(echo "$BASE_NAME" | sed -E 's/[-_]?(videos?|vids?|[0-9]+|20[0-9]{2})$//i')
    [ -z "$CLEAN_NAME" ] && CLEAN_NAME="$BASE_NAME"

    # Auto-generate output directories if not specified
    [ -z "$TXT_OUTPUT" ] && TXT_OUTPUT="${CLEAN_NAME}-txt"
    [ -z "$BLOG_OUTPUT" ] && BLOG_OUTPUT="${CLEAN_NAME}-blog"
    [ -z "$SUMMARIZE_OUTPUT" ] && SUMMARIZE_OUTPUT="${CLEAN_NAME}-summarize"
fi

echo "========================================="
echo "Video Transcription Pipeline"
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
    if [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
        source "/opt/anaconda3/etc/profile.d/conda.sh"
    elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/anaconda3/etc/profile.d/conda.sh"
    elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
    else
        print_error "Cannot find conda initialization script"
        echo "Please activate the environment manually: conda activate mcp-moat"
        echo "Then run this script again."
        exit 1
    fi

    conda activate mcp-moat || {
        print_error "Failed to activate mcp-moat environment"
        echo "Try running: conda activate mcp-moat"
        echo "Then run this script again."
        exit 1
    }
    print_success "Activated mcp-moat environment"
fi
print_info "Configuration:"
echo "  Video Directory: $VIDEO_DIR"
echo "  Text Output: $TXT_OUTPUT"
echo "  Blog Output: $BLOG_OUTPUT"
echo "  Summarize Output: $SUMMARIZE_OUTPUT"
echo "  Conda Environment: mcp-moat (active)"
echo ""

# Check if required directories exist or can be created
if [ ! -d "$VIDEO_DIR" ]; then
    print_error "Video directory does not exist: $VIDEO_DIR"
    echo "Please ensure the video directory exists and contains video files."
    exit 1
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed or not in PATH"
    exit 1
fi

# Check for ffmpeg (needed by whisper for video processing)
if ! command -v ffmpeg &> /dev/null; then
    print_error "ffmpeg is not installed"
    echo "Install with:"
    echo "  macOS: brew install ffmpeg"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  CentOS/RHEL: sudo yum install ffmpeg"
    exit 1
fi

# Check for required Python packages
print_info "Checking required Python packages..."
python3 -c "import whisper" 2>/dev/null || {
    print_error "whisper package not installed. Install with: pip install openai-whisper"
    exit 1
}



print_success "All prerequisites checked"
echo ""

# Create output directories if they don't exist
mkdir -p "$TXT_OUTPUT" "$BLOG_OUTPUT" "$SUMMARIZE_OUTPUT"

# Step 1: Video Transcriber
echo "Step 1/4: Running Video Transcriber..."
echo "-----------------------------------------"
if [ -f "step01_video_transcriber.py" ]; then
    python3 step01_video_transcriber.py --input "$VIDEO_DIR" --output "$TXT_OUTPUT"
    print_success "Step 1 completed"
else
    print_error "step01_video_transcriber.py not found"
    exit 1
fi
echo ""

# Step 2: Transcript Summarizer
echo "Step 2/4: Running Transcript Summarizer..."
echo "-----------------------------------------"
if [ -f "step02_transcript_summarizer.py" ]; then
    python3 step02_transcript_summarizer.py --input "$TXT_OUTPUT" --output "$BLOG_OUTPUT"
    print_success "Step 2 completed"
else
    print_error "step02_transcript_summarizer.py not found"
    exit 1
fi
echo ""

# Step 3: Rename Files
echo "Step 3/4: Renaming and Organizing Files..."
echo "-----------------------------------------"
if [ -f "step03_rename_files.py" ]; then
    python3 step03_rename_files.py --input "$BLOG_OUTPUT"
    print_success "Step 3 completed"
else
    print_error "step03_rename_files.py not found"
    exit 1
fi
echo ""

# Step 4: Summarizer Only
echo "Step 4/4: Running Final Summarizer..."
echo "-----------------------------------------"
if [ -f "step04_summarizer_only.py" ]; then
    python3 step04_summarizer_only.py -i "$BLOG_OUTPUT" -o "$SUMMARIZE_OUTPUT"
    print_success "Step 4 completed"
else
    print_error "step04_summarizer_only.py not found"
    exit 1
fi
echo ""

echo "========================================="
print_success "Video transcription pipeline completed!"
echo "========================================="
echo ""
echo "Output directories:"
echo "  Transcripts: $TXT_OUTPUT"
echo "  Blog posts: $BLOG_OUTPUT"
echo "  Summaries: $SUMMARIZE_OUTPUT"