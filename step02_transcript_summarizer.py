import os
from pathlib import Path
from typing import List, Dict, Set
import requests
import datetime
import json
import argparse
from time import sleep
from dotenv import load_dotenv
from progress_utils import ProgressTracker, setup_logging

# Load environment variables
load_dotenv()

# Configure logging
logger = setup_logging(__name__)

class TranscriptSummarizer:
    """A class to summarize transcripts using the Fireworks AI API"""
    
    def __init__(self, input_folder=None, output_folder=None):
        self.base_path = str(Path.home() / "cgithub" / "mcp-moat")
        
        # Set default paths if not provided
        if input_folder is None:
            self.input_folder = os.path.join(self.base_path, "wisdomhatch-txt")
        else:
            self.input_folder = input_folder
            
        if output_folder is None:
            self.output_folder = os.path.join(self.base_path, "wisdomhatch-blog")
        else:
            self.output_folder = output_folder
            
        logger.info(f"Input folder: {self.input_folder}")
        logger.info(f"Output folder: {self.output_folder}")
        
        # Azure OpenAI API configuration
        self.api_key = os.getenv('AZURE_OPENAI_API_KEY')
        self.api_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT')
        self.api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
        
        # Construct the API URL
        self.api_url = f"{self.api_endpoint}openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
        
        if not self.api_key or self.api_key == 'your_api_key_here' or not self.api_endpoint:
            raise ValueError(
                "Please set your Azure OpenAI API credentials in the .env file\n"
                "1. Open mcp-moat/.env\n"
                "2. Replace the placeholder values with your actual Azure OpenAI credentials\n"
                "3. Save the file and run the script again"
            )
            
        self.headers = {
            "api-key": f"{self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Rate limiting configuration
        self.request_delay = 2  # Delay between requests in seconds
        self.retry_delay = 60   # Delay when hitting rate limits
        self.max_retries = 5    # Maximum number of retries per chunk
        
    def setup_folders(self):
        """Create output folder if it doesn't exist"""
        os.makedirs(self.output_folder, exist_ok=True)
        logger.info(f"Output folder ready at: {self.output_folder}")
    
    def get_processed_files(self) -> Set[str]:
        """Get set of base names of already processed files"""
        processed = set()
        if os.path.exists(self.output_folder):
            for file in os.listdir(self.output_folder):
                if file.endswith('.txt'):
                    # Remove _partX.txt from the end to get base name
                    base_name = file.rsplit('_part', 1)[0]
                    processed.add(base_name)
        return processed
        
    def get_transcript_files(self) -> List[str]:
        """Get list of transcript files from input folder that haven't been processed yet"""
        if not os.path.exists(self.input_folder):
            raise FileNotFoundError(f"Input folder not found: {self.input_folder}")
        
        # Get already processed files
        processed_files = self.get_processed_files()
        
        # Filter out already processed files
        unprocessed_files = []
        for f in os.listdir(self.input_folder):
            if f.endswith('.txt'):
                base_name = os.path.splitext(f)[0]
                if base_name not in processed_files:
                    unprocessed_files.append(os.path.join(self.input_folder, f))
                else:
                    logger.info(f"Skipping {base_name} - already processed")
        
        return unprocessed_files
    
    def chunk_text(self, text: str, chunk_size: int = 10000) -> List[str]:
        """Split text into chunks of specified size"""
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    
    def query_api(self, payload):
        """Query the Azure OpenAI API"""
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=120
            )
            
            if response.status_code == 429:  # Rate limit exceeded
                logger.warning("Rate limit exceeded. Waiting before retry...")
                sleep(self.retry_delay)
                raise Exception("Rate limit exceeded")
            elif response.status_code == 401:  # Unauthorized
                logger.error("API authentication failed. Check your API key.")
                raise Exception("API authentication failed")
            elif response.status_code == 400:  # Bad request
                logger.error(f"Bad request: {response.text}")
                raise Exception(f"Bad request: {response.text}")
            elif response.status_code != 200:
                logger.error(f"API request failed with status code: {response.status_code}, response: {response.text}")
                raise Exception(f"API request failed with status code: {response.status_code}")
                
            # Parse the response
            json_response = response.json()
            return json_response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise
        finally:
            sleep(self.request_delay)  # Rate limiting delay
    
    def generate_summary(self, text: str) -> Dict[str, str]:
        """Generate summary and key takeaways using the Azure OpenAI API"""
        # Prepare the text for summarization
        text_to_summarize = text[:10000]  # Using full chunk size of 10000 characters
        
        prompt = f"""Please analyze the following text and provide:
1. A concise summary
2. Key takeaways and important points

Text to analyze:
{text_to_summarize}

Please format your response as:
Summary:
[Your summary here]

Key Takeaways:
- [First takeaway]
- [Additional takeaways]
"""
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 4000,
            "temperature": 0
        }
        
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                # Make API request
                response = self.query_api(payload)
                
                # Extract the response content
                if "choices" in response and len(response["choices"]) > 0:
                    full_response = response["choices"][0]["message"]["content"].strip()
                    
                    # Extract summary and takeaways from response
                    parts = full_response.split("Summary:")
                    if len(parts) > 1:
                        content = parts[1].strip()
                        summary_parts = content.split("Key Takeaways:")
                        
                        summary = summary_parts[0].strip()
                        takeaways = summary_parts[1].strip() if len(summary_parts) > 1 else ""
                        
                        return {
                            "summary": summary,
                            "takeaways": takeaways
                        }
                    else:
                        return {
                            "summary": full_response.strip(),
                            "takeaways": "No specific takeaways extracted."
                        }
                else:
                    raise Exception("Invalid response format from API")
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"Error in API request: {e}")
                retry_count += 1
                
                if "authentication failed" in str(e).lower():
                    logger.error("API authentication failed. Check your API key.")
                    raise
                    
                if retry_count < self.max_retries:
                    sleep_time = self.retry_delay * retry_count
                    logger.info(f"Waiting {sleep_time} seconds before retry {retry_count + 1}/{self.max_retries}")
                    sleep(sleep_time)
                    continue
                raise Exception(f"Max retries reached. Last error: {last_error}")
    
    def process_transcript(self, file_path: str):
        """Process a single transcript file"""
        try:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            logger.info(f"Processing transcript: {base_name}")
            
            # Read the transcript
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into chunks
            chunks = self.chunk_text(content)
            logger.info(f"Split into {len(chunks)} chunks")
            
            # Process each chunk
            for i, chunk in enumerate(chunks, 1):
                try:
                    # Check if this specific part exists
                    output_file = os.path.join(
                        self.output_folder,
                        f"{base_name}_part{i}.txt"
                    )
                    
                    if os.path.exists(output_file):
                        logger.info(f"Skipping {base_name} part {i} - already exists")
                        continue
                    
                    # Generate summary
                    result = self.generate_summary(chunk)
                    
                    # Create output file
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"Summary for: {base_name} - Part {i}\n")
                        f.write(f"Generated on: {datetime.datetime.now()}\n")
                        f.write("=" * 50 + "\n\n")
                        f.write("SUMMARY:\n")
                        f.write(result['summary'])
                        f.write("\n\nKEY TAKEAWAYS:\n")
                        f.write(result['takeaways'])
                        f.write("\n\nORIGINAL TEXT:\n")
                        f.write(chunk)
                    
                    logger.info(f"Saved summary part {i} to: {output_file}")
                    
                except Exception as e:
                    if "API quota exceeded" in str(e):
                        raise
                    logger.error(f"Error processing chunk {i} of {base_name}: {e}")
                    continue
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            raise
    
    def process_all_transcripts(self):
        """Process all transcripts with progress tracking"""
        try:
            # Setup output folder
            self.setup_folders()

            # Get list of unprocessed transcript files
            transcript_files = self.get_transcript_files()

            if not transcript_files:
                logger.info("No new transcript files to process")
                return

            # Initialize progress tracker
            progress_tracker = ProgressTracker(
                total_items=len(transcript_files),
                task_name="Transcript Summarization"
            )
            progress_tracker.start()

            # Process each transcript
            for transcript_file in transcript_files:
                try:
                    file_name = os.path.basename(transcript_file)
                    progress_tracker.start_item(file_name)

                    self.process_transcript(transcript_file)

                    progress_tracker.complete_item(file_name, success=True)
                except Exception as e:
                    file_name = os.path.basename(transcript_file)
                    progress_tracker.complete_item(file_name, success=False)

                    if "API quota exceeded" in str(e):
                        logger.error("API quota exceeded. Stopping all processing.")
                        break
                    logger.error(f"Failed to process {transcript_file}: {e}")
                    continue

            # Show final summary
            progress_tracker.finish()
            print(f"  📁 Output directory: {self.output_folder}")

        except Exception as e:
            logger.error(f"Error in process_all_transcripts: {e}")
            raise

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Summarize transcripts using Fireworks AI API')
    parser.add_argument('-i', '--input', dest='input_folder', 
                        help='Input folder containing transcript files')
    parser.add_argument('-o', '--output', dest='output_folder',
                        help='Output folder for summary files')
    return parser.parse_args()

def main():
    """Main function to run the transcript summarization process"""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Create summarizer with provided arguments
        summarizer = TranscriptSummarizer(
            input_folder=args.input_folder,
            output_folder=args.output_folder
        )
        
        summarizer.process_all_transcripts()
        logger.info("Transcript summarization process completed")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main() 