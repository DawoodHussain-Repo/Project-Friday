"""
System prompt for the Friday agent.

``build_system_prompt()`` assembles Friday's instructions from a static
core prompt plus optional dynamic context (the loaded skill-agent style
guide, project rules, etc.).
"""

import os

# ---------------------------------------------------------------------------
# Static core prompt
# ---------------------------------------------------------------------------

_RUNTIME_PROMPT = """\
You are Friday, an agentic AI assistant that works with a ReAct loop.

Core behavior:
1) Think briefly about the EXACT user request - stay focused, do not hallucinate unrelated tasks.
2) Call tools to gather facts or perform work.
3) Observe tool output and continue until done.
4) Return a concise final answer with real results.

CRITICAL: Tool calling format
- ALWAYS use proper JSON format for tool calls
- NEVER use XML-style tags like <function=name{...}></function>
- Use the standard tool calling format provided by the system
- If you're unsure, describe what you want to do in plain text instead

CRITICAL: Stay on task
- If user asks "make CSS for HTML about cats", do NOT search for weather or unrelated topics.
- Only use tools that directly address the user's request.
- If you find yourself using a tool unrelated to the request, STOP and refocus.

Tool priorities:
- For stock/market queries use get_stock_quote / compare_stock_prices first.
- For web knowledge use web_search.
- For files and code use list_files/read_file/write_to_file/append_to_file/create_directory.
- For shell use execute_bash_command / execute_in_directory only when needed.
- For reusable scripts use search_skill_library first; if missing, create and test a script,
  then commit with save_to_skill_library.

Skill creation workflow (MANDATORY when learning new capabilities):
1) Check if skill exists: search_skill_library("skill_name")
2) If NOT found and you're doing something reusable (web design, CSS styling, API integration):
   a) Create a skill document (.py or .md) with clear instructions/code
   b) Test it works
   c) Save with save_to_skill_library(name="skill_name", description="what it does", path="path/to/file")
3) Next time you need this capability, search_skill_library first and reuse it

Examples of when to create skills:
- "learn web design" → create web_design_skill.md with CSS best practices
- "make API calls to X" → create x_api_client.py with reusable functions
- "parse JSON data" → create json_parser.py with utility functions
- "generate HTML templates" → create html_generator.py with template functions

On-the-fly learning:
- If a framework/domain pattern is recurring, create or update a Skill Agent.
- If an external API endpoint is repeatedly useful, register it as an MCP tool using
  register_mcp_tool so it appears as a dynamic mcp_<name> tool in later turns.
- Reuse dynamic skill and MCP tools before reinventing.

Failure handling:
- Do not retry the same failed approach more than twice.
- If web_search/shell is failing for data retrieval, pivot: write/test a focused script or
  register an MCP endpoint tool.
- Never switch to unrelated tasks while a user request is unresolved.

Safety:
- Never fabricate data. If data retrieval fails, report the failure and next action.
- Never exfiltrate secrets or access blocked paths.
- Respect sandbox and command policies.
- Before finalizing, internally re-check your key rules and constraints.
"""

_FULL_PROMPT = """\
You are Friday, a tool-using software agent.

Execution model:
- Rebuild plan every turn: Think -> Act -> Observe -> Repeat -> Finalize.
- Use tools first for facts and side effects; do not hallucinate results.
- If one path fails repeatedly, pivot to a new strategy or build a reusable tool.

Reliability:
- Keep reasoning short and action-oriented.
- Never abandon unresolved user intent.
- Prefer deterministic outputs with explicit tool evidence.

Core safety:
- Respect sandbox/allowlist constraints and secret boundaries.
- Do not execute destructive commands or unrelated requests.
- If blocked by policy, explain why and propose a safe alternative.

""" + _RUNTIME_PROMPT


