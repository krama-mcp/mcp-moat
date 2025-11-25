#!/usr/bin/env python3
"""
step05_generate_linkedin_post.py

This script processes key takeaways from blog files, merges all parts of the same file,
and generates engaging LinkedIn posts using Azure OpenAI API.

The script automatically:
1. Groups files by base name (e.g., all files with "StepByStepClass1_part*" are grouped)
2. Merges all parts in order
3. Extracts key takeaways from the merged content
4. Generates an engaging LinkedIn post for each source
5. If multiple source files exist (>1), automatically creates a "merged-final-post.md"
   that synthesizes all individual posts into one cohesive viral post

Usage:
    # Using default behavior (auto-generates output folder with "-post" suffix)
    python step05_generate_linkedin_post.py -i /path/to/ryan-summarize
    # Output will be saved to /path/to/ryan-post

    # Specify custom input and output directories
    python step05_generate_linkedin_post.py -i <input_directory> -o <output_directory>

Example:
    python step05_generate_linkedin_post.py -i /Users/kiran.ramanna/Documents/github/mcp-moat/ryan-summarize

    # If toon-summarize has 3 different sources:
    # - can_you_reference_internet.md
    # - 005-compass_artifact.md
    # - data2_analysis.md
    #
    # Output in toon-post will be:
    # - can_you_reference_internet.md (individual post)
    # - 005-compass_artifact.md (individual post)
    # - data2_analysis.md (individual post)
    # - merged-final-post.md (synthesized from all 3 posts)
"""

import os
import re
import argparse
import requests
from pathlib import Path
from time import sleep
from collections import defaultdict
from dotenv import load_dotenv
from progress_utils import ProgressTracker, setup_logging

# Load environment variables
load_dotenv()

# Configure logging
logger = setup_logging(__name__)


