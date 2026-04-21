"""
Agent state definition for the Friday LangGraph.

The state flows through every node in the graph and accumulates messages,
tool-attempt counts, loaded skill context, and error history.
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state for the Friday ReAct agent graph."""

    #: Conversation messages (LangGraph's ``add_messages`` reducer appends).
    messages: Annotated[list, add_messages]

    #: How many times the current tool/script has been retried.
    tool_attempts: int

    #: File path of the skill script currently being executed (if any).
    active_skill: str | None

    #: Style-guide / rules loaded from a Skill Agent manifest.
    #: Injected into the system prompt so the LLM follows framework-
    #: specific best practices for the duration of the task.
    skill_context: str | None

    #: Optional directory *outside* the sandbox where a project should be
    #: scaffolded (e.g. ``D:/Projects/Gargantua``).  Must be inside one of
    #: the ``ALLOWED_TARGET_DIRS``.
    target_directory: str | None

    #: Rolling list of error messages from failed tool/script executions.
    #: Used by the retry sub-graph to decide whether to retry or bail out.
    error_history: list[str]
