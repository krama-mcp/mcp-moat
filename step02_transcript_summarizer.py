import os
import logging
from pathlib import Path
from typing import List, Dict, Set
import requests
import datetime
import json
from time import sleep
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TranscriptSummarizer:
    """A class to summarize transcripts using the Fireworks AI API"""
    
    def __init__(self):
        self.base_path = str(Path.home() / "cgithub" / "mcp-moat")
        self.input_folder = os.path.join(self.base_path, "wisdomhatch-txt")
        self.output_folder = os.path.join(self.base_path, "wisdomhatch-blog")
        
        # Fireworks AI API configuration
        self.api_url = "https://router.huggingface.co/fireworks-ai/inference/v1/chat/completions"
        self.api_key = os.getenv('HUGGINGFACE_API_KEY')
        
        if not self.api_key or self.api_key == 'your_api_key_here':
            raise ValueError(
                "Please set your Hugging Face API key in the .env file\n"
                "1. Open mcp-moat/.env\n"
                "2. Replace 'your_api_key_here' with your actual API key\n"
                "3. Save the file and run the script again"
            )
            
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
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
        """Query the Fireworks AI API with streaming response"""
        response = requests.post(self.api_url, headers=self.headers, json=payload, stream=True)
        
        if response.status_code == 429:  # Rate limit exceeded
            logger.warning("Rate limit exceeded. Waiting before retry...")
            sleep(self.retry_delay)
            raise Exception("Rate limit exceeded")
        elif response.status_code == 402:  # Payment required
            logger.error("API quota exceeded. Please upgrade your plan.")
            raise Exception("API quota exceeded")
        elif response.status_code != 200:
            raise Exception(f"API request failed with status code: {response.status_code}")
            
        for line in response.iter_lines():
            if not line.startswith(b"data:"):
                continue
            if line.strip() == b"data: [DONE]":
                return
            yield json.loads(line.decode("utf-8").lstrip("data:").rstrip("/n"))
        
        sleep(self.request_delay)  # Rate limiting delay
    
    def generate_summary(self, text: str) -> Dict[str, str]:
        """Generate summary and key takeaways using the Fireworks AI API"""
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
            "max_tokens": 20000,
            "model": "accounts/fireworks/models/deepseek-v3-0324",
            "stream": True
        }
        
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                # Collect the streamed response
                full_response = ""
                chunks = self.query_api(payload)
                
                for chunk in chunks:
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            full_response += delta["content"]
                
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
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"Error in API request: {e}")
                retry_count += 1
                
                if "API quota exceeded" in str(e):
                    logger.error("API quota exceeded. Stopping processing.")
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
        """Process all transcripts that haven't been processed yet"""
        try:
            # Setup output folder
            self.setup_folders()
            
            # Get list of unprocessed transcript files
            transcript_files = self.get_transcript_files()
            
            if not transcript_files:
                logger.info("No new transcript files to process")
                return
            
            logger.info(f"Found {len(transcript_files)} new transcript files to process")
            
            # Process each transcript
            for transcript_file in transcript_files:
                try:
                    self.process_transcript(transcript_file)
                except Exception as e:
                    if "API quota exceeded" in str(e):
                        logger.error("API quota exceeded. Stopping all processing.")
                        break
                    logger.error(f"Failed to process {transcript_file}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in process_all_transcripts: {e}")
            raise

def main():
    """Main function to run the transcript summarization process"""
    try:
        summarizer = TranscriptSummarizer()
        summarizer.process_all_transcripts()
        logger.info("Transcript summarization process completed")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main() 