class LinkedInPostGenerator:
    """A class to generate LinkedIn posts from key takeaways using Azure OpenAI API"""

    def __init__(self, input_folder=None, output_folder=None):
        """
        Initialize the LinkedIn post generator

        Args:
            input_folder: Directory containing key takeaways files
            output_folder: Directory where LinkedIn posts will be saved
        """
        # Use provided input folder or default
        if input_folder is None:
            base_path = str(Path.home() / "cgithub" / "mcp-moat")
            self.input_folder = os.path.join(base_path, "wisdomhatch-summarize")
        else:
            self.input_folder = input_folder

        # Auto-generate output folder name with "-post" suffix if not provided
        if output_folder is None:
            # Extract the folder name and replace "-summarize" with "-post"
            input_path = Path(self.input_folder)
            folder_name = input_path.name

            if folder_name.endswith("-summarize"):
                output_folder_name = folder_name.replace("-summarize", "-post")
            else:
                output_folder_name = f"{folder_name}-post"

            self.output_folder = str(input_path.parent / output_folder_name)
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
        self.max_retries = 5    # Maximum number of retries per request

    def setup_folders(self):
        """Create output folder if it doesn't exist"""
        os.makedirs(self.output_folder, exist_ok=True)
        logger.info(f"Output folder ready at: {self.output_folder}")

    def get_base_name(self, filename):
        """
        Extract the base name from a filename, removing part numbers, serial prefixes, and extensions

        Args:
            filename: The filename to process

        Returns:
            Base name without part numbers, serial prefixes, and extensions
        """
        # Remove extension
        name_without_ext = os.path.splitext(filename)[0]

        # Remove serial number prefix if present (e.g., 001-, 002-, etc.)
        name_without_serial = re.sub(r'^\d+-', '', name_without_ext)

        # Remove part suffixes - handles multiple patterns:
        # --part01 (double dash), -part01 (single dash), _part1 (underscore)
        base_name = re.sub(r'\s*[-_]+part\d+$', '', name_without_serial)

        return base_name

    def get_part_number(self, filename):
        """
        Extract the part number from a filename

        Args:
            filename: The filename to process

        Returns:
            Part number as integer, or 0 if no part number found
        """
        # Match patterns: --part01, -part01, _part1
        match = re.search(r'[-_]+part(\d+)', filename)
        return int(match.group(1)) if match else 0

    def group_files_by_base_name(self):
        """
        Group files by their base name (without part numbers)

        Returns:
            Dictionary mapping base names to sorted lists of file paths
        """
        if not os.path.exists(self.input_folder):
            raise FileNotFoundError(f"Input folder not found: {self.input_folder}")

        file_groups = defaultdict(list)

        for filename in os.listdir(self.input_folder):
            if filename.endswith('.md') or filename.endswith('.txt'):
                base_name = self.get_base_name(filename)
                file_path = os.path.join(self.input_folder, filename)
                part_number = self.get_part_number(filename)

                file_groups[base_name].append({
                    'path': file_path,
                    'filename': filename,
                    'part_number': part_number
                })

        # Sort files within each group by part number
        for base_name in file_groups:
            file_groups[base_name].sort(key=lambda x: x['part_number'])

        return file_groups

    def get_unprocessed_file_groups(self):
        """
        Get file groups that haven't been processed yet

        Returns:
            Dictionary of unprocessed file groups
        """
        # Get already processed files
        processed_files = set()
        if os.path.exists(self.output_folder):
            for file in os.listdir(self.output_folder):
                if file.endswith('.md'):
                    base_name = os.path.splitext(file)[0]
                    processed_files.add(base_name)

        # Get all file groups
        all_file_groups = self.group_files_by_base_name()

        # Filter out already processed groups
        unprocessed_groups = {}
        for base_name, files in all_file_groups.items():
            if base_name not in processed_files:
                unprocessed_groups[base_name] = files
            else:
                logger.info(f"Skipping {base_name} - already processed")

        return unprocessed_groups

    def merge_file_parts(self, file_list):
        """
        Merge content from multiple file parts

        Args:
            file_list: List of file dictionaries with 'path' keys

        Returns:
            Tuple of (merged_content, structured_original_content)
        """
        merged_content = []
        structured_parts = []

        for file_info in file_list:
            file_path = file_info['path']
            filename = file_info['filename']
            logger.info(f"  Reading part: {filename}")

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    merged_content.append(content)

                    # Store structured version with filename for original takeaways section
                    structured_parts.append({
                        'filename': filename,
                        'content': content
                    })
            except Exception as e:
                logger.error(f"  Error reading {file_path}: {e}")
                continue

        # Join all parts with double newline separator for extraction
        merged_for_extraction = "\n\n".join(merged_content)

        return merged_for_extraction, structured_parts

    def extract_key_takeaways(self, content):
        """
        Extract the KEY TAKEAWAYS section from the content

        Args:
            content: File content to extract takeaways from

        Returns:
            Extracted key takeaways or None if not found
        """
        # Find all KEY TAKEAWAYS sections - handle different formatting variations
        # Pattern 1: Look for KEY TAKEAWAYS: followed by content until next section or end
        takeaways_sections = re.findall(
            r'(?:##\s*)?KEY TAKEAWAYS:(?:\s*\*\*)?\s*(.*?)(?=\n\s*##\s*(?:SUMMARY|ORIGINAL TEXT|KEY TAKEAWAYS):|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )

        # If pattern 1 didn't find anything, try a simpler pattern for files that contain only KEY TAKEAWAYS
        if not takeaways_sections:
            # Check if the content starts with KEY TAKEAWAYS: (with or without ##)
            if re.match(r'^(?:##\s*)?KEY TAKEAWAYS:', content.strip(), re.IGNORECASE):
                # Extract everything after "KEY TAKEAWAYS:"
                match = re.search(r'^(?:##\s*)?KEY TAKEAWAYS:\s*(.*)', content.strip(), re.DOTALL | re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        if not takeaways_sections:
            return None

        # Combine all takeaways sections
        combined_takeaways = []
        for i, section in enumerate(takeaways_sections, 1):
            section_text = section.strip()
            if section_text:
                if len(takeaways_sections) > 1:
                    combined_takeaways.append(f"### Part {i}:\n{section_text}")
                else:
                    combined_takeaways.append(section_text)

        return "\n\n".join(combined_takeaways) if combined_takeaways else None

    def query_api(self, payload):
        """
        Query the Azure OpenAI API

        Args:
            payload: Request payload for the API

        Returns:
            API response JSON
        """
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

    def generate_linkedin_post(self, key_takeaways):
        """
        Generate an engaging LinkedIn post from key takeaways

        Args:
            key_takeaways: The key takeaways content

        Returns:
            Dictionary with structured LinkedIn post sections
        """
        prompt = f"""You are a professional LinkedIn content creator. Transform the following key takeaways into a structured, engaging LinkedIn post.

Please provide your response as a valid JSON object with these fields:

{{
  "PostTitle": "A compelling, attention-grabbing title for the post - keep it under 100 characters",
  "Categories": ["category1", "category2", "category3", "category4"],
  "CatchyIntro": "Your catchy intro text here",
  "PostContent": "Your post content here",
  "EndingThoughtsAndQuestion": "Your ending thoughts here"
}}

Field Instructions:

PostTitle: A compelling, attention-grabbing title for the post - keep it under 100 characters

Categories: Provide 2-4 relevant categories/tags for this content as an array. Examples: investing, finance, entrepreneurship, technology, business strategy, etc.

CatchyIntro: Write 1-2 punchy opening lines that hook the reader - this is the first thing they'll see. Make it intriguing, ask a question, or make a bold statement. This should be a single paragraph that flows naturally.

PostContent: Main body of the post with the key insights presented as bullet points. Follow these guidelines:
1. Use bullet points (with - ) for each key insight
2. Include relevant emojis at the start of each bullet point (one emoji per bullet)
3. Make each bullet point bold with a short heading, followed by explanation
4. Keep it concise but informative
5. Focus on value and actionable insights
6. Use short paragraphs within each bullet if needed for clarity
7. Add 3-5 relevant hashtags at the end of this section

EndingThoughtsAndQuestion: A thought-provoking closing statement or call-to-action question that encourages engagement and comments. This should make readers reflect or want to share their experience. Write 2-3 sentences that connect the insights to practical applications.

Key Takeaways to transform:
{key_takeaways}

IMPORTANT: Return ONLY a valid JSON object. Do not include any text before or after the JSON. Maintain professional but approachable tone."""

        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert LinkedIn content creator who writes engaging, professional posts that drive engagement and provide value. You always return valid JSON responses."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 2500,
            "temperature": 0.7,  # Higher temperature for more creative outputs
            "response_format": { "type": "json_object" }  # Request JSON mode
        }

        retry_count = 0
        last_error = None

        while retry_count < self.max_retries:
            try:
                # Make API request
                response = self.query_api(payload)

                # Extract the response content
                if "choices" in response and len(response["choices"]) > 0:
                    linkedin_post = response["choices"][0]["message"]["content"].strip()
                    return linkedin_post
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

    def parse_linkedin_post(self, response_text):
        """
        Parse the AI-generated JSON response into structured sections

        Args:
            response_text: Raw JSON response from AI

        Returns:
            Dictionary with parsed sections
        """
        import json

        try:
            # Try to parse as JSON directly
            sections = json.loads(response_text.strip())

            # Ensure all required fields are present
            required_fields = ['PostTitle', 'Categories', 'CatchyIntro', 'PostContent', 'EndingThoughtsAndQuestion']
            for field in required_fields:
                if field not in sections:
                    sections[field] = ''

            return sections

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text[:500]}")

            # Try to extract JSON from markdown code blocks if present
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    sections = json.loads(json_match.group(1).strip())
                    return sections
                except json.JSONDecodeError:
                    pass

            # If all parsing fails, return empty sections
            return {
                'PostTitle': 'Error parsing response',
                'Categories': ['general'],
                'CatchyIntro': '',
                'PostContent': '',
                'EndingThoughtsAndQuestion': ''
            }

    def format_jekyll_post(self, base_name, sections):
        """
        Format the parsed sections into Jekyll blog post format

        Args:
            base_name: Base name for the post
            sections: Dictionary with PostTitle, Categories, CatchyIntro, PostContent, EndingThoughtsAndQuestion

        Returns:
            Formatted Jekyll blog post content
        """
        from datetime import datetime

        # Generate current date in Jekyll format
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S +0900')

        # Get categories (already a list from JSON)
        categories_list = sections.get('Categories', ['general'])
        if isinstance(categories_list, str):
            # Handle if it's a string (fallback)
            categories_list = [cat.strip() for cat in categories_list.split(',')]

        # Build Jekyll frontmatter
        frontmatter = f"""---
layout: post
title:  "{sections['PostTitle']}"
date:   {current_date}
categories: {categories_list}
---
"""

        # Build post content
        post_body = f"""**{sections['PostTitle']}**

{sections['CatchyIntro']}

{sections['PostContent']}


**Why It Matters**
{sections['EndingThoughtsAndQuestion'].split('?')[0] if '?' in sections['EndingThoughtsAndQuestion'] else sections['EndingThoughtsAndQuestion'].split('.')[0]}.

**Your Turn**
{sections['EndingThoughtsAndQuestion']}
"""

        return frontmatter + post_body

    def format_structured_takeaways(self, structured_parts):
        """
        Format the original key takeaways with dividers and file titles

        Args:
            structured_parts: List of dictionaries with 'filename' and 'content'

        Returns:
            Formatted string with dividers and file titles
        """
        formatted_sections = []

        for part in structured_parts:
            filename = part['filename']
            content = part['content']

            section = f"""### {filename}
---

{content}
"""
            formatted_sections.append(section)

        return "\n\n".join(formatted_sections)

    def get_all_generated_posts(self):
        """
        Collect all generated LinkedIn posts from the output folder

        Returns:
            List of dictionaries with 'filename' and 'content' for each post
        """
        posts = []

        if not os.path.exists(self.output_folder):
            return posts

        for filename in sorted(os.listdir(self.output_folder)):
            if filename.endswith('.md') and filename != 'merged-final-post.md':
                file_path = os.path.join(self.output_folder, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        posts.append({
                            'filename': filename,
                            'content': content
                        })
                except Exception as e:
                    logger.error(f"Error reading post {filename}: {e}")
                    continue

        return posts

    def extract_post_content_for_merge(self, posts):
        """
        Extract the main content from generated posts for merging

        Args:
            posts: List of post dictionaries with 'filename' and 'content'

        Returns:
            Combined content suitable for the LinkedIn post generator prompt
        """
        combined_takeaways = []

        for i, post in enumerate(posts, 1):
            # Extract content after frontmatter (after the closing ---)
            content = post['content']

            # Find the end of Jekyll frontmatter
            frontmatter_end = content.find('---', content.find('---') + 3)
            if frontmatter_end != -1:
                post_body = content[frontmatter_end + 3:].strip()
            else:
                post_body = content.strip()

            # Remove the "Original Key Takeaways" section if present
            original_section_start = post_body.find('## Original Key Takeaways:')
            if original_section_start != -1:
                post_body = post_body[:original_section_start].strip()

            # Add to combined takeaways with source indicator
            combined_takeaways.append(f"### Source {i} - {post['filename']}:\n{post_body}")

        return "\n\n---\n\n".join(combined_takeaways)

    def generate_merged_final_post(self):
        """
        Generate a merged final post from all individual posts

        Returns:
            True if merged post was created, False otherwise
        """
        logger.info("Checking for multiple posts to merge...")

        # Get all generated posts
        posts = self.get_all_generated_posts()

        # Skip if only one or no posts
        if len(posts) <= 1:
            logger.info(f"Found {len(posts)} post(s). Skipping merge (need at least 2 posts)")
            return False

        logger.info(f"Found {len(posts)} posts. Creating merged final post...")

        # Extract and combine content from all posts
        combined_content = self.extract_post_content_for_merge(posts)

        # Generate LinkedIn post using the same prompt
        logger.info("  Generating merged LinkedIn post...")
        linkedin_post_raw = self.generate_linkedin_post(combined_content)

        # Parse the response
        sections = self.parse_linkedin_post(linkedin_post_raw)

        # Format as Jekyll blog post
        jekyll_post = self.format_jekyll_post("merged-final-post", sections)

        # Save to output file
        output_file = os.path.join(self.output_folder, "merged-final-post.md")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(jekyll_post)

        logger.info(f"  Saved merged final post to: {output_file}")
        return True

    def process_file_group(self, base_name, file_list):
        """
        Process a group of file parts and generate LinkedIn post

        Args:
            base_name: Base name for the file group
            file_list: List of file dictionaries belonging to this group
        """
        try:
            logger.info(f"Processing file group: {base_name} ({len(file_list)} parts)")

            # Merge all parts and get structured content
            merged_content, structured_parts = self.merge_file_parts(file_list)

            # Extract key takeaways from merged content
            key_takeaways = self.extract_key_takeaways(merged_content)

            if not key_takeaways:
                logger.warning(f"No key takeaways found in {base_name}")
                return False

            logger.info(f"  Extracted key takeaways, generating LinkedIn post...")

            # Generate LinkedIn post
            linkedin_post_raw = self.generate_linkedin_post(key_takeaways)

            # Parse the response into structured sections
            sections = self.parse_linkedin_post(linkedin_post_raw)

            # Format as Jekyll blog post
            jekyll_post = self.format_jekyll_post(base_name, sections)

            # Format original key takeaways with dividers and file titles
            formatted_takeaways = self.format_structured_takeaways(structured_parts)

            # Save to output file with Jekyll format
            output_file = os.path.join(self.output_folder, f"{base_name}.md")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(jekyll_post)
                f.write("\n\n---\n\n")
                f.write(f"## Original Key Takeaways:\n\n{formatted_takeaways}\n")

            logger.info(f"  Saved LinkedIn post to: {output_file}")
            return True

        except Exception as e:
            logger.error(f"Error processing {base_name}: {e}")
            raise

    def process_all_files(self):
        """Process all unprocessed file groups with progress tracking"""
        try:
            # Setup output folder
            self.setup_folders()

            # Get unprocessed file groups
            unprocessed_groups = self.get_unprocessed_file_groups()

            if not unprocessed_groups:
                logger.info("No new file groups to process")
                return

            # Initialize progress tracker
            progress_tracker = ProgressTracker(
                total_items=len(unprocessed_groups),
                task_name="LinkedIn Post Generation"
            )
            progress_tracker.start()

            # Process each file group
            for base_name, file_list in unprocessed_groups.items():
                try:
                    # Create display name showing number of parts
                    num_parts = len(file_list)
                    display_name = f"{base_name} ({num_parts} part{'s' if num_parts > 1 else ''})"
                    progress_tracker.start_item(display_name)

                    success = self.process_file_group(base_name, file_list)

                    progress_tracker.complete_item(display_name, success=success)
                except Exception as e:
                    display_name = f"{base_name} ({len(file_list)} parts)"
                    progress_tracker.complete_item(display_name, success=False)

                    if "API quota exceeded" in str(e):
                        logger.error("API quota exceeded. Stopping all processing.")
                        break
                    logger.error(f"Failed to process {base_name}: {e}")
                    continue

            # Show final summary
            progress_tracker.finish()
            print(f"  📁 Output directory: {self.output_folder}")

            # Automatically generate merged final post if multiple sources exist
            try:
                merged = self.generate_merged_final_post()
                if merged:
                    print(f"  🔗 Merged final post created: merged-final-post.md")
            except Exception as e:
                logger.error(f"Error generating merged final post: {e}")

        except Exception as e:
            logger.error(f"Error in process_all_files: {e}")
            raise


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Generate LinkedIn posts from key takeaways using Azure OpenAI API. '
                    'Merges all parts of the same file before generating posts.',
        epilog='Example: python step05_generate_linkedin_post.py -i /path/to/ryan-summarize'
    )
    parser.add_argument(
        '-i', '--input',
        dest='input_folder',
        required=True,
        help='Input folder containing key takeaways files (e.g., ryan-summarize)'
    )
    parser.add_argument(
        '-o', '--output',
        dest='output_folder',
        help='Output folder for LinkedIn posts (default: auto-generated with "-post" suffix)'
    )
    return parser.parse_args()


def main():
    """Main function to run the LinkedIn post generation process"""
    try:
        # Parse command line arguments
        args = parse_arguments()

        # Create generator with provided arguments
        generator = LinkedInPostGenerator(
            input_folder=args.input_folder,
            output_folder=args.output_folder
        )

        generator.process_all_files()
        logger.info("LinkedIn post generation process completed")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    main()
