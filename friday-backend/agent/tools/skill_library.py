"""
Skill library tools for the Friday agent.

Provides tools to save successfully tested scripts to a persistent skill
library and to search it for reuse.  Skills are stored as individual
Python scripts under ``SKILLS_DIR`` with metadata in ``index.json``.

Dynamic skill tools
-------------------
When a skill is committed, a corresponding ``StructuredTool`` is generated
so the LLM can invoke the skill directly (``skill_<name>``).  These are
re-loaded on every ``get_dynamic_skill_tools()`` call.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Callable

from langchain_core.tools import StructuredTool, tool
from pydantic import BaseModel, ConfigDict, Field

from agent.tools.os_tools import COMMAND_TIMEOUT, WORKSPACE_DIR, safe_path

SKILLS_DIR: str = os.path.abspath(os.getenv("SKILLS_DIR", "./skills"))
SKILL_INDEX_PATH: str = os.path.join(SKILLS_DIR, "index.json")


class SkillRunInput(BaseModel):
    """Schema for running a committed skill script."""

    model_config = ConfigDict(extra="forbid")

    arguments: str = Field(
        default="",
        description="Command-line arguments passed to the skill script.",
    )


# ---------------------------------------------------------------------------
# Index helpers
# ---------------------------------------------------------------------------


def _ensure_skill_store() -> None:
    os.makedirs(SKILLS_DIR, exist_ok=True)
    if not os.path.exists(SKILL_INDEX_PATH):
        with open(SKILL_INDEX_PATH, "w", encoding="utf-8") as fh:
            json.dump({}, fh, indent=2)


def load_skill_index() -> dict[str, Any]:
    """Load the skill index from disk."""
    _ensure_skill_store()
    with open(SKILL_INDEX_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else {}


def save_skill_index(index: dict[str, Any]) -> None:
    """Persist the skill index to disk."""
    _ensure_skill_store()
    with open(SKILL_INDEX_PATH, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2)


def _slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_").lower() or "skill"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool
def save_to_skill_library(skill_name: str, description: str, temp_filename: str) -> str:
    """Moves a tested script from workspace into the skills directory.

    Call this only **after** you have executed the script via
    ``execute_bash_command`` and confirmed it runs without errors.
    """
    _ensure_skill_store()
    source = safe_path(temp_filename)
    if not os.path.exists(source):
        return f"Skill source not found: {temp_filename}"

    normalized_name = _slugify(skill_name)
    destination = os.path.join(SKILLS_DIR, f"{normalized_name}.py")
    shutil.move(source, destination)

    index = load_skill_index()
    index[normalized_name] = {
        "description": description,
        "path": os.path.relpath(destination, os.getcwd()).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_skill_index(index)
    return f"Skill '{normalized_name}' committed to library."


@tool
def search_skill_library(query: str) -> str:
    """Finds the closest matching skill based on description similarity.

    Returns JSON with the skill name, description, path, and similarity
    score.  Returns a message if no close match is found.
    """
    index = load_skill_index()
    if not index:
        return "No skills in library yet."

    best_name = None
    best_score = 0.0

    for name, meta in index.items():
        description = str(meta.get("description", ""))
        score = SequenceMatcher(
            None, query.lower(), f"{name} {description}".lower()
        ).ratio()
        if score > best_score:
            best_score = score
            best_name = name

    if best_name is None or best_score < 0.35:
        return "No close skill match found."

    match = index[best_name]
    return json.dumps(
        {
            "name": best_name,
            "description": match.get("description", ""),
            "path": match.get("path", ""),
            "similarity": round(best_score, 3),
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Dynamic skill execution (subprocess, no shell=True)
# ---------------------------------------------------------------------------


def execute_skill_script(skill_path: str, arguments: str = "") -> str:
    """Run a committed skill script safely.

    Uses list-based ``subprocess.run`` (no shell injection) and enforces
    the configured command timeout.
    """
    cmd = [sys.executable, skill_path]
    if arguments.strip():
        # Split arguments safely — shlex on Windows is tricky, so we use
        # a simple whitespace split (skill args shouldn't be complex).
        cmd.extend(arguments.strip().split())

    try:
        result = subprocess.run(
            cmd,
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return f"ERROR: Skill timed out after {COMMAND_TIMEOUT}s."

    if result.returncode == 0:
        return result.stdout.strip() or "(no output)"
    return (
        f"ERROR (code {result.returncode}):\n"
        f"{result.stderr.strip() or result.stdout.strip()}"
    )


# ---------------------------------------------------------------------------
# Dynamic tool generation
# ---------------------------------------------------------------------------


def _build_skill_runner(skill_name: str, script_path: str) -> Callable:
    """Build a callable that runs the given skill script."""

    def runner(arguments: str = "") -> str:
        return execute_skill_script(script_path, arguments)

    runner.__name__ = f"run_skill_{skill_name}"
    return runner


def get_dynamic_skill_tools() -> list[StructuredTool]:
    """Generate StructuredTools for every committed skill script."""
    index = load_skill_index()
    tools: list[StructuredTool] = []

    for skill_name, meta in index.items():
        path = str(meta.get("path", ""))
        if not path:
            continue

        skill_path = os.path.abspath(path) if not os.path.isabs(path) else path

        if not os.path.exists(skill_path):
            continue

        description = str(meta.get("description", "User-created skill"))
        runner = _build_skill_runner(skill_name, skill_path)
        tools.append(
            StructuredTool.from_function(
                func=runner,
                name=f"skill_{_slugify(skill_name)}",
                description=f"Runs skill '{skill_name}'. {description}",
                args_schema=SkillRunInput,
            )
        )

    return tools
