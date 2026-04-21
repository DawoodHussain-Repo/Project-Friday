"""
Skill Agent system for Project Friday.

A **Skill Agent** is a structured knowledge bundle for a specific framework
or domain (Next.js, FastAPI, React + Vite, …).  Each agent lives in::

    skills/agents/<name>/
    ├── manifest.json      ← metadata, trigger patterns, dos/don'ts
    ├── style_guide.md     ← detailed best-practice document
    └── templates/         ← optional starter files

The tools in this module let the LLM create, load, list, and update
skill agents at runtime so Friday can **teach itself** new frameworks.
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

SKILLS_DIR: str = os.path.abspath(os.getenv("SKILLS_DIR", "./skills"))
AGENTS_DIR: str = os.path.join(SKILLS_DIR, "agents")


def _ensure_agents_dir() -> None:
    os.makedirs(AGENTS_DIR, exist_ok=True)


def _slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_").lower() or "skill"


def _read_manifest(agent_name: str) -> dict[str, Any] | None:
    """Return the parsed manifest for *agent_name*, or ``None``."""
    path = os.path.join(AGENTS_DIR, agent_name, "manifest.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_manifest(agent_name: str, manifest: dict[str, Any]) -> str:
    """Persist *manifest* and return the file path."""
    agent_dir = os.path.join(AGENTS_DIR, agent_name)
    os.makedirs(agent_dir, exist_ok=True)
    path = os.path.join(agent_dir, "manifest.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    return path


# ── Tools ──────────────────────────────────────────────────────────────────


@tool
def create_skill_agent(
    framework_name: str,
    description: str,
    dos: str,
    donts: str,
    scaffold_steps: str,
    trigger_patterns: str,
) -> str:
    """Creates a new Skill Agent with a manifest and style guide.

    Call this when Friday encounters a framework or domain it has no
    existing skill for.  After creation, use ``load_skill_context`` to
    inject the new agent's rules into the current conversation.

    Parameters
    ----------
    framework_name:
        Human-readable framework name, e.g. ``"Next.js"``.
    description:
        One-line summary of what projects this agent handles.
    dos:
        Newline-separated list of best-practice rules to follow.
        Example::

            Use App Router (app/ directory)
            Use TypeScript for all files
            Use server components by default
    donts:
        Newline-separated list of anti-patterns to avoid.
    scaffold_steps:
        Newline-separated shell commands / file-creation steps to set up
        a fresh project.  Example::

            npx -y create-next-app@latest ./ --typescript --tailwind --app --eslint --src-dir --import-alias "@/*" --use-npm
    trigger_patterns:
        Comma-separated keywords that should activate this agent, e.g.
        ``"next.js, nextjs, next js, react ssr"``.
    """
    _ensure_agents_dir()
    slug = _slugify(framework_name)
    agent_dir = os.path.join(AGENTS_DIR, slug)

    if os.path.isdir(agent_dir):
        return (
            f"Skill Agent '{slug}' already exists.  "
            "Use update_skill_agent() to modify it, or load_skill_context() to use it."
        )

    do_list = [d.strip() for d in dos.strip().splitlines() if d.strip()]
    dont_list = [d.strip() for d in donts.strip().splitlines() if d.strip()]
    steps_list = [s.strip() for s in scaffold_steps.strip().splitlines() if s.strip()]
    patterns_list = [p.strip().lower() for p in trigger_patterns.split(",") if p.strip()]

    manifest: dict[str, Any] = {
        "name": slug,
        "display_name": framework_name,
        "version": "1.0.0",
        "description": description,
        "trigger_patterns": patterns_list,
        "rules": {
            "do": do_list,
            "dont": dont_list,
        },
        "scaffold_steps": steps_list,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "auto_generated": True,
    }

    _write_manifest(slug, manifest)

    # Also generate a human-readable style guide markdown
    style_lines = [
        f"# {framework_name} — Style Guide\n",
        f"> {description}\n",
        "## Do ✅\n",
        *[f"- {d}" for d in do_list],
        "\n## Don't ❌\n",
        *[f"- {d}" for d in dont_list],
        "\n## Scaffold Steps\n",
        "```bash",
        *steps_list,
        "```\n",
    ]
    guide_path = os.path.join(agent_dir, "style_guide.md")
    with open(guide_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(style_lines))

    # Create templates directory
    os.makedirs(os.path.join(agent_dir, "templates"), exist_ok=True)

    return (
        f"Skill Agent '{slug}' created successfully.\n"
        f"  Manifest : {os.path.relpath(os.path.join(agent_dir, 'manifest.json'))}\n"
        f"  Guide    : {os.path.relpath(guide_path)}\n"
        f"  Triggers : {patterns_list}\n"
        f"  Rules    : {len(do_list)} dos, {len(dont_list)} don'ts\n"
        f"\nCall load_skill_context('{slug}') to inject these rules into "
        f"the current conversation."
    )


@tool
def load_skill_context(skill_name: str) -> str:
    """Loads a Skill Agent's manifest and style guide into a text block.

    The returned text should be used as additional context for the LLM so
    it follows the agent's dos, don'ts, and project-structure conventions.
    """
    slug = _slugify(skill_name)
    manifest = _read_manifest(slug)
    if manifest is None:
        return f"No Skill Agent found with name '{slug}'."

    rules = manifest.get("rules", {})
    dos = rules.get("do", [])
    donts = rules.get("dont", [])
    steps = manifest.get("scaffold_steps", [])

    parts = [
        f"## Skill Agent: {manifest.get('display_name', slug)}",
        f"**Description:** {manifest.get('description', 'N/A')}",
        "",
        "### Do ✅",
        *[f"- {d}" for d in dos],
        "",
        "### Don't ❌",
        *[f"- {d}" for d in donts],
        "",
        "### Scaffold Steps",
        *[f"  {i+1}. `{s}`" for i, s in enumerate(steps)],
    ]

    # Also include the style guide markdown if it exists
    guide_path = os.path.join(AGENTS_DIR, slug, "style_guide.md")
    if os.path.isfile(guide_path):
        with open(guide_path, "r", encoding="utf-8") as fh:
            guide_content = fh.read()
        parts.append("\n### Full Style Guide\n")
        parts.append(guide_content)

    return "\n".join(parts)


@tool
def list_skill_agents() -> str:
    """Lists all registered Skill Agents and their descriptions."""
    _ensure_agents_dir()

    agents: list[dict[str, Any]] = []
    if not os.path.isdir(AGENTS_DIR):
        return "No skill agents registered yet."

    for entry in sorted(os.listdir(AGENTS_DIR)):
        manifest = _read_manifest(entry)
        if manifest is None:
            continue
        agents.append({
            "name": manifest.get("name", entry),
            "display_name": manifest.get("display_name", entry),
            "description": manifest.get("description", ""),
            "triggers": manifest.get("trigger_patterns", []),
            "rules_count": (
                len(manifest.get("rules", {}).get("do", []))
                + len(manifest.get("rules", {}).get("dont", []))
            ),
        })

    if not agents:
        return "No skill agents registered yet."

    lines = ["Registered Skill Agents:\n"]
    for a in agents:
        lines.append(
            f"• **{a['display_name']}** (`{a['name']}`)\n"
            f"  {a['description']}\n"
            f"  Triggers: {', '.join(a['triggers'])}\n"
            f"  Rules: {a['rules_count']}"
        )
    return "\n".join(lines)


@tool
def update_skill_agent(skill_name: str, updates: str) -> str:
    """Updates an existing Skill Agent's rules or metadata.

    *updates* is a JSON string with the fields to patch.  Supported keys::

        {
          "add_dos": ["new rule 1", "new rule 2"],
          "add_donts": ["new anti-pattern"],
          "remove_dos": ["old rule to remove"],
          "remove_donts": ["old anti-pattern to remove"],
          "add_scaffold_steps": ["new step"],
          "description": "updated description"
        }
    """
    slug = _slugify(skill_name)
    manifest = _read_manifest(slug)
    if manifest is None:
        return f"No Skill Agent found with name '{slug}'."

    try:
        changes = json.loads(updates)
    except json.JSONDecodeError as exc:
        return f"Invalid JSON in updates: {exc}"

    rules = manifest.setdefault("rules", {"do": [], "dont": []})

    if "add_dos" in changes:
        rules["do"].extend(changes["add_dos"])
    if "add_donts" in changes:
        rules["dont"].extend(changes["add_donts"])
    if "remove_dos" in changes:
        rules["do"] = [d for d in rules["do"] if d not in changes["remove_dos"]]
    if "remove_donts" in changes:
        rules["dont"] = [d for d in rules["dont"] if d not in changes["remove_donts"]]
    if "add_scaffold_steps" in changes:
        manifest.setdefault("scaffold_steps", []).extend(changes["add_scaffold_steps"])
    if "description" in changes:
        manifest["description"] = changes["description"]

    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_manifest(slug, manifest)

    # Regenerate style guide
    dos = rules.get("do", [])
    donts = rules.get("dont", [])
    steps = manifest.get("scaffold_steps", [])
    style_lines = [
        f"# {manifest.get('display_name', slug)} — Style Guide\n",
        f"> {manifest.get('description', '')}\n",
        "## Do ✅\n",
        *[f"- {d}" for d in dos],
        "\n## Don't ❌\n",
        *[f"- {d}" for d in donts],
        "\n## Scaffold Steps\n",
        "```bash",
        *steps,
        "```\n",
    ]
    guide_path = os.path.join(AGENTS_DIR, slug, "style_guide.md")
    with open(guide_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(style_lines))

    return (
        f"Skill Agent '{slug}' updated.  "
        f"Now has {len(dos)} dos, {len(donts)} don'ts, "
        f"{len(steps)} scaffold steps."
    )


# ── Utilities used by the tool registry ────────────────────────────────────


def get_all_skill_agent_names() -> list[str]:
    """Return slug names of every registered skill agent."""
    _ensure_agents_dir()
    names = []
    for entry in sorted(os.listdir(AGENTS_DIR)):
        if os.path.isfile(os.path.join(AGENTS_DIR, entry, "manifest.json")):
            names.append(entry)
    return names
