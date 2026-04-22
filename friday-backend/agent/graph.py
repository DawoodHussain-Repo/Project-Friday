"""
LangGraph state-machine definition for the Friday agent.

Graph topology::

    ┌────────────┐   tool_calls?   ┌──────────────┐
    │   agent    │ ─── YES ──────▶ │    tools      │
    │   (LLM)   │ ◀────────────── │  (executor)   │
    └─────┬──────┘                 └──────────────┘
        │ NO
        ▼
     ┌────────────┐
     │  validate  │ --needs_revision--> agent
     └─────┬──────┘
         │ pass
         ▼
        END

The tool node is built dynamically so that newly registered skills are
available immediately.  A ``ToolNode`` cache avoids re-creating the
wrapper on every invocation unless the skill index has changed.
"""

import hashlib
import json
import os
import sqlite3

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from agent.nodes import agent_node, router, validator_node, validator_router
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
CHECKPOINTER_BACKEND: str = os.getenv("CHECKPOINTER_BACKEND", "sqlite").strip().lower()
DEFAULT_CHECKPOINTS_DIR: str = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "checkpoints")
)
CHECKPOINTS_DIR: str = os.path.abspath(
    os.getenv("CHECKPOINTS_DIR", DEFAULT_CHECKPOINTS_DIR)
)
CHECKPOINTS_DB_PATH: str = os.path.abspath(
    os.getenv("CHECKPOINTS_DB_PATH", os.path.join(CHECKPOINTS_DIR, "friday_state.sqlite"))
)

_sqlite_connection: sqlite3.Connection | None = None


def _build_checkpointer():
    """Create the configured graph checkpointer.

    - ``sqlite`` (default): persists threads to a SQLite DB on disk.
    - ``memory``: ephemeral in-memory saver for test sessions.
    """
    global _sqlite_connection  # noqa: PLW0603

    if CHECKPOINTER_BACKEND == "memory":
        return MemorySaver()

    if CHECKPOINTER_BACKEND != "sqlite":
        raise ValueError(
            "Unsupported CHECKPOINTER_BACKEND. Use 'sqlite' or 'memory'."
        )

    os.makedirs(os.path.dirname(CHECKPOINTS_DB_PATH), exist_ok=True)
    _sqlite_connection = sqlite3.connect(CHECKPOINTS_DB_PATH, check_same_thread=False)
    saver = SqliteSaver(_sqlite_connection)
    saver.setup()
    return saver


def close_graph_resources() -> None:
    """Close open graph resources (SQLite connection) on app shutdown."""
    global _sqlite_connection  # noqa: PLW0603

    if _sqlite_connection is not None:
        _sqlite_connection.close()
        _sqlite_connection = None

builder = StateGraph(AgentState)

builder.add_node("agent", agent_node)
builder.add_node("tools", dynamic_tool_node)
builder.add_node("validate", validator_node)

builder.set_entry_point("agent")

builder.add_conditional_edges("agent", router, {"tools": "tools", "validate": "validate"})
builder.add_edge("tools", "agent")  # loop back after tool execution
builder.add_conditional_edges("validate", validator_router, {"agent": "agent", END: END})

graph = builder.compile(
    checkpointer=_build_checkpointer(),
    # recursion_limit is set per-invocation in main.py
)
