import requests
import json
from datetime import datetime
import logging
import time
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HackerNewsFetcher:
    """A class to fetch and process Hacker News stories"""
    
    def __init__(self):
        self.base_url = "https://hacker-news.firebaseio.com/v0"
    
    def get_top_stories(self, limit: int = 10) -> List[int]:
        """Fetch IDs of top stories"""
        try:
            response = requests.get(f"{self.base_url}/topstories.json")
            response.raise_for_status()
            return response.json()[:limit]
        except Exception as e:
            logger.error(f"Error fetching top stories: {e}")
            raise

    def get_story_details(self, story_id: int) -> Dict[str, Any]:
        """Fetch details of a specific story"""
        try:
            response = requests.get(f"{self.base_url}/item/{story_id}.json")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching story {story_id}: {e}")
            raise

    def fetch_and_save_stories(self, limit: int = 10):
        """Fetch top stories and save them to files"""
        try:
            logger.info(f"Fetching top {limit} Hacker News stories...")
            story_ids = self.get_top_stories(limit)
            
            stories = []
            for story_id in story_ids:
                story = self.get_story_details(story_id)
                stories.append(story)
                time.sleep(0.1)  # Be nice to the API
            
            # Create timestamp for filenames
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save formatted text version
            txt_filename = f'hackernews_posts_{timestamp}.txt'
            with open(txt_filename, 'w', encoding='utf-8') as f:
                f.write("=== Latest Hacker News Posts ===\n\n")
                for idx, story in enumerate(stories, 1):
                    f.write(f"{idx}. {story.get('title', 'No title')}\n")
                    f.write(f"   URL: {story.get('url', 'No URL')}\n")
                    f.write(f"   Score: {story.get('score', 0)}\n")
                    f.write(f"   Author: {story.get('by', 'Unknown')}\n")
                    f.write(f"   Comments: {story.get('descendants', 0)}\n")
                    if story.get('text'):
                        f.write(f"   Text: {story['text']}\n")
                    f.write("\n")
            
            logger.info(f"Saved formatted posts to {txt_filename}")
            
            # Save raw JSON version
            json_filename = f'hackernews_posts_{timestamp}.json'
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(stories, f, indent=2)
            
            logger.info(f"Saved raw JSON data to {json_filename}")
            
            return txt_filename, json_filename
            
        except Exception as e:
            logger.error(f"Error in fetch_and_save_stories: {e}")
            raise

def main():
    """Main function to demonstrate usage"""
    fetcher = HackerNewsFetcher()
    try:
        txt_file, json_file = fetcher.fetch_and_save_stories(limit=10)
        logger.info("Successfully fetched and saved Hacker News stories")
        logger.info(f"Text file: {txt_file}")
        logger.info(f"JSON file: {json_file}")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main() 