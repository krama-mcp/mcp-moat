# MCP Moat

A comprehensive media transcription and content publishing pipeline for converting videos/audio into blog posts and publishing them to GitHub.

## Description

This repository provides an end-to-end workflow for:
1. Transcribing video/audio content
2. Summarizing transcripts into structured blog posts
3. Generating engaging LinkedIn posts
4. Publishing content to GitHub repositories

## Quick Start

### Setup Environment

```bash
# Clone the repository
git clone https://github.com/krama-mcp/mcp-moat.git
cd mcp-moat

# Run setup script (creates conda environment and installs dependencies)
bash setup_env.sh

# Activate the environment
conda activate mcp-moat
```

### Complete Pipeline (Media → Blog Posts)

Use `run01_all_steps.sh` to transcribe media and generate summaries:

```bash
# Transcribe videos and generate blog posts
./run01_all_steps.sh ~/path/to/videos

# Output folders created automatically:
#   {name}-txt        - Transcripts
#   {name}-blog       - Blog-style summaries
#   {name}-summarize  - Key takeaways only
```

### Post to GitHub Pipeline

Use `run02_post_to_github.sh` to generate LinkedIn posts and push to GitHub:

```bash
# Generate posts and push to GitHub
./run02_post_to_github.sh wisdomhatch-summarize

# Or without the -summarize suffix (it will be added automatically)
./run02_post_to_github.sh wisdomhatch

# Output:
#   {name}-post       - LinkedIn posts (locally)
#   GitHub repository - Posts published to _posts/
```

## Individual Scripts

### Step 1: Video Transcription (step01_video_transcriber.py)

Transcribes video/audio files into text using OpenAI's Whisper model.

**Usage:**
```bash
python step01_video_transcriber.py -i <input_folder> -o <output_folder>
```

**Options:**
- `-i, --input`: Directory containing video/audio files to transcribe
- `-o, --output`: Directory where transcript text files will be saved

**Features:**
- Supports multiple formats: mp4, avi, mov, mkv, mp3, wav, m4a, etc.
- Progress tracking with time estimates
- Automatic chunk processing for large files

---

### Step 2: Transcript Summarization (step02_transcript_summarizer.py)

Summarizes transcript text files using Azure OpenAI API, generating blog-style content.

**Usage:**
```bash
python step02_transcript_summarizer.py -i <input_directory> -o <output_directory>
```

**Options:**
- `-i, --input`: Directory containing transcript text files
- `-o, --output`: Directory where summarized blog files will be saved

**Output Format:**
- Summary section
- Key takeaways (bullet points)
- Original transcript text

---

### Step 3: File Renaming (step03_rename_files.py)

Renames files based on session numbers and patterns to ensure consistent naming.

**Usage:**
```bash
python step03_rename_files.py -d <directory>
```

**Options:**
- `-d, --directory`: Directory containing files to rename

**Features:**
- Adds serial number prefixes (001-, 002-, etc.)
- Organizes files by session
- Groups multi-part files

---

### Step 4: Key Takeaways Extractor (step04_summarizer_only.py)

Extracts only the KEY TAKEAWAYS section from blog files.

**Usage:**
```bash
python step04_summarizer_only.py -i <input_directory> -o <output_directory>
```

**Options:**
- `-i, --input`: Directory containing blog files with KEY TAKEAWAYS sections
- `-o, --output`: Directory where extracted KEY TAKEAWAYS will be saved

**Features:**
- Extracts key takeaways from blog posts
- Handles multi-part files automatically
- Only processes files with KEY TAKEAWAYS content

---

### Step 5: LinkedIn Post Generator (step05_generate_linkedin_post.py)

Generates engaging LinkedIn posts from key takeaways using Azure OpenAI API.

**Usage:**
```bash
python step05_generate_linkedin_post.py -i <input_folder> [-o <output_folder>]
```

**Options:**
- `-i, --input`: Input folder containing key takeaways files (typically `*-summarize`)
- `-o, --output`: Output folder for LinkedIn posts (default: auto-generated with `-post` suffix)

**Features:**
- Merges multi-part files automatically
- Generates structured posts with:
  - Catchy intro
  - Emoji-enhanced bullet points
  - Relevant hashtags
  - Engagement questions
- Jekyll-compatible frontmatter
- Progress tracking

**Example:**
```bash
# Auto-generates wisdomhatch-post folder
python step05_generate_linkedin_post.py -i wisdomhatch-summarize

# Custom output folder
python step05_generate_linkedin_post.py -i ryan-summarize -o ryan-posts
```

---

### Step 6: GitHub Publisher (step06_push_to_github.py)

Pushes blog posts from a folder to a GitHub repository.

**Usage:**
```bash
python step06_push_to_github.py -i <input_folder> [-r <repo_name>] [-d <remote_dir>]
```

**Options:**
- `-i, --input`: Input folder containing blog post files (required)
- `-r, --repo`: GitHub repository name (format: username/repo, default: kiranramanna/thinkit)
- `-d, --dir`: Remote directory in the repository (default: _posts)

**Features:**
- Extracts pure content (excludes "Original Key Takeaways" sections)
- Generates GitHub-compatible filenames from frontmatter
- Preserves original dates when updating existing files
- Creates new files or updates existing ones
- Progress tracking with success/failure counts

