"""
Graph nodes and routing functions for the Friday agent.

Nodes
-----
- ``agent_node`` — invokes the LLM with tools and the system prompt.
- ``router`` — decides whether to call tools or validate.
- ``validator_node`` — checks final output against minimal guardrails.
- ``validator_router`` — decides whether to regenerate or end.
"""

from functools import lru_cache
import os
import re
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END

from agent.logger import setup_logger
from agent.model import get_llm
from agent.state import AgentState
from agent.system_prompt import build_system_prompt
from agent.tools import get_registered_tools

logger = setup_logger(__name__)

MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "50"))
MAX_MEMORY_SUMMARY_CHARS: int = int(os.getenv("MAX_MEMORY_SUMMARY_CHARS", "10000"))
MAX_INPUT_CHARS: int = int(os.getenv("MAX_INPUT_CHARS", "100000"))
MAX_VALIDATION_ATTEMPTS: int = int(os.getenv("MAX_VALIDATION_ATTEMPTS", "1"))


@lru_cache(maxsize=1)
def _get_base_llm():
    """Cache base model construction to avoid repeated provider setup I/O."""
    return get_llm()


def _message_text(message: BaseMessage) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                value = str(item.get("text", "")).strip()
                if value:
                    chunks.append(value)
        if chunks:
            return "\n".join(chunks)
    return str(content)


def _estimate_chars(messages: list[BaseMessage]) -> int:
    return sum(len(_message_text(message)) + 40 for message in messages)


def _latest_user_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            value = _message_text(message).strip()
            if value:
                return value
    return ""


def _build_memory_summary(existing_summary: str | None, new_messages: list[BaseMessage]) -> str | None:
    if not new_messages:
        return existing_summary

    lines: list[str] = []
    if existing_summary:
        lines.append(existing_summary.strip())

    for message in new_messages:
        if isinstance(message, HumanMessage):
            role = "User"
        elif isinstance(message, AIMessage):
            role = "Assistant"
        else:
            continue

        text = _message_text(message).strip()
        if not text:
            continue
        lines.append(f"{role}: {text[:240]}")

    summary = "\n".join(lines).strip()
    if not summary:
        return None
    if len(summary) > MAX_MEMORY_SUMMARY_CHARS:
        summary = summary[-MAX_MEMORY_SUMMARY_CHARS:]
    return summary


def _is_stock_query(text: str) -> bool:
    lowered = text.lower()
    keywords = ["stock", "ticker", "share", "price", "nvda", "amd", "market cap"]
    return any(keyword in lowered for keyword in keywords)


# ---------------------------------------------------------------------------
# Agent node
# ---------------------------------------------------------------------------


