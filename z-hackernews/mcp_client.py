from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import logging
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPServerType(Enum):
    SEQUENTIAL_THINKING = "sequential-thinking"
    HACKER_NEWS = "hacker-news"
    CUSTOM = "custom"

class MCPClient:
    def __init__(
        self,
        server_type: MCPServerType = MCPServerType.CUSTOM,
        server_command: Optional[str] = None,
        server_args: Optional[list] = None,
        server_env: Optional[Dict[str, str]] = None
    ):
        self.server_type = server_type
        self.server_params = self._get_server_params(
            server_type, server_command, server_args, server_env
        )
        self.session: Optional[ClientSession] = None

    def _get_server_params(
        self,
        server_type: MCPServerType,
        command: Optional[str],
        args: Optional[list],
        env: Optional[Dict[str, str]]
    ) -> StdioServerParameters:
        """Get server parameters based on server type"""
        if server_type == MCPServerType.SEQUENTIAL_THINKING:
            return StdioServerParameters(
                command="npx",
                args=[
                    "~/.cursor/servers/src/sequentialthinking/",
                    "--yes",
                    "@modelcontextprotocol/server-sequential-thinking@0.6.2"
                ],
                env=env or os.environ.copy()
            )
        elif server_type == MCPServerType.HACKER_NEWS:
            home_dir = os.path.expanduser("~")
            server_path = os.path.join(home_dir, ".cursor/community_servers/hn-server/build/index.js")
            return StdioServerParameters(
                command="node",
                args=[server_path],
                env=env or os.environ.copy()
            )
        else:
            if not command:
                raise ValueError("server_command is required for custom server type")
            return StdioServerParameters(
                command=command,
                args=args or [],
                env=env or os.environ.copy()
            )

    async def handle_sampling_message(
        self,
        message: types.CreateMessageRequestParams
    ) -> types.CreateMessageResult:
        """Handle sampling messages from the server"""
        try:
            return types.CreateMessageResult(
                role="assistant",
                content=types.TextContent(
                    type="text",
                    text=f"Processing message: {message.content}"
                ),
                model="gpt-3.5-turbo",
                stopReason="endTurn"
            )
        except Exception as e:
            logger.error(f"Error in sampling handler: {e}")
            raise

    async def initialize(self) -> None:
        """Initialize the MCP client session"""
        try:
            read, write = await stdio_client(self.server_params).__aenter__()
            self.session = await ClientSession(
                read,
                write,
                sampling_callback=self.handle_sampling_message
            ).__aenter__()
            await self.session.initialize()
            logger.info(f"MCP client session initialized successfully for {self.server_type.value} server")
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
            raise

    async def list_available_resources(self) -> list:
        """List available resources from the server"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        try:
            resources = await self.session.list_resources()
            logger.info(f"Found {len(resources)} available resources")
            return resources
        except Exception as e:
            logger.error(f"Error listing resources: {e}")
            raise

    async def list_available_tools(self) -> list:
        """List available tools from the server"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        try:
            tools = await self.session.list_tools()
            logger.info(f"Found {len(tools)} available tools")
            return tools
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            raise

    async def read_resource(self, resource_path: str) -> tuple:
        """Read a resource from the server"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        try:
            content, mime_type = await self.session.read_resource(resource_path)
            logger.info(f"Successfully read resource: {resource_path}")
            return content, mime_type
        except Exception as e:
            logger.error(f"Error reading resource {resource_path}: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the server"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        try:
            result = await self.session.call_tool(tool_name, arguments=arguments)
            logger.info(f"Successfully called tool: {tool_name}")
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise

    async def close(self) -> None:
        """Close the MCP client session"""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
                logger.info("MCP client session closed successfully")
            except Exception as e:
                logger.error(f"Error closing session: {e}")
                raise

async def main():
    """Example usage of the MCP client with Hacker News"""
    # Initialize Hacker News client
    hn_client = MCPClient(server_type=MCPServerType.HACKER_NEWS)
    
    try:
        await hn_client.initialize()
        logger.info("Fetching latest Hacker News posts...")
        
        # First, list available tools to see what we can use
        tools = await hn_client.list_available_tools()
        logger.info(f"Available tools: {tools}")
        
        # Call the get-top-stories tool
        result = await hn_client.call_tool(
            "get-top-stories",
            arguments={"limit": 10}  # Get top 10 stories
        )
        
        # Create timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'hackernews_posts_{timestamp}.txt'
        
        # Format and save the posts
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== Latest Hacker News Posts ===\n\n")
            for idx, story in enumerate(result, 1):
                f.write(f"{idx}. {story.get('title', 'No title')}\n")
                f.write(f"   URL: {story.get('url', 'No URL')}\n")
                f.write(f"   Score: {story.get('score', 0)}\n")
                f.write(f"   Author: {story.get('by', 'Unknown')}\n")
                f.write(f"   Comments: {story.get('descendants', 0)}\n")
                f.write("\n")
        
        logger.info(f"Saved Hacker News posts to {filename}")
        
        # Also save raw JSON for potential further processing
        json_filename = f'hackernews_posts_{timestamp}.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Saved raw JSON data to {json_filename}")
        
    except Exception as e:
        logger.error(f"Error fetching Hacker News posts: {e}")
        raise
    finally:
        await hn_client.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 