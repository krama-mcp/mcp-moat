import os
from typing import Dict, List
import math
import json
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# For Python versions that don't have ExceptionGroup in builtins
try:
    from builtins import ExceptionGroup
except ImportError:
    ExceptionGroup = BaseException  # Fallback for older Python versions

def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def split_content(content: str, chunk_size: int = 25000) -> List[str]:
    """Split content into chunks of specified size."""
    return [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]

async def get_perplexity_response(messages: List[Dict[str, str]], max_retries: int = 3) -> Dict:
    """Get response from Perplexity using MCP."""
    last_error = None
    
    # Initialize the MCP server for Perplexity outside the retry loop
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-perplexity"],
        env={
            **os.environ,
            "PERPLEXITY_API_KEY": "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",
        }
    )
    
    # Create a single client session for all retries
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            for attempt in range(max_retries):
                try:
                    # Call the Perplexity ask function through MCP
                    response = await session.call(
                        "mcp_perplexity_ask_perplexity_ask",
                        {"messages": messages}
                    )
                    return response
                        
                except Exception as e:
                    last_error = e
                    print(f"Error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                    if attempt < max_retries - 1:
                        # Exponential backoff with longer delays
                        delay = (attempt + 1) * 3  # 3 seconds, 6 seconds, 9 seconds
                        print(f"Waiting {delay} seconds before retry...")
                        await asyncio.sleep(delay)
                    continue
    
    # If we get here, all retries failed
    raise last_error if last_error else Exception("All retries failed")

async def get_perplexity_summary(content: str, part_num: int = None) -> Dict[str, str]:
    """Get summary and takeaways using Perplexity through MCP."""
    part_info = f" (Part {part_num})" if part_num is not None else ""
    
    messages = [
        {
            "role": "system", 
            "content": f"""You are a helpful assistant that summarizes transcripts concisely and professionally.
            You are currently analyzing{part_info} of a transcript.
            Your response should be in the following format:
            
            SUMMARY:
            [A concise summary of the main points and insights from this section]
            
            TAKEAWAYS:
            [List any explicit takeaways mentioned in this section (when speaker specifically calls something a takeaway), 
            as well as implicit key lessons that are emphasized. Number each takeaway.]"""
        },
        {
            "role": "user", 
            "content": f"Please analyze the following transcript section and provide a summary and takeaways: {content}"
        }
    ]
    
    try:
        # Get response from Perplexity with retries
        response = await get_perplexity_response(messages)
        
        if not response or not isinstance(response, dict) or 'content' not in response:
            return {
                "summary": "Error: Invalid response format from Perplexity API",
                "takeaways": "Unable to process response - invalid format received"
            }
            
        response_text = response['content']
        
        # Split the response into summary and takeaways
        if "SUMMARY:" not in response_text or "TAKEAWAYS:" not in response_text:
            return {
                "summary": response_text,  # Use full response as summary if not properly formatted
                "takeaways": "Response not in expected format - using raw response"
            }
            
        # Extract summary and takeaways
        summary_start = response_text.find("SUMMARY:")
        takeaways_start = response_text.find("TAKEAWAYS:")
        
        summary = response_text[summary_start + 8:takeaways_start].strip()
        takeaways = response_text[takeaways_start + 10:].strip()
        
        return {
            "summary": summary,
            "takeaways": takeaways
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error processing part {part_num} with Perplexity: {error_msg}")
        return {
            "summary": f"Error processing this section (part {part_num}): {error_msg}",
            "takeaways": "Unable to extract takeaways due to an error. Please try processing this section again."
        }

def create_markdown_summary(source_file: str, summary: str, takeaways: str, part_num: int = None) -> str:
    """Create markdown formatted summary."""
    title = os.path.basename(source_file)
    if part_num is not None:
        title = f"{title} (Part {part_num})"
    
    markdown = f"""# Summary of {title}

**Source**: {source_file}

## Summary
{summary}

## Key Takeaways
{takeaways}
"""
    return markdown

async def process_transcript_files(source_dir: str, output_dir: str) -> None:
    """Process all transcript files and create markdown summaries."""
    # Ensure output directory exists
    ensure_directory_exists(output_dir)
    
    # Process each file in the source directory
    for filename in os.listdir(source_dir):
        if filename.endswith('.txt'):
            source_path = os.path.join(source_dir, filename)
            base_output_name = filename.replace('.txt', '')
            
            print(f"\nProcessing: {filename}")
            
            # Read content
            with open(source_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split content into chunks
            chunks = split_content(content)
            total_chunks = len(chunks)
            
            print(f"File split into {total_chunks} parts")
            
            # Process each chunk
            for i, chunk in enumerate(chunks, 1):
                print(f"\nProcessing part {i} of {total_chunks}...")
                
                # Get summary and takeaways from Perplexity
                result = await get_perplexity_summary(chunk, part_num=i if total_chunks > 1 else None)
                
                # Create output filename
                if total_chunks > 1:
                    output_filename = f"{base_output_name}-part-{i:02d}.md"
                else:
                    output_filename = f"{base_output_name}.md"
                
                output_path = os.path.join(output_dir, output_filename)
                
                # Create markdown content
                markdown_content = create_markdown_summary(
                    source_path, 
                    result["summary"], 
                    result["takeaways"],
                    part_num=i if total_chunks > 1 else None
                )
                
                # Write markdown file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                print(f"Created: {output_filename}")
                
                # Add longer delay between chunks to avoid overwhelming the API
                if i < total_chunks:
                    delay = 5  # 5 second delay between chunks
                    print(f"Waiting {delay} seconds before processing next chunk...")
                    await asyncio.sleep(delay)
            
            # Add longer delay between files
            if any(f.endswith('.txt') for f in os.listdir(source_dir)[os.listdir(source_dir).index(filename) + 1:]):
                delay = 10  # 10 second delay between files
                print(f"\nWaiting {delay} seconds before processing next file...")
                await asyncio.sleep(delay)

async def main():
    # Define directories
    base_dir = "/Users/shivswork/cgithub/mcp-moat"
    source_dir = os.path.join(base_dir, "wisdomhatch-txt")
    output_dir = os.path.join(base_dir, "wisdomhatch_blog")
    
    # Process files
    await process_transcript_files(source_dir, output_dir)
    print("\nProcessing complete!")

if __name__ == "__main__":
    asyncio.run(main()) 