**Example:**
```bash
# Push to default repository
python step06_push_to_github.py -i wisdomhatch-post

# Push to custom repository
python step06_push_to_github.py -i ryan-post -r username/other-repo
```

**Environment Variables Required:**
```bash
# Add to .env file
GITHUB_TOKEN_THINKIT=your_github_personal_access_token
```

## Automated Workflows

### run01_all_steps.sh - Complete Transcription Pipeline

Runs steps 1-4 automatically: transcription → summarization → renaming → key takeaways extraction.

**Usage:**
```bash
./run01_all_steps.sh [MEDIA_DIR] [OPTIONS]
```

**Options:**
- `-t, --txt-output DIR`: Override text output directory
- `-b, --blog-output DIR`: Override blog output directory
- `-s, --summarize-output DIR`: Override summarize output directory
- `-h, --help`: Show help message

**Examples:**
```bash
# Auto-generates output folders
./run01_all_steps.sh ~/Desktop/my-videos
# Creates: my-videos-txt, my-videos-blog, my-videos-summarize

# With custom output directories
./run01_all_steps.sh ~/Desktop/conference-talks -t transcripts -b summaries
```

**Features:**
- Auto-detects conda environment
- Validates prerequisites (ffmpeg, Python packages)
- Can skip transcription if `-txt` folder already exists
- Progress tracking for each step

---

### run02_post_to_github.sh - Post to GitHub Pipeline

Runs steps 5-6 automatically: LinkedIn post generation → GitHub publishing.

**Usage:**
```bash
./run02_post_to_github.sh [INPUT_FOLDER] [OPTIONS]
```

**Options:**
- `-o, --output DIR`: Override post output directory
- `-r, --repo NAME`: GitHub repository (default: kiranramanna/thinkit)
- `-h, --help`: Show help message

**Folder Name Logic:**
- **With `-summarize` suffix**: Uses folder as-is
  - Input: `wisdomhatch-summarize` → Output: `wisdomhatch-post`
- **Without `-summarize` suffix**: Appends `-summarize` and validates
  - Input: `yc-startuppicker` → Looks for: `yc-startuppicker-summarize` → Output: `yc-startuppicker-post`

**Examples:**
```bash
# With -summarize suffix
./run02_post_to_github.sh wisdomhatch-summarize
# Uses: wisdomhatch-summarize → Creates: wisdomhatch-post

# Without -summarize suffix
./run02_post_to_github.sh yc-startuppicker
# Looks for: yc-startuppicker-summarize → Creates: yc-startuppicker-post

# Custom repository
./run02_post_to_github.sh ryan-summarize -r username/other-repo

# Custom output folder
./run02_post_to_github.sh wisdomhatch-summarize -o my-posts
```

**Features:**
- Auto-detects conda environment
- Validates input folder exists and has content
- Generates LinkedIn posts with AI
- Pushes to GitHub with preserved dates
- Progress tracking for both steps

## Configuration

### Required Environment Variables

Create a `.env` file in the project root:

```bash
# Azure OpenAI API (for summarization and post generation)
AZURE_OPENAI_API_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# GitHub Publishing
GITHUB_TOKEN_THINKIT=your_github_personal_access_token
```

### Dependencies

All dependencies are managed via `requirements.txt` and installed automatically by `setup_env.sh`:

- openai-whisper - Audio/video transcription
- PyGithub - GitHub API integration
- requests - HTTP requests
- python-dotenv - Environment variable management
- PyPDF2, pdfplumber - PDF processing
- langdetect - Language detection

## Workflow Examples

### Example 1: Complete Pipeline from Videos to GitHub

```bash
# Step 1: Transcribe and summarize videos
./run01_all_steps.sh ~/Videos/podcast-episodes
# Output: podcast-episodes-txt, podcast-episodes-blog, podcast-episodes-summarize

# Step 2: Generate posts and push to GitHub
./run02_post_to_github.sh podcast-episodes
# Output: podcast-episodes-post (local + GitHub)
```

### Example 2: Using Existing Transcripts

```bash
# Skip transcription if you already have transcripts in a -txt folder
./run01_all_steps.sh ~/existing-transcripts-txt
# Skips step 1, runs steps 2-4

# Then publish
./run02_post_to_github.sh existing-transcripts-summarize
```

### Example 3: Custom Workflow

```bash
# Run individual steps with full control
python step01_video_transcriber.py -i videos -o transcripts
python step02_transcript_summarizer.py -i transcripts -o blogs
python step03_rename_files.py -d blogs
python step04_summarizer_only.py -i blogs -o summaries
python step05_generate_linkedin_post.py -i summaries -o posts
python step06_push_to_github.py -i posts -r username/my-blog
```

## Troubleshooting

### Common Issues

**1. "ModuleNotFoundError: No module named 'github'"**
```bash
# Run setup script to install dependencies
bash setup_env.sh
conda activate mcp-moat
```

**2. "ffmpeg is not installed"**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Or via conda
conda install -c conda-forge ffmpeg
```

**3. "GitHub API authentication failed"**
- Ensure `GITHUB_TOKEN_THINKIT` is set in your `.env` file
- Create a token at: https://github.com/settings/tokens
- Required permissions: `repo` (full control of private repositories)

**4. "No .md files found in input folder"**
- Verify the input folder exists and contains `.md` files
- Check folder naming (should end with `-summarize` or script will append it)

## Contributing

Feel free to submit issues and pull requests.

## License

This project is licensed under the MIT License.