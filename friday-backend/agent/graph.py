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

import asyncio
import hashlib
import json
import os

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from agent.logger import setup_logger, log_checkpoint_operation
from agent.nodes import agent_node, router, validator_node, validator_router
from agent.state import AgentState
from agent.tools import get_registered_tools

logger = setup_logger(__name__)

# ---------------------------------------------------------------------------
# Cached dynamic tool node
# ---------------------------------------------------------------------------

_cached_tool_node: ToolNode | None = None
_cached_tools_hash: str = ""
_tool_cache_lock = asyncio.Lock()


def _tools_fingerprint(tools: list) -> str:
    """Compute a lightweight hash of tool names to detect changes."""
    names = sorted(getattr(t, "name", str(t)) for t in tools)
    return hashlib.sha256(json.dumps(names).encode()).hexdigest()


async def dynamic_tool_node(state: AgentState):
    """Execute tool calls using the current tool set.

    Re-creates the ``ToolNode`` only when the set of registered tools has
    changed (e.g. a new skill was committed).
    """
    global _cached_tool_node, _cached_tools_hash  # noqa: PLW0603

    tools = get_registered_tools()
    fingerprint = _tools_fingerprint(tools)

    async with _tool_cache_lock:
        if _cached_tool_node is None or fingerprint != _cached_tools_hash:
            _cached_tool_node = ToolNode(tools)
            _cached_tools_hash = fingerprint
        tool_node = _cached_tool_node

    return await tool_node.ainvoke(state)


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

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

_async_checkpointer: AsyncSqliteSaver | None = None
_checkpointer_context = None


async def _build_checkpointer():
    """Create the configured graph checkpointer.

    - ``sqlite`` (default): persists threads to a SQLite DB on disk.
    - ``memory``: ephemeral in-memory saver for test sessions.
    """
    global _async_checkpointer, _checkpointer_context  # noqa: PLW0603

    logger.info(f"Initializing checkpointer backend: {CHECKPOINTER_BACKEND}")

    if CHECKPOINTER_BACKEND == "memory":
        logger.info("Using in-memory checkpointer (ephemeral)")
        return MemorySaver()

    if CHECKPOINTER_BACKEND != "sqlite":
        logger.error(f"Unsupported CHECKPOINTER_BACKEND: {CHECKPOINTER_BACKEND}")
        raise ValueError(
            "Unsupported CHECKPOINTER_BACKEND. Use 'sqlite' or 'memory'."
        )

    try:
        os.makedirs(os.path.dirname(CHECKPOINTS_DB_PATH), exist_ok=True)
        logger.info(f"Initializing AsyncSqliteSaver at: {CHECKPOINTS_DB_PATH}")
        
        # AsyncSqliteSaver.from_conn_string returns an async context manager
        _checkpointer_context = AsyncSqliteSaver.from_conn_string(CHECKPOINTS_DB_PATH)
        # Enter the context manager and keep it alive
        _async_checkpointer = await _checkpointer_context.__aenter__()
        
        logger.info("AsyncSqliteSaver initialized successfully")
        log_checkpoint_operation(logger, "init", "system", success=True)
        return _async_checkpointer
    except Exception as e:
        logger.error(f"Failed to initialize AsyncSqliteSaver: {e}", exc_info=True)
        log_checkpoint_operation(logger, "init", "system", success=False)
        raise


async def close_graph_resources() -> None:
    """Close open graph resources (AsyncSqliteSaver) on app shutdown."""
    global _async_checkpointer, _checkpointer_context  # noqa: PLW0603

    if _checkpointer_context is not None:
        logger.info("Closing graph resources...")
        # Exit the context manager properly
        try:
            await _checkpointer_context.__aexit__(None, None, None)
            logger.info("Graph resources closed successfully")
            log_checkpoint_operation(logger, "close", "system", success=True)
        except Exception as e:
            logger.error(f"Error closing graph resources: {e}", exc_info=True)
            log_checkpoint_operation(logger, "close", "system", success=False)
        finally:
            _async_checkpointer = None
            _checkpointer_context = None

builder = StateGraph(AgentState)

builder.add_node("agent", agent_node)
builder.add_node("tools", dynamic_tool_node)
builder.add_node("validate", validator_node)

builder.set_entry_point("agent")

builder.add_conditional_edges("agent", router, {"tools": "tools", "validate": "validate"})
builder.add_edge("tools", "agent")  # loop back after tool execution
builder.add_conditional_edges("validate", validator_router, {"agent": "agent", END: END})

# Compile graph without checkpointer initially (will be set lazily on first use)
_graph_builder = builder
_compiled_graph = None
_graph_init_lock = asyncio.Lock()


async def get_graph():
    """Get or initialize the compiled graph with async checkpointer."""
    global _compiled_graph  # noqa: PLW0603
    
    if _compiled_graph is not None:
        return _compiled_graph
    
    async with _graph_init_lock:
        if _compiled_graph is not None:
            return _compiled_graph
        
        logger.info("Compiling LangGraph state machine...")
        try:
            checkpointer = await _build_checkpointer()
            _compiled_graph = _graph_builder.compile(
                checkpointer=checkpointer,
                # recursion_limit is set per-invocation in main.py
            )
            logger.info("LangGraph compiled successfully")
            return _compiled_graph
        except Exception as e:
            logger.error(f"Failed to compile graph: {e}", exc_info=True)
            raise


# For backward compatibility, create a synchronous wrapper that will fail with a helpful message
class _GraphProxy:
    """Proxy that ensures graph is accessed via get_graph() async function."""
    
    def __getattr__(self, name):
        raise RuntimeError(
            "Graph must be initialized asynchronously. Use 'await get_graph()' instead of 'graph'."
        )


graph = _GraphProxy()
