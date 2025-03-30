from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import logging
import os
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(
        self,
        server_command: str = "python",
        server_args: Optional[list] = None,
        server_env: Optional[Dict[str, str]] = None
    ):
        self.server_params = StdioServerParameters(
            command=server_command,
            args=server_args or [],
            env=server_env or os.environ.copy()
        )
        self.session: Optional[ClientSession] = None

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
            logger.info("MCP client session initialized successfully")
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
    """Example usage of the MCP client"""
    client = MCPClient(
        server_command="python",
        server_args=["example_server.py"],
    )

    try:
        # Initialize the client
        await client.initialize()

        # List available tools
        tools = await client.list_available_tools()
        print("Available tools:", tools)

        # List available resources
        resources = await client.list_available_resources()
        print("Available resources:", resources)

        # Example tool call
        result = await client.call_tool(
            "example-tool",
            arguments={"param1": "value1"}
        )
        print("Tool call result:", result)

    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise
    finally:
        # Ensure the client is properly closed
        await client.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 