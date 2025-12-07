import os
import whisper
import datetime
import argparse
import asyncio
import re
import time
from pathlib import Path
from progress_utils import ProgressTracker, setup_logging
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import yt_dlp

# Configure logging
logger = setup_logging(__name__)

# Document folder suffixes that trigger document processing
DOC_FOLDER_SUFFIXES = ('-doc', '-pdf', '-pptx', '-xlsx')

class VideoTranscriber:
    """A class to transcribe videos using Whisper with progress tracking"""

    def __init__(self, input_folder=None, output_folder=None):
        print("\n📚 Loading Whisper model...")
        self.model = whisper.load_model("base")
        print("✓ Model loaded successfully\n")
        self.progress_tracker = None

        # Set default paths if not provided
        if input_folder is None:
            self.desktop_path = str(Path.home() / "Desktop")
            self.source_folder = os.path.join(self.desktop_path, "wisdomhatch2")
        else:
            self.source_folder = input_folder

        if output_folder is None:
            self.output_folder = os.path.join(str(Path.home()), "cgithub", "mcp-moat", "wisdomhatch-txt")
        else:
            self.output_folder = output_folder

        logger.info(f"Input folder: {self.source_folder}")
        logger.info(f"Output folder: {self.output_folder}")
        
    def setup_output_folder(self):
        """Create output folder if it doesn't exist"""
        os.makedirs(self.output_folder, exist_ok=True)
        logger.info(f"Output folder ready at: {self.output_folder}")
    
    def get_video_files(self):
        """Get list of video and audio files from source folder"""
        video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma')
        video_files = []

        if not os.path.exists(self.source_folder):
            raise FileNotFoundError(f"Source folder not found: {self.source_folder}")

        for file in os.listdir(self.source_folder):
            if file.lower().endswith(video_extensions):
                video_files.append(os.path.join(self.source_folder, file))

        return sorted(video_files)  # Sort for consistent ordering
    
    def transcribe_video(self, video_path):
        """Transcribe a single video"""
        try:
            # Get base filename without extension
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(self.output_folder, f"{base_name}.txt")

            # Start tracking this item if tracker exists
            if self.progress_tracker:
                self.progress_tracker.start_item(base_name)

            # Perform transcription
            result = self.model.transcribe(video_path, fp16=False, verbose=False)

            # Update progress
            if self.progress_tracker:
                self.progress_tracker.update_progress(100, f"Completed {base_name}")

            # Save transcript
            start_time = datetime.datetime.now()
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"Transcript for: {base_name}\n")
                f.write(f"Transcription Date: {start_time}\n")
                f.write("=" * 50 + "\n\n")
                f.write(result["text"])

            # Mark as complete
            if self.progress_tracker:
                self.progress_tracker.complete_item(base_name, success=True)
                print(f"   ✓ Saved to: {os.path.basename(output_path)}")

            return output_path

        except Exception as e:
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            if self.progress_tracker:
                self.progress_tracker.complete_item(base_name, success=False)
            logger.error(f"Error transcribing {video_path}: {e}")
            raise
    
    def process_all_videos(self):
        """Process all videos with progress tracking"""
        try:
            # Setup output folder
            self.setup_output_folder()

            # Get list of video files
            video_files = self.get_video_files()

            if not video_files:
                logger.warning(f"No video or audio files found in {self.source_folder}")
                return

            # Initialize progress tracker
            self.progress_tracker = ProgressTracker(
                total_items=len(video_files),
                task_name="Video Transcription Pipeline"
            )
            self.progress_tracker.start()

            # Process each video
            for video_file in video_files:
                try:
                    output_path = self.transcribe_video(video_file)
                except Exception as e:
                    logger.error(f"Failed to process {video_file}: {e}")
                    continue

            # Show final summary
            self.progress_tracker.finish()
            print(f"  📁 Output directory: {self.output_folder}")

        except Exception as e:
            logger.error(f"Error in process_all_videos: {e}")
            raise


