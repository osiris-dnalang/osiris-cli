"""osiris.mcp — Model Context Protocol integration."""

# MCP server/client stubs for future implementation
__all__ = ["MCPServer", "MCPClient"]


class MCPServer:
    """MCP server stub."""
    def __init__(self, name: str = "osiris"):
        self.name = name
        self.tools: dict = {}

    def register_tool(self, name: str, handler):
        self.tools[name] = handler

    def list_tools(self):
        return list(self.tools.keys())


class MCPClient:
    """MCP client stub."""
    def __init__(self, server_url: str = "localhost:3000"):
        self.server_url = server_url
