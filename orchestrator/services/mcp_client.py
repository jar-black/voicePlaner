"""
MCP Client for communicating with MCP servers
"""

import httpx
from typing import Any, Dict, Optional


class MCPClient:
    """Client for communicating with MCP servers"""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=timeout)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool response data

        Raises:
            Exception: If tool call fails
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/call_tool",
                json={
                    "name": tool_name,
                    "arguments": arguments
                }
            )
            response.raise_for_status()

            result = response.json()

            if not result.get("success"):
                raise Exception(f"Tool call failed: {result.get('error')}")

            return result.get("data", {})

        except httpx.HTTPError as e:
            raise Exception(f"HTTP error calling {tool_name}: {str(e)}")
        except Exception as e:
            raise Exception(f"Error calling {tool_name}: {str(e)}")

    async def list_tools(self) -> Dict[str, Any]:
        """Get list of available tools"""
        try:
            response = await self.client.get(f"{self.base_url}/tools")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error listing tools: {str(e)}")

    async def health_check(self) -> bool:
        """Check if MCP server is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class MCPClientManager:
    """Manager for multiple MCP clients"""

    def __init__(
        self,
        planning_url: str,
        github_url: str,
        claude_code_url: str
    ):
        self.planning = MCPClient(planning_url)
        self.github = MCPClient(github_url)
        self.claude_code = MCPClient(claude_code_url)

    async def check_health(self) -> Dict[str, bool]:
        """Check health of all MCP servers"""
        return {
            "planning": await self.planning.health_check(),
            "github": await self.github.health_check(),
            "claude_code": await self.claude_code.health_check()
        }

    async def close_all(self):
        """Close all MCP clients"""
        await self.planning.close()
        await self.github.close()
        await self.claude_code.close()