class DocumentTranscriber:
    """A class to transcribe documents (PDF, DOCX, PPTX, XLSX) using Claude Agent SDK Skills"""

    def __init__(self, input_folder=None, output_folder=None):
        self.progress_tracker = None

        # Set default paths if not provided
        if input_folder is None:
            self.desktop_path = str(Path.home() / "Desktop")
            self.source_folder = os.path.join(self.desktop_path, "documents")
        else:
            self.source_folder = input_folder

        if output_folder is None:
            self.output_folder = os.path.join(str(Path.home()), "cgithub", "mcp-moat", "documents-txt")
        else:
            self.output_folder = output_folder

        logger.info(f"Input folder: {self.source_folder}")
        logger.info(f"Output folder: {self.output_folder}")

    def setup_output_folder(self):
        """Create output folder if it doesn't exist"""
        os.makedirs(self.output_folder, exist_ok=True)
        logger.info(f"Output folder ready at: {self.output_folder}")

    def get_document_files(self):
        """Get list of document files from source folder"""
        doc_extensions = ('.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls')
        doc_files = []

        if not os.path.exists(self.source_folder):
            raise FileNotFoundError(f"Source folder not found: {self.source_folder}")

        for file in os.listdir(self.source_folder):
            if file.lower().endswith(doc_extensions):
                doc_files.append(os.path.join(self.source_folder, file))

        return sorted(doc_files)

    async def transcribe_document(self, doc_path):
        """Transcribe a single document using Claude Agent SDK Skills"""
        try:
            from claude_agent_sdk import query, ClaudeAgentOptions

            base_name = os.path.splitext(os.path.basename(doc_path))[0]
            output_path = os.path.join(self.output_folder, f"{base_name}.txt")
            file_ext = os.path.splitext(doc_path)[1].lower()

            # Start tracking this item if tracker exists
            if self.progress_tracker:
                self.progress_tracker.start_item(base_name)

            # Determine the appropriate skill based on file extension
            if file_ext in ('.pdf',):
                skill_type = "pdf"
            elif file_ext in ('.docx', '.doc'):
                skill_type = "docx"
            elif file_ext in ('.pptx', '.ppt'):
                skill_type = "pptx"
            elif file_ext in ('.xlsx', '.xls'):
                skill_type = "xlsx"
            else:
                raise ValueError(f"Unsupported file extension: {file_ext}")

            # Get project root directory (where .claude/skills/ exists)
            current_file = Path(__file__).resolve()
            project_root = current_file.parent

            logger.info(f"Project root: {project_root}")

            # Configure Claude Agent SDK options with Skills enabled
            # NOTE: No api_key passed - SDK uses existing Claude Code authentication
            options = ClaudeAgentOptions(
                cwd=str(project_root),
                setting_sources=["user", "project"],  # Load skills from .claude/skills/
                allowed_tools=[
                    "Skill",      # Required to execute skills
                    "Read",       # Required for reading document files
                    "Write",      # Required for writing extracted text
                    "Bash",       # May be needed for file operations
                    "Glob",       # For finding files
                    "Grep"        # For searching content
                ],
                max_turns=5  # Limit conversation turns to avoid large responses
            )

            # Create the prompt for document text extraction
            # IMPORTANT: Tell Claude to use Python libraries (from Skills) to avoid buffer overflow
            prompt = f"""Write and execute Python code to extract text from a {skill_type.upper()} file.

Input: {doc_path}
Output: {output_path}

IMPORTANT: Do NOT use the Read tool to read the document directly. Instead:
1. Write a Python script using pypdf/pdfplumber for PDFs (or appropriate library for other formats)
2. Execute the Python script with Bash tool
3. The script should extract text and save to the output file

The output file should have a header line with the filename, then all extracted text.

Confirm when done. Do not include extracted text in your response."""

            # Execute the query using Claude Agent SDK
            logger.info(f"Invoking Claude Agent SDK for {skill_type} extraction...")

            response_text = ""
            async for message in query(prompt=prompt, options=options):
                # Collect the output - messages may have .text attribute or be strings
                if hasattr(message, 'text'):
                    response_text += message.text + "\n"
                elif isinstance(message, str):
                    response_text += message + "\n"
                logger.debug(f"SDK message: {str(message)[:100]}...")

            # Update progress
            if self.progress_tracker:
                self.progress_tracker.update_progress(100, f"Completed {base_name}")

            # Verify the output file was created
            if os.path.exists(output_path):
                if self.progress_tracker:
                    self.progress_tracker.complete_item(base_name, success=True)
                    print(f"   ✓ Saved to: {os.path.basename(output_path)}")
            else:
                # If SDK didn't create the file, mark as failed
                logger.warning(f"Output file not created for {base_name}")
                logger.warning(f"SDK response: {response_text[:500]}...")
                if self.progress_tracker:
                    self.progress_tracker.complete_item(base_name, success=False)
                    print(f"   ✗ Failed to create: {os.path.basename(output_path)}")

            return output_path

        except ImportError as e:
            logger.error(f"Claude Agent SDK not installed. Please install with: pip install claude-agent-sdk")
            raise
        except Exception as e:
            base_name = os.path.splitext(os.path.basename(doc_path))[0]
            if self.progress_tracker:
                self.progress_tracker.complete_item(base_name, success=False)
            logger.error(f"Error transcribing {doc_path}: {e}")
            raise

    async def process_all_documents_async(self):
        """Process all documents with progress tracking (async version)"""
        try:
            # Setup output folder
            self.setup_output_folder()

            # Get list of document files
            doc_files = self.get_document_files()

            if not doc_files:
                logger.warning(f"No document files found in {self.source_folder}")
                return

            # Initialize progress tracker
            self.progress_tracker = ProgressTracker(
                total_items=len(doc_files),
                task_name="Document Transcription Pipeline"
            )
            self.progress_tracker.start()

            # Process each document
            for doc_file in doc_files:
                try:
                    output_path = await self.transcribe_document(doc_file)
                except Exception as e:
                    logger.error(f"Failed to process {doc_file}: {e}")
                    continue

            # Show final summary
            self.progress_tracker.finish()
            print(f"  📁 Output directory: {self.output_folder}")

        except Exception as e:
            logger.error(f"Error in process_all_documents: {e}")
            raise

    def process_all_documents(self):
        """Process all documents (sync wrapper)"""
        asyncio.run(self.process_all_documents_async())