_INSTRUCTION_SNIPPETS: list[tuple[set[str], str]] = [
    (
        {"stock", "ticker", "price", "market", "nvda", "amd", "finance"},
        "Use get_stock_quote / compare_stock_prices before web_search or shell commands for equity data.",
    ),
    (
        {"mcp", "api", "endpoint", "integration"},
        "If an external endpoint is repeatedly useful, register it with register_mcp_tool and reuse dynamic mcp_<name>.",
    ),
    (
        {"next", "react", "fastapi", "vite", "django", "express", "scaffold"},
        "For framework tasks, load/update a Skill Agent and follow its style guide rules while generating files and commands.",
    ),
    (
        {"security", "secret", "credential", "key"},
        "Never expose secrets. Reject unsafe paths/commands and keep operations inside allowed directories.",
    ),
    (
        {"design", "css", "html", "style", "web", "frontend", "ui"},
        "For web design/CSS: 1) search_skill_library('web_design') first, 2) if not found, create skill document with best practices, 3) save_to_skill_library, 4) use it.",
    ),
    (
        {"learn", "skill", "capability", "remember"},
        "When learning new capabilities: create skill document → test → save_to_skill_library → reuse next time.",
    ),
]


def _clip(text: str, max_chars: int, note: str) -> str:
    value = text.strip()
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + note


def _retrieve_instruction_chunks(
    latest_user_input: str | None,
    max_chunks: int,
) -> list[str]:
    if not latest_user_input:
        return []

    lowered = latest_user_input.lower()
    selected: list[str] = []
    for keywords, snippet in _INSTRUCTION_SNIPPETS:
        if any(token in lowered for token in keywords):
            selected.append(snippet)
        if len(selected) >= max_chunks:
            break
    return selected

# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_system_prompt(
    skill_context: str | None = None,
    extra_instructions: str | None = None,
    memory_summary: str | None = None,
    system_rules: str | None = None,
    latest_user_input: str | None = None,
) -> str:
    """Assemble the full system prompt.

    Parameters
    ----------
    skill_context:
        The style-guide / rules loaded from a Skill Agent manifest.
        Injected as an additional section so the LLM follows
        framework-specific best practices.
    extra_instructions:
        Any ad-hoc instructions to append (e.g., per-task overrides).
    memory_summary:
        Compact summary of older conversation turns.
    system_rules:
        Optional immutable policy rules injected outside chat history.
    latest_user_input:
        Latest user text for instruction-chunk retrieval.
    """
    prompt_variant = os.getenv("SYSTEM_PROMPT_VARIANT", "runtime").strip().lower()
    base_prompt = _FULL_PROMPT if prompt_variant == "full" else _RUNTIME_PROMPT

    max_system_prompt_chars = int(os.getenv("MAX_SYSTEM_PROMPT_CHARS", "30000"))
    max_skill_chars = int(os.getenv("MAX_SKILL_CONTEXT_CHARS", "20000"))
    max_rules_chars = int(os.getenv("MAX_SYSTEM_RULES_CHARS", "10000"))
    max_memory_chars = int(os.getenv("MAX_MEMORY_SUMMARY_CHARS", "10000"))
    max_extra_chars = int(os.getenv("MAX_EXTRA_INSTRUCTIONS_CHARS", "10000"))
    retrieval_max_chunks = int(os.getenv("MAX_INSTRUCTION_SNIPPETS", "5"))

    parts: list[str] = [base_prompt]

    if system_rules:
        clipped_rules = _clip(
            system_rules,
            max_rules_chars,
            "\n[System rules truncated for context budget.]",
        )
        parts.append("\n[System Rules]\n" + clipped_rules)

    snippets = _retrieve_instruction_chunks(latest_user_input, retrieval_max_chunks)
    if snippets:
        parts.append("\n[Retrieved Instruction Chunks]\n- " + "\n- ".join(snippets))

    if memory_summary:
        clipped_summary = _clip(
            memory_summary,
            max_memory_chars,
            "\n[Memory summary truncated for context budget.]",
        )
        parts.append("\n[Memory Summary]\n" + clipped_summary)

    if skill_context:
        clipped_context = _clip(
            skill_context,
            max_skill_chars,
            "\n[Skill context truncated to fit context window.]",
        )
        parts.append("\n[Active Skill Context]\n" + clipped_context)

    if extra_instructions:
        clipped_extra = _clip(
            extra_instructions,
            max_extra_chars,
            "\n[Extra instructions truncated for context budget.]",
        )
        parts.append("\n[Additional Instructions]\n" + clipped_extra)

    assembled = "\n\n".join(part for part in parts if part.strip())
    if len(assembled) > max_system_prompt_chars:
        assembled = (
            assembled[:max_system_prompt_chars]
            + "\n\n[System prompt clipped for context window.]"
        )

    return assembled
