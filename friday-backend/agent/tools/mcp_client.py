from langchain_core.tools import tool

from agent.tools.mcp_registry import execute_mcp_tool


@tool
def mcp_call(server_name: str, tool_name: str, payload: str = "{}") -> str:
    """Calls a registered MCP tool by server/name with JSON payload."""
    return execute_mcp_tool(server_name=server_name, tool_name=tool_name, payload=payload)
