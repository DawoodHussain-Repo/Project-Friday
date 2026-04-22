"""
Dynamic MCP tool registry for Friday.

This module lets the agent register external HTTP/MCP-style tools at runtime,
then exposes each registered entry as a dynamic LangChain tool (mcp_<name>).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable

import httpx
from dotenv import load_dotenv
from langchain_core.tools import StructuredTool, tool
from pydantic import BaseModel, Field

load_dotenv()

SKILLS_DIR: str = os.path.abspath(os.getenv("SKILLS_DIR", "./skills"))
MCP_REGISTRY_PATH: str = os.path.join(SKILLS_DIR, "mcp_tools.json")
MCP_TIMEOUT_SECONDS: int = int(os.getenv("MCP_TIMEOUT_SECONDS", "20"))


class MCPInvokeInput(BaseModel):
    payload: str = Field(
        default="{}",
        description="JSON string payload sent to the MCP/HTTP endpoint.",
    )


def _slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_").lower() or "tool"


def _ensure_registry() -> None:
    os.makedirs(SKILLS_DIR, exist_ok=True)
    if not os.path.isfile(MCP_REGISTRY_PATH):
        with open(MCP_REGISTRY_PATH, "w", encoding="utf-8") as file_handle:
            json.dump({}, file_handle, indent=2)


def load_mcp_registry() -> dict[str, Any]:
    _ensure_registry()
    with open(MCP_REGISTRY_PATH, "r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)
    return data if isinstance(data, dict) else {}


def save_mcp_registry(registry: dict[str, Any]) -> None:
    _ensure_registry()
    with open(MCP_REGISTRY_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(registry, file_handle, indent=2)


def _parse_payload(payload: str) -> Any:
    text = payload.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def _invoke_registered_entry(entry: dict[str, Any], payload: str = "{}") -> str:
    endpoint = str(entry.get("endpoint", "")).strip()
    method = str(entry.get("method", "POST")).strip().upper()
    timeout = int(entry.get("timeout_seconds", MCP_TIMEOUT_SECONDS))
    headers = entry.get("headers", {}) or {}

    if not endpoint:
        return "ERROR: MCP endpoint is missing."

    parsed_payload = _parse_payload(payload)

    kwargs: dict[str, Any] = {"headers": headers, "timeout": timeout}
    if method == "GET":
        if isinstance(parsed_payload, dict):
            kwargs["params"] = parsed_payload
    else:
        if isinstance(parsed_payload, dict):
            kwargs["json"] = parsed_payload
        else:
            kwargs["content"] = str(parsed_payload)

    try:
        response = httpx.request(method, endpoint, **kwargs)
    except Exception as exc:
        return f"ERROR: MCP request failed: {exc}"

    if response.status_code >= 400:
        snippet = response.text[:1200]
        return (
            f"ERROR: MCP endpoint returned HTTP {response.status_code}. "
            f"Response: {snippet}"
        )

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            return json.dumps(response.json(), indent=2)
        except ValueError:
            return response.text[:1200] or "(empty response)"

    return response.text[:1200] or "(empty response)"


@tool
def register_mcp_tool(
    tool_name: str,
    description: str,
    endpoint: str,
    method: str = "POST",
    server_name: str = "default",
    headers_json: str = "{}",
) -> str:
    """Register an MCP/HTTP endpoint as a reusable dynamic tool.

    After registration, the tool is available automatically as `mcp_<tool_name>`
    on the next agent turn.
    """
    normalized_name = _slugify(tool_name)
    normalized_server = _slugify(server_name)
    normalized_method = method.strip().upper() or "POST"

    if normalized_method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        return "ERROR: method must be one of GET, POST, PUT, PATCH, DELETE."

    if not endpoint.startswith("http://") and not endpoint.startswith("https://"):
        return "ERROR: endpoint must start with http:// or https://"

    try:
        headers = json.loads(headers_json) if headers_json.strip() else {}
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid headers_json: {exc}"

    if not isinstance(headers, dict):
        return "ERROR: headers_json must decode to a JSON object."

    registry = load_mcp_registry()
    registry[normalized_name] = {
        "name": normalized_name,
        "server_name": normalized_server,
        "description": description.strip() or "Dynamic MCP tool",
        "endpoint": endpoint.strip(),
        "method": normalized_method,
        "headers": headers,
        "timeout_seconds": MCP_TIMEOUT_SECONDS,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_mcp_registry(registry)

    return (
        f"Registered MCP tool '{normalized_name}'. "
        f"Dynamic tool name: mcp_{normalized_name}"
    )


@tool
def list_registered_mcp_tools() -> str:
    """List all dynamically registered MCP tools."""
    registry = load_mcp_registry()
    if not registry:
        return "No MCP tools registered."

    rows = []
    for name, entry in sorted(registry.items()):
        rows.append(
            {
                "name": name,
                "dynamic_tool": f"mcp_{name}",
                "server_name": entry.get("server_name", "default"),
                "method": entry.get("method", "POST"),
                "endpoint": entry.get("endpoint", ""),
                "description": entry.get("description", ""),
            }
        )
    return json.dumps(rows, indent=2)


@tool
def unregister_mcp_tool(tool_name: str) -> str:
    """Remove a registered MCP tool from the dynamic registry."""
    normalized_name = _slugify(tool_name)
    registry = load_mcp_registry()

    if normalized_name not in registry:
        return f"MCP tool '{normalized_name}' not found."

    registry.pop(normalized_name, None)
    save_mcp_registry(registry)
    return f"Unregistered MCP tool '{normalized_name}'."


def execute_mcp_tool(server_name: str, tool_name: str, payload: str = "{}") -> str:
    """Execute a registered MCP tool by server/name pair or by tool_name."""
    normalized_name = _slugify(tool_name)
    normalized_server = _slugify(server_name)
    registry = load_mcp_registry()

    entry = registry.get(normalized_name)
    if entry is None:
        return f"ERROR: MCP tool '{normalized_name}' is not registered."

    stored_server = str(entry.get("server_name", "default")).strip().lower()
    if normalized_server and normalized_server != "default" and stored_server != normalized_server:
        return (
            f"ERROR: MCP tool '{normalized_name}' is registered under server "
            f"'{stored_server}', not '{normalized_server}'."
        )

    return _invoke_registered_entry(entry, payload)


def _build_mcp_runner(tool_name: str) -> Callable:
    def runner(payload: str = "{}") -> str:
        registry = load_mcp_registry()
        entry = registry.get(tool_name)
        if entry is None:
            return f"ERROR: MCP tool '{tool_name}' no longer exists."
        return _invoke_registered_entry(entry, payload)

    runner.__name__ = f"run_mcp_{tool_name}"
    return runner


def get_dynamic_mcp_tools() -> list[StructuredTool]:
    """Build StructuredTools for every registered MCP tool."""
    registry = load_mcp_registry()
    tools: list[StructuredTool] = []

    for name, entry in sorted(registry.items()):
        runner = _build_mcp_runner(name)
        description = str(entry.get("description", "Dynamic MCP tool"))
        endpoint = str(entry.get("endpoint", ""))
        method = str(entry.get("method", "POST"))

        tools.append(
            StructuredTool.from_function(
                func=runner,
                name=f"mcp_{name}",
                description=(
                    f"Dynamically registered MCP tool '{name}'. "
                    f"Method={method}, Endpoint={endpoint}. {description}"
                ),
                args_schema=MCPInvokeInput,
            )
        )

    return tools
