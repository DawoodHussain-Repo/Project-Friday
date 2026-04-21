import os
from typing import Any

from langgraph.graph import END

from agent.model import get_llm
from agent.state import AgentState
from agent.tools import get_registered_tools

MAX_TOOL_ATTEMPTS = int(os.getenv("MAX_TOOL_ATTEMPTS", "3"))


def agent_node(state: AgentState) -> dict[str, Any]:
    llm_with_tools = get_llm().bind_tools(get_registered_tools())
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def router(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


def should_retry(state: AgentState) -> str:
    if state["tool_attempts"] >= MAX_TOOL_ATTEMPTS:
        return "human_fallback"
    return "coder"
