import json
import os
import uuid
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, ToolMessage
from pydantic import BaseModel

from agent.graph import graph
from agent.tools.os_tools import WORKSPACE_DIR
from agent.tools.skill_library import load_skill_index

load_dotenv()

RECURSION_LIMIT = int(os.getenv("RECURSION_LIMIT", "25"))
NEXTJS_ORIGIN = os.getenv("NEXTJS_ORIGIN", "http://localhost:3000")


class ChatRequest(BaseModel):
    query: str
    conversation_id: str | None = None


app = FastAPI(title="Project Friday API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[NEXTJS_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse_payload(event_type: str, content: str) -> str:
    return f"data: {json.dumps({'type': event_type, 'content': content})}\n\n"


def _normalize_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_value = str(item.get("text", "")).strip()
                if text_value:
                    text_chunks.append(text_value)
        if text_chunks:
            return "\n".join(text_chunks)

    return json.dumps(content, ensure_ascii=True, default=str)


async def event_stream(query: str, conversation_id: str | None, request: Request):
    thread_id = conversation_id or str(uuid.uuid4())
    seen_agent_signatures: set[str] = set()
    seen_tool_signatures: set[str] = set()

    initial_state = {
        "messages": [HumanMessage(content=query)],
        "tool_attempts": 0,
        "active_skill": None,
    }
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT}

    try:
        async for update in graph.astream(initial_state, config=config, stream_mode="updates"):
            if await request.is_disconnected():
                break

            for node_name, payload in update.items():
                if not isinstance(payload, dict):
                    continue
                messages = payload.get("messages", [])

                if node_name == "agent" and messages:
                    agent_message = messages[-1]
                    text = _normalize_message_content(getattr(agent_message, "content", ""))
                    tool_calls = getattr(agent_message, "tool_calls", []) or []
                    message_id = str(getattr(agent_message, "id", ""))
                    call_signature = json.dumps(tool_calls, ensure_ascii=True, default=str, sort_keys=True)
                    agent_signature = f"{message_id}|{text}|{call_signature}"

                    if agent_signature in seen_agent_signatures:
                        continue
                    seen_agent_signatures.add(agent_signature)

                    if tool_calls:
                        if text:
                            yield _sse_payload("thought", str(text))
                        for call in tool_calls:
                            tool_name = call.get("name", "unknown_tool")
                            args = json.dumps(call.get("args", {}), ensure_ascii=True)
                            yield _sse_payload("tool_call", f"{tool_name} {args}")
                    else:
                        if text:
                            yield _sse_payload("final", str(text))

                if node_name == "tools" and messages:
                    for message in messages:
                        if not isinstance(message, ToolMessage):
                            continue

                        tool_name = getattr(message, "name", "tool")
                        serialized_output = _normalize_message_content(getattr(message, "content", ""))
                        message_id = str(getattr(message, "id", ""))
                        tool_signature = f"{message_id}|{tool_name}|{serialized_output}"

                        if tool_signature in seen_tool_signatures:
                            continue
                        seen_tool_signatures.add(tool_signature)

                        yield _sse_payload("tool_result", f"[{tool_name}] {serialized_output}")
    except Exception as exc:
        yield _sse_payload("final", f"Friday failed: {exc}")


@app.post("/chat")
async def chat(body: ChatRequest, request: Request):
    return StreamingResponse(
        event_stream(body.query, body.conversation_id, request),
        media_type="text/event-stream",
    )


def _build_tree(path: str, root: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    if not os.path.exists(path):
        return nodes

    for entry in sorted(os.listdir(path)):
        full = os.path.join(path, entry)
        rel = os.path.relpath(full, root).replace("\\", "/")
        if os.path.isdir(full):
            nodes.append(
                {
                    "name": entry,
                    "path": rel,
                    "type": "directory",
                    "children": _build_tree(full, root),
                }
            )
        else:
            nodes.append({"name": entry, "path": rel, "type": "file"})

    return nodes


@app.get("/workspace")
async def get_workspace_tree():
    tree = _build_tree(WORKSPACE_DIR, WORKSPACE_DIR)
    return {"tree": tree}


@app.get("/skills")
async def get_skills():
    index = load_skill_index()
    skills = [
        {
            "name": name,
            "description": data.get("description", ""),
            "path": data.get("path", ""),
        }
        for name, data in index.items()
    ]
    return {"skills": skills}
