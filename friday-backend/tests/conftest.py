import os
from pathlib import Path

# Configure deterministic test defaults before project modules are imported.
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("CHECKPOINTER_BACKEND", "memory")
os.environ.setdefault("WORKSPACE_DIR", str(ROOT / "workspace"))
os.environ.setdefault("SKILLS_DIR", str(ROOT / "skills"))
os.environ.setdefault("CHAT_STREAM_TIMEOUT_SECONDS", "30")
