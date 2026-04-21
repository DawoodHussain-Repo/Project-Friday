import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Callable

from dotenv import load_dotenv
from langchain_core.tools import StructuredTool, tool
from pydantic import BaseModel, Field

from agent.tools.os_tools import WORKSPACE_DIR, safe_path

load_dotenv()

SKILLS_DIR = os.path.abspath(os.getenv("SKILLS_DIR", "./skills"))
SKILL_INDEX_PATH = os.path.join(SKILLS_DIR, "index.json")


class SkillRunInput(BaseModel):
    arguments: str = Field(default="", description="Command-line arguments passed to the skill script")


def _ensure_skill_store() -> None:
    os.makedirs(SKILLS_DIR, exist_ok=True)
    if not os.path.exists(SKILL_INDEX_PATH):
        with open(SKILL_INDEX_PATH, "w", encoding="utf-8") as file_handle:
            json.dump({}, file_handle, indent=2)


def load_skill_index() -> dict[str, Any]:
    _ensure_skill_store()
    with open(SKILL_INDEX_PATH, "r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)
    return data if isinstance(data, dict) else {}


def save_skill_index(index: dict[str, Any]) -> None:
    _ensure_skill_store()
    with open(SKILL_INDEX_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(index, file_handle, indent=2)


def _slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_").lower() or "skill"


@tool
def save_to_skill_library(skill_name: str, description: str, temp_filename: str) -> str:
    """Moves a tested script from workspace into skills directory and registers it."""
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
        "embedding_id": f"local_{normalized_name}",
    }
    save_skill_index(index)
    return f"Skill '{normalized_name}' committed to library."


@tool
def search_skill_library(query: str) -> str:
    """Finds the closest matching skill based on description similarity."""
    index = load_skill_index()
    if not index:
        return "No skills in library yet."

    best_name = None
    best_score = 0.0

    for name, meta in index.items():
        description = str(meta.get("description", ""))
        score = SequenceMatcher(None, query.lower(), f"{name} {description}".lower()).ratio()
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


def execute_skill_script(skill_path: str, arguments: str = "") -> str:
    command = f'python "{skill_path}" {arguments}'.strip()
    result = subprocess.run(
        command,
        shell=True,
        cwd=WORKSPACE_DIR,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode == 0:
        return result.stdout.strip() or "(no output)"
    return f"ERROR (code {result.returncode}):\n{result.stderr.strip() or result.stdout.strip()}"


def _build_skill_runner(skill_name: str, script_path: str) -> Callable:
    def runner(arguments: str = "") -> str:
        return execute_skill_script(script_path, arguments)

    runner.__name__ = f"run_skill_{skill_name}"
    return runner


def get_dynamic_skill_tools() -> list[StructuredTool]:
    index = load_skill_index()
    tools: list[StructuredTool] = []

    for skill_name, meta in index.items():
        path = str(meta.get("path", ""))
        if not path:
            continue

        if not os.path.isabs(path):
            skill_path = os.path.abspath(path)
        else:
            skill_path = path

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
