"""
OS tools for the Friday agent.

Provides sandboxed file-system and shell operations.  Every path-based tool
enforces a workspace prefix via ``safe_path()``.  Shell execution uses a
command **allowlist** — only explicitly permitted command prefixes are run.
"""

import os
import re
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WORKSPACE_DIR: str = os.path.abspath(os.getenv("WORKSPACE_DIR", "./workspace"))

#: Directories *outside* the workspace where the agent may scaffold projects.
#: Comma-separated absolute paths stored in the environment variable
#: ``ALLOWED_TARGET_DIRS``.  Example:
#:     ALLOWED_TARGET_DIRS=D:/Projects,C:/Users/dawoo/Desktop
ALLOWED_TARGET_DIRS: list[str] = [
    os.path.abspath(d.strip())
    for d in os.getenv("ALLOWED_TARGET_DIRS", "").split(",")
    if d.strip()
]

#: Maximum seconds a subprocess may run before being killed.
COMMAND_TIMEOUT: int = int(os.getenv("COMMAND_TIMEOUT", "120"))

#: Path segments that must never appear in resolved file paths.
BLOCKED_SEGMENTS: set[str] = {".env", ".ssh", ".git", ".gnupg", ".aws"}

#: Only commands whose first token matches one of these prefixes are allowed.
#: The list is case-insensitive.  Add more as needed.
COMMAND_ALLOWLIST: list[str] = [
    p.strip().lower()
    for p in os.getenv(
        "COMMAND_ALLOWLIST",
        "python,pip,npm,npx,node,mkdir,ls,dir,cat,type,echo,git,cd,pwd,"
        "touch,cp,copy,mv,move,head,tail,find,grep,curl,wget,pytest,cargo,"
        "dotnet,go,java,javac,gcc,g++,make,cmake,tsc,eslint,prettier",
    ).split(",")
    if p.strip()
]

# ---------------------------------------------------------------------------
# Path safety helpers
# ---------------------------------------------------------------------------


def safe_path(relative: str) -> str:
    """Resolve *relative* under ``WORKSPACE_DIR``, blocking escapes.

    Raises ``PermissionError`` when:
    * The path is absolute.
    * Traversal (``../../``) escapes the workspace.
    * A blocked segment (``.env``, ``.ssh``, …) appears in the path.
    * The resolved path is a symbolic link pointing outside the workspace.
    """
    candidate = Path(relative)
    if candidate.is_absolute():
        raise PermissionError("Absolute paths are not allowed inside the workspace.")

    resolved = os.path.realpath(os.path.join(WORKSPACE_DIR, relative))

    if os.path.commonpath([WORKSPACE_DIR, resolved]) != WORKSPACE_DIR:
        raise PermissionError("Path escape attempt blocked.")

    # Symlink detection: if the result of realpath differs from normpath,
    # a symlink was resolved.  Verify the *target* is still in the workspace.
    logical = os.path.normpath(os.path.join(WORKSPACE_DIR, relative))
    if logical != resolved:
        # resolved followed a symlink — make sure it didn't land outside
        if os.path.commonpath([WORKSPACE_DIR, resolved]) != WORKSPACE_DIR:
            raise PermissionError(
                "Symbolic link target is outside the workspace — access denied."
            )

    parts = {part.lower() for part in Path(resolved).parts}
    if any(segment in parts for segment in BLOCKED_SEGMENTS):
        raise PermissionError(f"Access to protected path segment blocked.")

    return resolved


def safe_target_path(absolute: str) -> str:
    """Validate that *absolute* falls inside one of ``ALLOWED_TARGET_DIRS``.

    Used by ``execute_in_directory`` to allow project scaffolding outside
    the sandbox.  Raises ``PermissionError`` when the path is not under any
    allowed directory.
    """
    resolved = os.path.realpath(absolute)
    for allowed in ALLOWED_TARGET_DIRS:
        try:
            if os.path.commonpath([allowed, resolved]) == allowed:
                return resolved
        except ValueError:
            continue
    raise PermissionError(
        f"Path '{absolute}' is not inside any allowed target directory.  "
        f"Allowed: {ALLOWED_TARGET_DIRS or '(none configured — set ALLOWED_TARGET_DIRS)'}"
    )


