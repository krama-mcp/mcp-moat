#!/usr/bin/env python3
"""
step06_push_to_github.py

This script pushes blog posts from a folder (with "-post" suffix) to a GitHub repository.
It extracts the pure content (excluding "Original Key Takeaways" section) and pushes to GitHub.

Usage:
    python step06_push_to_github.py -i /path/to/folder-post

Example:
    python step06_push_to_github.py -i /Users/kiran.ramanna/Documents/github/mcp-moat/wisdomhatch-post
"""

import os
import re
import argparse
import datetime
from pathlib import Path
from github import Github
from dotenv import load_dotenv
from progress_utils import ProgressTracker, setup_logging

# Load environment variables
load_dotenv()

# Configure logging
logger = setup_logging(__name__)


class GitHubPublisher:
    """A class to publish blog posts to GitHub"""

    def __init__(self, input_folder=None, repo_name="kiranramanna/thinkit", remote_dir="_posts"):
        """
        Initialize the GitHub publisher

        Args:
            input_folder: Directory containing blog post files (typically ending with -post)
            repo_name: GitHub repository name (format: username/repo)
            remote_dir: Directory in the repo where files should be created
        """
        if input_folder is None:
            raise ValueError("Input folder must be specified with -i argument")

        self.input_folder = input_folder
        self.repo_name = repo_name
        self.remote_dir = remote_dir

        logger.info(f"Input folder: {self.input_folder}")
        logger.info(f"GitHub repository: {repo_name}")
        logger.info(f"Remote directory: {remote_dir}")

        # Get GitHub token from environment
        self.github_token = os.getenv("GITHUB_TOKEN_THINKIT")

        if not self.github_token or self.github_token == 'your_github_token_here':
            raise ValueError(
                "Please set your GitHub token in the .env file\n"
                "1. Open mcp-moat/.env\n"
                "2. Add GITHUB_TOKEN_THINKIT=your_actual_token\n"
                "3. Save the file and run the script again\n"
                "To create a token: https://github.com/settings/tokens"
            )

        # Initialize GitHub connection
        try:
            self.github = Github(self.github_token)
            self.repo = self.github.get_repo(self.repo_name)
            logger.info("GitHub connection established")
        except Exception as e:
            raise ValueError(f"Failed to connect to GitHub: {e}")

    def extract_pure_content(self, content):
        """
        Extract pure blog content, excluding the "Original Key Takeaways" section

        Args:
            content: Full file content

        Returns:
            Pure content (frontmatter + blog post only)
        """
        # Find the separator before "## Original Key Takeaways:"
        # Split on the pattern: --- followed by ## Original Key Takeaways:
        pattern = r'\n---\s*\n+##\s*Original Key Takeaways:'

        parts = re.split(pattern, content, maxsplit=1)

        if len(parts) > 1:
            # Found the separator, return only the first part
            pure_content = parts[0].strip()
            logger.debug("  Extracted pure content (excluded Original Key Takeaways)")
            return pure_content
        else:
            # No separator found, return full content
            logger.debug("  No Original Key Takeaways section found, using full content")
            return content.strip()

    def extract_frontmatter_title(self, content):
        """
        Extract title from YAML frontmatter

        Args:
            content: File content with frontmatter

        Returns:
            Title string or None
        """
        match = re.search(r'title:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
        if match:
            return match.group(1).strip('"\'')
        return None

    def extract_frontmatter_date(self, content):
        """
        Extract date from YAML frontmatter

        Args:
            content: File content with frontmatter

        Returns:
            Date string (YYYY-MM-DD) or today's date
        """
        match = re.search(r'date:\s*(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
        if match:
            return match.group(1)
        return datetime.datetime.now().strftime('%Y-%m-%d')

    def generate_github_filename(self, original_filename, content):
        """
        Generate GitHub-compatible filename

        Args:
            original_filename: Original filename from the folder
            content: File content (to extract date/title from frontmatter)

        Returns:
            GitHub-compatible filename (e.g., 2025-02-13-blog-title.md)
        """
        # Extract date and title from frontmatter
        date_str = self.extract_frontmatter_date(content)
        title = self.extract_frontmatter_title(content)

        if not title:
            # Fall back to filename without extension
            title = os.path.splitext(original_filename)[0]

        # Convert title to slug: lowercase, replace spaces with hyphens, remove special chars
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')

        return f"{date_str}-{slug}.md"

    def get_existing_files_on_github(self):
        """
        Get set of existing filenames on GitHub

        Returns:
            Set of filenames
        """
        existing_files = set()
        try:
            contents = self.repo.get_contents(self.remote_dir)
            for content in contents:
                if content.name.endswith('.md'):
                    existing_files.add(content.name)
            logger.info(f"Found {len(existing_files)} existing files on GitHub")
        except Exception as e:
            logger.warning(f"Could not fetch existing files from GitHub: {e}")
        return existing_files

    def get_files_to_process(self):
        """
        Get list of files to process from input folder

        Returns:
            List of file info dictionaries
        """
        if not os.path.exists(self.input_folder):
            raise FileNotFoundError(f"Input folder not found: {self.input_folder}")

        # Get all .md files from input folder
        all_files = []
        for filename in os.listdir(self.input_folder):
            if filename.endswith('.md'):
                file_path = os.path.join(self.input_folder, filename)

                try:
                    # Read file to determine GitHub filename
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    github_filename = self.generate_github_filename(filename, content)

                    all_files.append({
                        'path': file_path,
                        'filename': filename,
                        'github_filename': github_filename
                    })
                except Exception as e:
                    logger.warning(f"Error reading file {filename}: {e}")
                    continue

        if not all_files:
            logger.warning(f"No .md files found in {self.input_folder}")
            return []

        logger.info(f"Found {len(all_files)} files to process")
        return all_files

    def preserve_existing_date(self, new_content, existing_content):
        """
        Replace the date in new_content with the date from existing_content

        Args:
            new_content: New content with potentially updated date
            existing_content: Existing content from GitHub with original date

        Returns:
            Content with original date preserved
        """
        # Extract date from existing content
        existing_date_match = re.search(r'date:\s*(.+?)$', existing_content, re.MULTILINE)

        if existing_date_match:
            existing_date = existing_date_match.group(1).strip()
            # Replace date in new content with existing date
            new_content = re.sub(
                r'(date:\s*)(.+?)$',
                r'\g<1>' + existing_date,
                new_content,
                count=1,
                flags=re.MULTILINE
            )
            logger.info(f"  Preserved original date: {existing_date}")

        return new_content

    def push_file_to_github(self, file_path, filename, github_filename=None):
        """
        Push a single file to GitHub

        Args:
            file_path: Path to the local file
            filename: Original filename
            github_filename: Target filename on GitHub

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"  Reading file: {filename}")

            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                full_content = f.read()

            # Extract pure content (without Original Key Takeaways)
            pure_content = self.extract_pure_content(full_content)

            # Generate GitHub filename if not provided
            if github_filename is None:
                github_filename = self.generate_github_filename(filename, pure_content)

            # Extract title for commit message
            title = self.extract_frontmatter_title(pure_content) or filename

            # Create remote path
            remote_path = f"{self.remote_dir}/{github_filename}"
            commit_message = f"Add post: {title}"

            logger.info(f"  Pushing to GitHub as: {github_filename}")

            try:
                # Try to get existing file
                existing_file = self.repo.get_contents(remote_path)
                existing_content = existing_file.decoded_content.decode('utf-8')

                # Preserve the original date from existing file
                pure_content = self.preserve_existing_date(pure_content, existing_content)

                # Update the file
                self.repo.update_file(
                    remote_path,
                    f"Update post: {title}",
                    pure_content,
                    existing_file.sha
                )
                logger.info(f"  ✓ File updated: {remote_path}")
                return True
            except:
                # If file doesn't exist, create it
                self.repo.create_file(remote_path, commit_message, pure_content)
                logger.info(f"  ✓ File created: {remote_path}")
                return True

        except Exception as e:
            logger.error(f"  ✗ Error pushing file {filename}: {e}")
            return False

    def process_all_files(self):
        """Process all files with progress tracking"""
        try:
            # Get files to process
            files_to_process = self.get_files_to_process()

            if not files_to_process:
                logger.info("No new files to process")
                return

            # Initialize progress tracker
            progress_tracker = ProgressTracker(
                total_items=len(files_to_process),
                task_name="GitHub Publishing"
            )
            progress_tracker.start()

            # Process each file
            successful = 0
            failed = 0

            for file_info in files_to_process:
                try:
                    file_path = file_info['path']
                    filename = file_info['filename']
                    github_filename = file_info.get('github_filename')

                    progress_tracker.start_item(filename)

                    success = self.push_file_to_github(file_path, filename, github_filename)

                    if success:
                        successful += 1
                    else:
                        failed += 1

                    progress_tracker.complete_item(filename, success=success)

                except Exception as e:
                    logger.error(f"Failed to process {file_info['filename']}: {e}")
                    failed += 1
                    progress_tracker.complete_item(file_info['filename'], success=False)
                    continue

            # Show final summary
            progress_tracker.finish()
            print(f"\n  ✓ Successfully pushed: {successful} files")
            if failed > 0:
                print(f"  ✗ Failed: {failed} files")
            print(f"  📦 Repository: https://github.com/{self.repo_name}")

        except Exception as e:
            logger.error(f"Error in process_all_files: {e}")
            raise


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Push blog posts from a folder to GitHub repository. '
                    'Updates existing files while preserving their original dates.',
        epilog='Example: python step06_push_to_github.py -i /path/to/ryan-post'
    )
    parser.add_argument(
        '-i', '--input',
        dest='input_folder',
        required=True,
        help='Input folder containing blog post files (e.g., ryan-post)'
    )
    parser.add_argument(
        '-r', '--repo',
        dest='repo_name',
        default='kiranramanna/thinkit',
        help='GitHub repository name (format: username/repo, default: kiranramanna/thinkit)'
    )
    parser.add_argument(
        '-d', '--dir',
        dest='remote_dir',
        default='_posts',
        help='Remote directory in the repository (default: _posts)'
    )
    return parser.parse_args()


def main():
    """Main function to run the GitHub publishing process"""
    try:
        # Parse command line arguments
        args = parse_arguments()

        # Create publisher with provided arguments
        publisher = GitHubPublisher(
            input_folder=args.input_folder,
            repo_name=args.repo_name,
            remote_dir=args.remote_dir
        )

        publisher.process_all_files()
        logger.info("GitHub publishing process completed")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    main()
