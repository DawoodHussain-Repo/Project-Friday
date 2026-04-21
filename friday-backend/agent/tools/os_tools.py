import os
import re
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

WORKSPACE_DIR = os.path.abspath(os.getenv("WORKSPACE_DIR", "./workspace"))
BLOCKED_SEGMENTS = {".env", ".ssh"}
BLOCKED_COMMAND_PATTERNS = [
    "rm -rf /",
    "sudo",
    "chmod 777",
]

ABSOLUTE_PATH_PATTERNS = [
    re.compile(r"(^|\s)[a-zA-Z]:[\\/]"),
    re.compile(r"(^|\s)/[a-zA-Z]/"),
]


def safe_path(relative: str) -> str:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise PermissionError("Absolute paths are not allowed.")

    resolved = os.path.realpath(os.path.join(WORKSPACE_DIR, relative))
    if os.path.commonpath([WORKSPACE_DIR, resolved]) != WORKSPACE_DIR:
        raise PermissionError("Path escape attempt blocked.")

    parts = {part.lower() for part in Path(resolved).parts}
    if any(segment in parts for segment in BLOCKED_SEGMENTS):
        raise PermissionError("Access to protected path blocked.")

    return resolved


def _ensure_workspace() -> None:
    os.makedirs(WORKSPACE_DIR, exist_ok=True)


@tool
def list_files(directory: str = ".") -> str:
    """Lists files and folders at the given path within the workspace."""
    _ensure_workspace()
    target = safe_path(directory)
    entries = sorted(os.listdir(target))
    return "\n".join(entries) if entries else "(empty)"


@tool
def read_file(filename: str) -> str:
    """Reads and returns the contents of a file in the workspace."""
    _ensure_workspace()
    with open(safe_path(filename), "r", encoding="utf-8") as file_handle:
        return file_handle.read()


@tool
def write_to_file(filename: str, content: str) -> str:
    """Creates or overwrites a file in the workspace with the given content."""
    _ensure_workspace()
    path = safe_path(filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file_handle:
        file_handle.write(content)
    return f"Wrote {len(content)} chars to {filename}"


@tool
def execute_bash_command(command: str) -> str:
    """Runs a shell command inside the workspace and returns stdout/stderr."""
    _ensure_workspace()
    if any(pattern.search(command) for pattern in ABSOLUTE_PATH_PATTERNS):
        return (
            "ERROR:\nAbsolute paths are blocked. Use workspace-relative paths only "
            "(for example: mkdir my_folder)."
        )

    lower_command = command.lower()
    if any(pattern in lower_command for pattern in BLOCKED_COMMAND_PATTERNS):
        return "ERROR:\nCommand blocked by policy."

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        return "ERROR:\nCommand timed out after 15 seconds."

    if result.returncode == 0:
        return result.stdout.strip() or "(no output)"
    return f"ERROR (code {result.returncode}):\n{result.stderr.strip() or result.stdout.strip()}"