class YouTubeTranscriber:
    """A class to transcribe YouTube videos and playlists using YouTube Transcript API"""

    def __init__(self, input_folder=None, output_folder=None):
        self.progress_tracker = None

        # Set default paths if not provided
        if input_folder is None:
            self.desktop_path = str(Path.home() / "Desktop")
            self.source_folder = os.path.join(self.desktop_path, "youtube")
        else:
            self.source_folder = input_folder

        if output_folder is None:
            self.output_folder = os.path.join(str(Path.home()), "cgithub", "mcp-moat", "youtube-txt")
        else:
            self.output_folder = output_folder

        logger.info(f"Input folder: {self.source_folder}")
        logger.info(f"Output folder: {self.output_folder}")

    def setup_output_folder(self):
        """Create output folder if it doesn't exist"""
        os.makedirs(self.output_folder, exist_ok=True)
        logger.info(f"Output folder ready at: {self.output_folder}")

    def get_youtube_files(self):
        """Get list of *_yt.txt or *-yt.txt files from source folder"""
        yt_files = []

        if not os.path.exists(self.source_folder):
            raise FileNotFoundError(f"Source folder not found: {self.source_folder}")

        for file in os.listdir(self.source_folder):
            if file.lower().endswith('_yt.txt') or file.lower().endswith('-yt.txt'):
                yt_files.append(os.path.join(self.source_folder, file))

        return sorted(yt_files)

    def extract_youtube_urls(self, file_path):
        """Extract YouTube URLs from _yt.txt file (one URL per line)"""
        urls = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and (line.startswith('http://') or line.startswith('https://')):
                        urls.append(line)
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            raise
        return urls

    def is_playlist_url(self, url):
        """Check if URL is a YouTube playlist"""
        return 'list=' in url

    def extract_video_id(self, url):
        """Extract video ID from various YouTube URL formats"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def extract_playlist_videos(self, url):
        """Extract video IDs and titles from a YouTube playlist using yt-dlp"""
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'force_generic_extractor': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if 'entries' in info:
                    videos = []
                    for entry in info['entries']:
                        if entry:
                            video_id = entry.get('id')
                            video_title = entry.get('title', f'video_{video_id}')
                            if video_id:
                                videos.append({
                                    'id': video_id,
                                    'title': video_title,
                                    'url': f'https://www.youtube.com/watch?v={video_id}'
                                })
                    return videos
                else:
                    # Single video
                    video_id = info.get('id')
                    video_title = info.get('title', f'video_{video_id}')
                    return [{
                        'id': video_id,
                        'title': video_title,
                        'url': url
                    }]
        except Exception as e:
            logger.error(f"Error extracting playlist info: {e}")
            raise

    def get_video_info(self, url):
        """Get video title and ID from a single video URL using yt-dlp"""
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_id = info.get('id')
                video_title = info.get('title', f'video_{video_id}')
                return {
                    'id': video_id,
                    'title': video_title,
                    'url': url
                }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            raise

    def convert_to_camel_case(self, title):
        """Convert video title to camelCase"""
        # Remove special characters and split into words
        words = re.sub(r'[^\w\s]', '', title).split()
        if not words:
            return 'untitled'

        # First word lowercase, rest title case, then join
        camel = words[0].lower() + ''.join(word.capitalize() for word in words[1:])
        return camel

    def transcribe_youtube_video(self, video_info, base_filename, counter):
        """Transcribe a single YouTube video"""
        try:
            video_id = video_info['id']
            video_title = video_info['title']
            video_url = video_info['url']

            # Create filename: <base>_<counter>_<camelCaseTitle>.txt
            camel_title = self.convert_to_camel_case(video_title)
            output_filename = f"{base_filename}_{counter:02d}_{camel_title}.txt"
            output_path = os.path.join(self.output_folder, output_filename)

            # Start tracking this item if tracker exists
            if self.progress_tracker:
                self.progress_tracker.start_item(f"{counter:02d}_{camel_title}")

            # Fetch transcript using YouTube Transcript API
            fetched_transcript = YouTubeTranscriptApi().fetch(video_id)

            # Combine all transcript segments
            full_transcript = ' '.join([snippet.text for snippet in fetched_transcript.snippets])

            # Save transcript
            start_time = datetime.datetime.now()
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"Transcript for: {video_title}\n")
                f.write(f"YouTube URL: {video_url}\n")
                f.write(f"Video ID: {video_id}\n")
                f.write(f"Transcription Date: {start_time}\n")
                f.write("=" * 50 + "\n\n")
                f.write(full_transcript)

            # Mark as complete
            if self.progress_tracker:
                self.progress_tracker.complete_item(f"{counter:02d}_{camel_title}", success=True)
                print(f"   ✓ Saved to: {output_filename}")

            return output_path

        except (TranscriptsDisabled, NoTranscriptFound) as e:
            logger.error(f"No transcript available for {video_info['title']}: {e}")
            if self.progress_tracker:
                self.progress_tracker.complete_item(f"{counter:02d}_{camel_title}", success=False)
            return None
        except Exception as e:
            logger.error(f"Error transcribing {video_info['title']}: {e}")
            if self.progress_tracker:
                self.progress_tracker.complete_item(f"{counter:02d}_{camel_title}", success=False)
            return None

    def process_youtube_url(self, url, base_filename, start_counter):
        """Process a single YouTube URL (video or playlist)"""
        videos_processed = 0

        try:
            if self.is_playlist_url(url):
                logger.info(f"Detected playlist URL: {url}")
                videos = self.extract_playlist_videos(url)
                logger.info(f"Found {len(videos)} videos in playlist")
            else:
                logger.info(f"Detected single video URL: {url}")
                video_info = self.get_video_info(url)
                videos = [video_info]

            # Process each video
            for i, video_info in enumerate(videos):
                counter = start_counter + i
                self.transcribe_youtube_video(video_info, base_filename, counter)
                videos_processed += 1

        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")

        return videos_processed

    def process_all_youtube(self):
        """Process all YouTube files with progress tracking and retry logic"""
        try:
            # Setup output folder
            self.setup_output_folder()

            # Get list of _yt.txt files
            yt_files = self.get_youtube_files()

            if not yt_files:
                logger.warning(f"No *_yt.txt files found in {self.source_folder}")
                return

            # Collect all video info with metadata
            all_videos = []
            for yt_file in yt_files:
                base_filename = os.path.splitext(os.path.basename(yt_file))[0]
                # Remove _yt or -yt suffix
                if base_filename.endswith('_yt'):
                    base_filename = base_filename[:-3]
                elif base_filename.endswith('-yt'):
                    base_filename = base_filename[:-3]

                urls = self.extract_youtube_urls(yt_file)
                counter = 1

                for url in urls:
                    try:
                        if self.is_playlist_url(url):
                            logger.info(f"Detected playlist URL: {url}")
                            videos = self.extract_playlist_videos(url)
                            logger.info(f"Found {len(videos)} videos in playlist")
                            for video in videos:
                                all_videos.append({
                                    'video_info': video,
                                    'base_filename': base_filename,
                                    'counter': counter,
                                    'status': 'pending'
                                })
                                counter += 1
                        else:
                            logger.info(f"Detected single video URL: {url}")
                            video_info = self.get_video_info(url)
                            all_videos.append({
                                'video_info': video_info,
                                'base_filename': base_filename,
                                'counter': counter,
                                'status': 'pending'
                            })
                            counter += 1
                    except Exception as e:
                        logger.error(f"Error processing URL {url}: {e}")

            if not all_videos:
                logger.warning("No valid YouTube URLs found")
                return

            # Initialize progress tracker
            self.progress_tracker = ProgressTracker(
                total_items=len(all_videos),
                task_name="YouTube Transcript Pipeline"
            )
            self.progress_tracker.start()

            # Process videos with retry logic
            max_retries = 4
            retry_delay = 3  # seconds

            for retry_round in range(max_retries):
                failed_videos = [v for v in all_videos if v['status'] == 'pending']

                if not failed_videos:
                    break

                if retry_round > 0:
                    print(f"\n🔄 Retry round {retry_round}: Processing {len(failed_videos)} failed videos...")
                    print(f"⏳ Waiting {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)

                for video_item in failed_videos:
                    result = self.transcribe_youtube_video(
                        video_item['video_info'],
                        video_item['base_filename'],
                        video_item['counter']
                    )

                    if result:
                        video_item['status'] = 'success'
                    else:
                        video_item['status'] = 'pending'  # Will retry in next round

            # Show final summary
            self.progress_tracker.finish()
            print(f"  📁 Output directory: {self.output_folder}")

        except Exception as e:
            logger.error(f"Error in process_all_youtube: {e}")
            raise


def is_document_folder(folder_path):
    """Check if the folder is meant for document processing based on its suffix"""
    folder_name = os.path.basename(folder_path.rstrip(os.sep)).lower()
    return any(folder_name.endswith(suffix) for suffix in DOC_FOLDER_SUFFIXES)


def has_youtube_files(folder_path):
    """Check if the folder contains any *_yt.txt or *-yt.txt files"""
    if not folder_path or not os.path.exists(folder_path):
        return False

    for file in os.listdir(folder_path):
        if file.lower().endswith('_yt.txt') or file.lower().endswith('-yt.txt'):
            return True
    return False


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Transcribe videos using Whisper')
    parser.add_argument('-i', '--input', dest='input_folder', 
                        help='Input folder containing video files')
    parser.add_argument('-o', '--output', dest='output_folder',
                        help='Output folder for transcript files')
    return parser.parse_args()

def main():
    """Main function to run the video, document, or YouTube transcription process"""
    try:
        # Parse command line arguments
        args = parse_arguments()

        # Determine which transcription pipeline to use
        input_folder = args.input_folder

        # Priority: YouTube files > Document folder > Video/Audio folder
        if input_folder and has_youtube_files(input_folder):
            # YouTube processing pipeline
            print("\n📺 YouTube files detected, using YouTube Transcript API...")
            transcriber = YouTubeTranscriber(
                input_folder=args.input_folder,
                output_folder=args.output_folder
            )
            transcriber.process_all_youtube()
            logger.info("YouTube transcription process completed")
        elif input_folder and is_document_folder(input_folder):
            # Document processing pipeline
            print("\n📄 Document folder detected, using Claude Agent SDK Skills for text extraction...")
            transcriber = DocumentTranscriber(
                input_folder=args.input_folder,
                output_folder=args.output_folder
            )
            transcriber.process_all_documents()
            logger.info("Document transcription process completed")
        else:
            # Video/Audio processing pipeline (original behavior)
            print("\n🎥 Video/Audio folder detected, using Whisper for transcription...")
            transcriber = VideoTranscriber(
                input_folder=args.input_folder,
                output_folder=args.output_folder
            )
            transcriber.process_all_videos()
            logger.info("Video transcription process completed")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main()