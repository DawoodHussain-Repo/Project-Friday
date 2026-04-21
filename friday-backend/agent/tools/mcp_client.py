from langchain_core.tools import tool


@tool
def mcp_call(server_name: str, tool_name: str, payload: str = "{}") -> str:
    """Calls a configured MCP server tool. Placeholder for Phase 2+ integration."""
    return (
        "MCP integration is not configured yet. "
        f"Requested server={server_name}, tool={tool_name}, payload={payload}"
    )
