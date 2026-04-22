import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from langgraph.graph import END

from agent.nodes import router, validator_router
from agent.tools import os_tools


@pytest.mark.unit
def test_router_routes_to_tools_when_tool_calls_present() -> None:
    state = {
        "messages": [
            AIMessage(
                content="calling tool",
                tool_calls=[
                    {
                        "name": "list_files",
                        "args": {"directory": "."},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            )
        ]
    }
    assert router(state) == "tools"


@pytest.mark.unit
def test_router_routes_to_validate_without_tool_calls() -> None:
    state = {"messages": [AIMessage(content="final answer")]}  # no tool calls
    assert router(state) == "validate"


@pytest.mark.unit
def test_validator_router_uses_revision_flag() -> None:
    assert validator_router({"needs_revision": True}) == "agent"
    assert validator_router({"needs_revision": False}) == END


@pytest.mark.unit
def test_is_command_allowed_blocks_chaining_operator() -> None:
    allowed, reason = os_tools._is_command_allowed("python --version && whoami")
    assert allowed is False
    assert "not allowed" in reason.lower()


@pytest.mark.unit
def test_is_command_allowed_accepts_python_version() -> None:
    allowed, reason = os_tools._is_command_allowed("python --version")
    assert allowed is True
    assert reason == ""


@pytest.mark.unit
def test_safe_path_blocks_workspace_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os_tools, "WORKSPACE_DIR", str(tmp_path))
    with pytest.raises(PermissionError):
        os_tools.safe_path("../../outside.txt")


@pytest.mark.unit
def test_main_sse_helpers() -> None:
    from main import _normalize_message_content, _sse_payload

    payload = _sse_payload("final", "done")
    assert payload.startswith("data: ")

    data = json.loads(payload.removeprefix("data: ").strip())
    assert data == {"type": "final", "content": "done"}

    normalized = _normalize_message_content(
        [{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}]
    )
    assert normalized == "hello\nworld"
