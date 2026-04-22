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

    #: Stable system-level rules separated from conversation history.
    #: This is optional and can be injected by future policy services.
    system_rules: str | None

    #: Rolling summary of older conversation turns to reduce token usage.
    memory_summary: str | None

    #: Cursor index into ``messages`` indicating how much history has already
    #: been compressed into ``memory_summary``.
    summary_cursor: int

    #: Optional directory *outside* the sandbox where a project should be
    #: scaffolded (e.g. ``D:/Projects/Gargantua``).  Must be inside one of
    #: the ``ALLOWED_TARGET_DIRS``.
    target_directory: str | None

    #: Rolling list of error messages from failed tool/script executions.
    #: Used by the retry sub-graph to decide whether to retry or bail out.
    error_history: list[str]

    #: Validator flag set by the validation node to request a regeneration.
    needs_revision: bool

    #: Count of validator-triggered retries for the current response.
    validation_attempts: int

    #: Final answer approved by validator node (if present).
    final_answer: str | None
