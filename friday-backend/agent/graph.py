from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from agent.nodes import agent_node, router
from agent.state import AgentState
from agent.tools import get_registered_tools


builder = StateGraph(AgentState)

builder.add_node("agent", agent_node)


def dynamic_tool_node(state: AgentState):
    node = ToolNode(get_registered_tools())
    return node.invoke(state)


builder.add_node("tools", dynamic_tool_node)
builder.set_entry_point("agent")
builder.add_conditional_edges("agent", router, {"tools": "tools", END: END})
builder.add_edge("tools", "agent")

graph = builder.compile(checkpointer=MemorySaver())