async def agent_node(state: AgentState) -> dict[str, Any]:
    """Invoke the LLM with the current messages, tools, and system prompt.

    The system prompt is assembled from the static core instructions plus
    any dynamically loaded skill context (e.g. a Next.js style guide).
    """
    full_history = list(state["messages"])

    cursor = max(0, int(state.get("summary_cursor", 0)))
    summary_cutoff = max(0, len(full_history) - MAX_HISTORY_MESSAGES)
    to_summarize = full_history[cursor:summary_cutoff]
    memory_summary = _build_memory_summary(state.get("memory_summary"), to_summarize)

    # Build the system prompt with optional skill context and rolling memory.
    skill_context = state.get("skill_context")
    system_prompt = build_system_prompt(
        skill_context=skill_context,
        memory_summary=memory_summary,
        system_rules=state.get("system_rules"),
        latest_user_input=_latest_user_text(full_history),
    )

    tools = get_registered_tools()
    llm_with_tools = _get_base_llm().bind_tools(tools)

    # Keep bounded recent messages, then apply a strict character budget.
    bounded_history = full_history[-MAX_HISTORY_MESSAGES:]
    messages = [SystemMessage(content=system_prompt)] + bounded_history

    while _estimate_chars(messages) > MAX_INPUT_CHARS and len(bounded_history) > 2:
        bounded_history = bounded_history[1:]
        messages = [SystemMessage(content=system_prompt)] + bounded_history

    try:
        response = await llm_with_tools.ainvoke(messages)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"LLM invocation failed: {error_msg}", exc_info=True)
        
        # Check if it's a tool use failure from Groq
        if "tool_use_failed" in error_msg or "Failed to call a function" in error_msg:
            # Extract the failed generation if available
            failed_gen_match = re.search(r"'failed_generation': '([^']+)'", error_msg)
            failed_gen = failed_gen_match.group(1) if failed_gen_match else "unknown"
            
            logger.warning(f"Tool use failed - malformed output: {failed_gen[:200]}")
            
            # Try again without tool binding - let the model respond in plain text
            logger.info("Retrying without tool binding - model will respond in plain text")
            try:
                llm_without_tools = _get_base_llm()
                # Add instruction to describe what it wants to do
                retry_messages = messages + [
                    SystemMessage(content="The previous tool call failed due to formatting issues. "
                                         "Please describe in plain text what you want to do, "
                                         "and I'll help you execute it properly.")
                ]
                response = await llm_without_tools.ainvoke(retry_messages)
                logger.info("Successfully got response without tool binding")
            except Exception as retry_error:
                logger.error(f"Retry without tools also failed: {retry_error}", exc_info=True)
                # Return an error message to the user
                error_response = AIMessage(
                    content=f"I encountered persistent errors trying to process your request. "
                            f"The model is having trouble with tool calls. "
                            f"Please try rephrasing your request or breaking it into smaller steps."
                )
                return {
                    "messages": [error_response],
                    "memory_summary": memory_summary,
                    "summary_cursor": max(cursor, summary_cutoff),
                    "needs_revision": False,
                    "final_answer": None,
                }
        else:
            # Re-raise other errors
            raise

    return {
        "messages": [response],
        "memory_summary": memory_summary,
        "summary_cursor": max(cursor, summary_cutoff),
        "needs_revision": False,
        "final_answer": None,
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def router(state: AgentState) -> str:
    """Route after the agent node.

    Returns ``"tools"`` if the last message contains tool calls, otherwise
    ``"validate"`` to run final-answer guardrails.
    """
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "validate"


def validator_node(state: AgentState) -> dict[str, Any]:
    """Validate the latest candidate final response and request retry if needed."""
    messages = list(state["messages"])
    attempts = int(state.get("validation_attempts", 0))

    latest_ai: AIMessage | None = None
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            latest_ai = message
            break

    if latest_ai is None:
        return {"needs_revision": False, "final_answer": None}

    candidate = _message_text(latest_ai).strip()
    if not candidate:
        feedback = "Validator: Your answer was empty. Provide a direct answer to the user request."
        if attempts < MAX_VALIDATION_ATTEMPTS:
            return {
                "messages": [HumanMessage(content=feedback)],
                "needs_revision": True,
                "validation_attempts": attempts + 1,
                "final_answer": None,
            }
        return {"needs_revision": False, "final_answer": "I could not generate a valid answer."}

    user_text = _latest_user_text(messages)
    lowered_answer = candidate.lower()
    feedback_items: list[str] = []

    if _is_stock_query(user_text) and "can't provide real-time" in lowered_answer:
        feedback_items.append(
            "Use market-data tools for stock requests instead of refusing real-time data."
        )

    if _is_stock_query(user_text) and "paris weather" in lowered_answer:
        feedback_items.append("Your answer drifted to an unrelated domain. Stay on the stock query.")

    if feedback_items and attempts < MAX_VALIDATION_ATTEMPTS:
        feedback = "Validator feedback: " + " ".join(feedback_items)
        return {
            "messages": [HumanMessage(content=feedback)],
            "needs_revision": True,
            "validation_attempts": attempts + 1,
            "final_answer": None,
        }

    return {
        "needs_revision": False,
        "validation_attempts": attempts,
        "final_answer": candidate,
    }


def validator_router(state: AgentState) -> str:
    """Route after validation: retry once if needed, otherwise end."""
    if state.get("needs_revision"):
        return "agent"
    return END