def _ensure_workspace() -> None:
    """Create the workspace directory if it does not exist."""
    os.makedirs(WORKSPACE_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Command safety helpers
# ---------------------------------------------------------------------------

#: Patterns that indicate an absolute-path reference on Windows or Unix.
_ABSOLUTE_PATH_PATTERNS = [
    re.compile(r"(^|\s)[a-zA-Z]:[\\/]"),
    re.compile(r"(^|\s)/[a-zA-Z]/"),
]

#: Dangerous shell operators that could be used for injection.
_DANGEROUS_OPERATORS = ["&&", "||", "|", ";", "`", "$(", "${"]


def _is_command_allowed(command: str) -> tuple[bool, str]:
    """Check *command* against the allowlist.

    Returns ``(True, "")`` if the command is permitted, otherwise
    ``(False, reason)``.
    """
    stripped = command.strip()
    if not stripped:
        return False, "Empty command."

    # Reject commands that contain dangerous shell operators to prevent
    # chaining.  (The user can still invoke multiple tools sequentially.)
    for op in _DANGEROUS_OPERATORS:
        if op in stripped:
            return False, (
                f"Shell operator '{op}' is not allowed.  "
                "Run each command separately instead of chaining."
            )

    first_token = stripped.split()[0].lower()
    # Strip common path prefixes so "python3", "./node_modules/.bin/tsc" etc.
    # still match the allowlist.
    first_token_base = os.path.basename(first_token).removesuffix(".exe")

    if first_token_base in COMMAND_ALLOWLIST:
        return True, ""

    return False, (
        f"Command '{first_token}' is not on the allowlist.  "
        f"Allowed: {', '.join(sorted(COMMAND_ALLOWLIST))}"
    )


# ---------------------------------------------------------------------------
# File tools
# ---------------------------------------------------------------------------


@tool
def list_files(directory: str = ".") -> str:
    """Lists files and folders at the given path within the workspace."""
    _ensure_workspace()
    target = safe_path(directory)
    entries = sorted(os.listdir(target))
    return "\n".join(entries) if entries else "(empty directory)"


@tool
def read_file(filename: str) -> str:
    """Reads and returns the full contents of a file in the workspace."""
    _ensure_workspace()
    with open(safe_path(filename), "r", encoding="utf-8") as fh:
        return fh.read()


@tool
def write_to_file(filename: str, content: str) -> str:
    """Creates or overwrites a file in the workspace with the given content."""
    _ensure_workspace()
    path = safe_path(filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return f"Wrote {len(content)} chars to {filename}"


@tool
def append_to_file(filename: str, content: str) -> str:
    """Appends content to an existing file in the workspace (creates if missing)."""
    _ensure_workspace()
    path = safe_path(filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(content)
    return f"Appended {len(content)} chars to {filename}"


@tool
def create_directory(directory: str) -> str:
    """Creates a directory (and parents) inside the workspace."""
    _ensure_workspace()
    path = safe_path(directory)
    os.makedirs(path, exist_ok=True)
    return f"Directory created: {directory}"


@tool
def delete_file(filename: str) -> str:
    """Deletes a single file inside the workspace.  Cannot delete directories."""
    _ensure_workspace()
    path = safe_path(filename)
    if os.path.isdir(path):
        return "ERROR: Use a shell command to remove directories.  This tool only deletes files."
    if not os.path.exists(path):
        return f"File not found: {filename}"
    os.remove(path)
    return f"Deleted: {filename}"


# ---------------------------------------------------------------------------
# Shell tools
# ---------------------------------------------------------------------------


@tool
def execute_bash_command(command: str) -> str:
    """Runs an allowlisted shell command inside the workspace.

    Only commands whose first word appears in the configured allowlist are
    permitted.  Shell chaining operators (``&&``, ``|``, ``;``, …) are
    rejected — run each command as a separate tool call instead.
    """
    _ensure_workspace()

    allowed, reason = _is_command_allowed(command)
    if not allowed:
        return f"BLOCKED: {reason}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return f"ERROR: Command timed out after {COMMAND_TIMEOUT}s."

    if result.returncode == 0:
        return result.stdout.strip() or "(no output)"
    return f"ERROR (code {result.returncode}):\n{result.stderr.strip() or result.stdout.strip()}"


@tool
def execute_in_directory(directory: str, command: str) -> str:
    """Runs an allowlisted shell command in a specified *external* directory.

    The directory must be inside one of the configured ``ALLOWED_TARGET_DIRS``.
    Use this for project scaffolding (``npx create-next-app``, etc.) outside
    the sandbox workspace.
    """
    try:
        target = safe_target_path(directory)
    except PermissionError as exc:
        return f"BLOCKED: {exc}"

    allowed, reason = _is_command_allowed(command)
    if not allowed:
        return f"BLOCKED: {reason}"

    os.makedirs(target, exist_ok=True)

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=target,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return f"ERROR: Command timed out after {COMMAND_TIMEOUT}s."

    if result.returncode == 0:
        return result.stdout.strip() or "(no output)"
    return f"ERROR (code {result.returncode}):\n{result.stderr.strip() or result.stdout.strip()}"
