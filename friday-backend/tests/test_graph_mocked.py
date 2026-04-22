import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from agent import graph as graph_module
from agent import nodes as nodes_module


class ScriptedLLM:
    def __init__(self, responses: list[AIMessage]):
        self._responses = list(responses)
        self.bound_tools = []

    def bind_tools(self, tools):
        self.bound_tools = list(tools)
        return self

    async def ainvoke(self, _messages):
        if not self._responses:
            raise AssertionError("ScriptedLLM ran out of responses")
        return self._responses.pop(0)


@tool
def fake_lookup(symbol: str = "NVDA") -> str:
    """Deterministic test tool used for graph structure tests."""
    return f"lookup:{symbol}"


@pytest.fixture(autouse=True)
def reset_graph_tool_cache(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(graph_module, "_cached_tool_node", None)
    monkeypatch.setattr(graph_module, "_cached_tools_hash", "")


@pytest.mark.asyncio
@pytest.mark.mocked_graph
async def test_graph_loops_through_tools_then_finishes(monkeypatch: pytest.MonkeyPatch):
    scripted = ScriptedLLM(
        responses=[
            AIMessage(
                content="Need a tool call first.",
                tool_calls=[
                    {
                        "name": "fake_lookup",
                        "args": {"symbol": "AMD"},
                        "id": "call-lookup-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="AMD lookup complete. Final answer."),
        ]
    )

    monkeypatch.setattr(nodes_module, "_get_base_llm", lambda: scripted)
    monkeypatch.setattr(nodes_module, "get_registered_tools", lambda: [fake_lookup])
    monkeypatch.setattr(graph_module, "get_registered_tools", lambda: [fake_lookup])

    initial_state = {
        "messages": [HumanMessage(content="Check AMD")],
        "tool_attempts": 0,
        "active_skill": None,
        "skill_context": None,
        "system_rules": None,
        "memory_summary": None,
        "summary_cursor": 0,
        "target_directory": None,
        "error_history": [],
        "needs_revision": False,
        "validation_attempts": 0,
        "final_answer": None,
    }

    result = await graph_module.graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": "mocked-graph-tools"}, "recursion_limit": 8},
    )

    assert result["final_answer"] == "AMD lookup complete. Final answer."
    assert any(isinstance(message, ToolMessage) for message in result["messages"])


@pytest.mark.asyncio
@pytest.mark.mocked_graph
async def test_graph_checkpointer_persists_thread_history(monkeypatch: pytest.MonkeyPatch):
    scripted = ScriptedLLM(
        responses=[
            AIMessage(content="First response."),
            AIMessage(content="Second response."),
        ]
    )

    monkeypatch.setattr(nodes_module, "_get_base_llm", lambda: scripted)
    monkeypatch.setattr(nodes_module, "get_registered_tools", lambda: [])
    monkeypatch.setattr(graph_module, "get_registered_tools", lambda: [])

    config = {"configurable": {"thread_id": "mocked-graph-memory"}, "recursion_limit": 8}

    first_turn = {
        "messages": [HumanMessage(content="first message")],
        "tool_attempts": 0,
        "active_skill": None,
        "skill_context": None,
        "system_rules": None,
        "memory_summary": None,
        "summary_cursor": 0,
        "target_directory": None,
        "error_history": [],
        "needs_revision": False,
        "validation_attempts": 0,
        "final_answer": None,
    }
    second_turn = {
        "messages": [HumanMessage(content="second message")],
        "tool_attempts": 0,
        "active_skill": None,
        "skill_context": None,
        "system_rules": None,
        "memory_summary": None,
        "summary_cursor": 0,
        "target_directory": None,
        "error_history": [],
        "needs_revision": False,
        "validation_attempts": 0,
        "final_answer": None,
    }

    await graph_module.graph.ainvoke(first_turn, config=config)
    result_second = await graph_module.graph.ainvoke(second_turn, config=config)

    contents = [str(getattr(message, "content", "")) for message in result_second["messages"]]
    assert any("first message" in content for content in contents)
    assert any("second message" in content for content in contents)
    assert result_second["final_answer"] == "Second response."
