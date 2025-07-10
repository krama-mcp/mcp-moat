# MCP Moat

A sample repository for demonstrating project setup and Git workflow.

## Description

This repository serves as a template for setting up new projects. It demonstrates basic repository structure and Git workflow practices.

## Transcript Processing Pipeline

This repository contains a series of scripts for processing video transcripts:

### Step 1: Video Transcription (step01_video_transcriber.py)

Transcribes video files into text using the Whisper model.

**Usage:**
```bash
python step01_video_transcriber.py -i <input_folder> -o <output_folder>
```

- `-i, --input`: Directory containing video files to transcribe
- `-o, --output`: Directory where transcript text files will be saved

### Step 2: Transcript Summarization (step02_transcript_summarizer.py)

Summarizes transcript text files using the Fireworks AI API, generating blog-style content with summary, key takeaways, and original text sections.

**Usage:**
```bash
python step02_transcript_summarizer.py -i <input_directory> -o <output_directory>
```

- `-i, --input`: Directory containing transcript text files
- `-o, --output`: Directory where summarized blog files will be saved

### Step 3: File Renaming (step03_rename_files.py)

Renames files based on session numbers and other patterns to ensure consistent naming.

**Usage:**
```bash
python step03_rename_files.py -d <directory>
```

- `-d, --directory`: Directory containing files to rename

### Step 4: Key Takeaways Extractor (step4_summarizer_only.py)

Extracts only the KEY TAKEAWAYS section from blog files. Only creates output files for inputs that contain a KEY TAKEAWAYS section.

**Usage:**
```bash
python step4_summarizer_only.py -i <input_directory> -o <output_directory>
```

- `-i, --input`: Directory containing blog files with KEY TAKEAWAYS sections
- `-o, --output`: Directory where extracted KEY TAKEAWAYS will be saved

## Getting Started

To get started with this project:

1. Clone the repository
```bash
git clone https://github.com/krama-mcp/mcp-moat.git
cd mcp-moat
```

2. Make your changes
3. Push your changes

## Contributing

Feel free to submit issues and pull requests.

## License

This project is licensed under the MIT License.