import os
import whisper
import datetime
import argparse
import asyncio
from pathlib import Path
from progress_utils import ProgressTracker, setup_logging

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


def is_document_folder(folder_path):
    """Check if the folder is meant for document processing based on its suffix"""
    folder_name = os.path.basename(folder_path.rstrip(os.sep)).lower()
    return any(folder_name.endswith(suffix) for suffix in DOC_FOLDER_SUFFIXES)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Transcribe videos using Whisper')
    parser.add_argument('-i', '--input', dest='input_folder', 
                        help='Input folder containing video files')
    parser.add_argument('-o', '--output', dest='output_folder',
                        help='Output folder for transcript files')
    return parser.parse_args()

def main():
    """Main function to run the video or document transcription process"""
    try:
        # Parse command line arguments
        args = parse_arguments()

        # Determine if we should use document or video transcription
        input_folder = args.input_folder

        if input_folder and is_document_folder(input_folder):
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