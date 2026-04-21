"""
Graph nodes and routing functions for the Friday agent.

Nodes
-----
- ``agent_node`` — invokes the LLM with tools and the system prompt.
- ``router`` — decides whether to call tools or end.
- ``should_retry`` — decides whether to retry a failed tool execution.
"""

import os
from typing import Any

from langchain_core.messages import SystemMessage
from langgraph.graph import END

from agent.model import get_llm
from agent.state import AgentState
from agent.system_prompt import build_system_prompt
from agent.tools import get_registered_tools

MAX_TOOL_ATTEMPTS: int = int(os.getenv("MAX_TOOL_ATTEMPTS", "3"))


# ---------------------------------------------------------------------------
# Agent node
# ---------------------------------------------------------------------------


def agent_node(state: AgentState) -> dict[str, Any]:
    """Invoke the LLM with the current messages, tools, and system prompt.

    The system prompt is assembled from the static core instructions plus
    any dynamically loaded skill context (e.g. a Next.js style guide).
    """
    # Build the system prompt with optional skill context
    skill_context = state.get("skill_context")
    system_prompt = build_system_prompt(skill_context=skill_context)

    tools = get_registered_tools()
    llm_with_tools = get_llm().bind_tools(tools)

    # Prepend the system message to the conversation
    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def router(state: AgentState) -> str:
    """Route after the agent node.

    Returns ``"tools"`` if the last message contains tool calls, otherwise
    ``END`` (the agent is done).
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


def should_retry(state: AgentState) -> str:
    """Decide whether to retry after a tool failure.

    Returns ``"agent"`` to let the LLM try again (the error is already in
    the message history), or ``END`` if the retry budget is exhausted.
    """
    attempts = state.get("tool_attempts", 0)
    if attempts >= MAX_TOOL_ATTEMPTS:
        return END  # bail out — the agent will explain the failure
    return "agent"
