"""
LangGraph state-machine definition for the Friday agent.

Graph topology::

    ┌────────────┐   tool_calls?   ┌──────────────┐
    │   agent    │ ─── YES ──────▶ │    tools      │
    │   (LLM)   │ ◀────────────── │  (executor)   │
    └─────┬──────┘                 └──────────────┘
          │ NO (final answer)
          ▼
        END

The tool node is built dynamically so that newly registered skills are
available immediately.  A ``ToolNode`` cache avoids re-creating the
wrapper on every invocation unless the skill index has changed.
"""

import hashlib
import json
import os

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from agent.nodes import agent_node, router
from agent.state import AgentState
from agent.tools import get_registered_tools

# ---------------------------------------------------------------------------
# Cached dynamic tool node
# ---------------------------------------------------------------------------

_cached_tool_node: ToolNode | None = None
_cached_tools_hash: str = ""


def _tools_fingerprint(tools: list) -> str:
    """Compute a lightweight hash of tool names to detect changes."""
    names = sorted(getattr(t, "name", str(t)) for t in tools)
    return hashlib.md5(json.dumps(names).encode()).hexdigest()


def dynamic_tool_node(state: AgentState):
    """Execute tool calls using the current tool set.

    Re-creates the ``ToolNode`` only when the set of registered tools has
    changed (e.g. a new skill was committed).
    """
    global _cached_tool_node, _cached_tools_hash  # noqa: PLW0603

    tools = get_registered_tools()
    fingerprint = _tools_fingerprint(tools)

    if _cached_tool_node is None or fingerprint != _cached_tools_hash:
        _cached_tool_node = ToolNode(tools)
        _cached_tools_hash = fingerprint

    return _cached_tool_node.invoke(state)


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

RECURSION_LIMIT: int = int(os.getenv("RECURSION_LIMIT", "25"))

builder = StateGraph(AgentState)

builder.add_node("agent", agent_node)
builder.add_node("tools", dynamic_tool_node)

builder.set_entry_point("agent")

builder.add_conditional_edges("agent", router, {"tools": "tools", END: END})
builder.add_edge("tools", "agent")  # loop back after tool execution

graph = builder.compile(
    checkpointer=MemorySaver(),
    # recursion_limit is set per-invocation in main.py
)
