import os
import whisper
import datetime
import argparse
from pathlib import Path
from progress_utils import ProgressTracker, setup_logging

# Configure logging
logger = setup_logging(__name__)

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
        """Get list of video files from source folder"""
        video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.wmv')
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
                logger.warning(f"No video files found in {self.source_folder}")
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

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Transcribe videos using Whisper')
    parser.add_argument('-i', '--input', dest='input_folder', 
                        help='Input folder containing video files')
    parser.add_argument('-o', '--output', dest='output_folder',
                        help='Output folder for transcript files')
    return parser.parse_args()

def main():
    """Main function to run the video transcription process"""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Create transcriber with provided arguments
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