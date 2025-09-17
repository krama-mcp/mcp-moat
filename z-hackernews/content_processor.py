import os
import time
from datetime import datetime
import requests
import json

def fetch_hn_top_stories():
    """Fetch top stories from Hacker News API"""
    try:
        # Fetch top story IDs
        response = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json')
        story_ids = response.json()[:10]  # Get top 10 stories
        
        stories = []
        for story_id in story_ids:
            # Fetch individual story details
            story_url = f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json'
            story_response = requests.get(story_url)
            story = story_response.json()
            stories.append(story)
            time.sleep(0.1)  # Be nice to the API
        
        return stories
    except Exception as e:
        print(f"Error fetching stories: {e}")
        return []

def save_raw_content(stories):
    """Save raw content to a file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'raw_content_{timestamp}.txt'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(stories, f, indent=2)
    
    return filename

def process_content(raw_filename):
    """Process content in chunks and save results"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    processed_filename = f'processed_content_{timestamp}.txt'
    
    with open(raw_filename, 'r', encoding='utf-8') as f:
        stories = json.load(f)
    
    processed_content = []
    for story in stories:
        # Extract title and first 100 words of text if available
        title = story.get('title', '')
        text = story.get('text', '')
        url = story.get('url', '')
        
        words = text.split()[:100]
        summary = ' '.join(words)
        
        processed_story = {
            'title': title,
            'url': url,
            'summary': summary
        }
        processed_content.append(processed_story)
    
    with open(processed_filename, 'w', encoding='utf-8') as f:
        json.dump(processed_content, f, indent=2)
    
    return processed_filename

def main():
    """Main execution loop"""
    try:
        while True:
            print("Fetching new stories...")
            stories = fetch_hn_top_stories()
            
            if stories:
                raw_filename = save_raw_content(stories)
                print(f"Raw content saved to: {raw_filename}")
                
                processed_filename = process_content(raw_filename)
                print(f"Processed content saved to: {processed_filename}")
            
            print("Waiting for 5 minutes before next fetch...")
            time.sleep(300)  # Wait 5 minutes between fetches
            
    except KeyboardInterrupt:
        print("\nStopping the content processor...")

if __name__ == "__main__":
    main() 