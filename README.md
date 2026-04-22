# Project Friday

> A self-improving, tool-using AI agent with a ReAct brain, sandboxed OS hands, and a growing skill library.

## Monorepo Layout

- `friday-backend/` — FastAPI + LangGraph + tools + skill agents
- `friday-frontend/` — Next.js chat UI + API proxy
- `docs/` — LaTeX architecture & API documentation

## Features

| Feature | Description |
|---|---|
| **ReAct Loop** | Reason → Act → Observe → Repeat — genuine agentic reasoning |
| **Sandboxed Tools** | File R/W, shell commands with allowlist enforcement, symlink detection |
| **Skill Library** | Save & reuse tested scripts; dynamic tool registration |
| **Skill Agents** | Framework-specific knowledge bundles (Next.js, FastAPI, etc.) with dos/don'ts, style guides, scaffold steps |
| **Self-Improvement** | Voyager-inspired: writes tool → tests → commits → reuses later |
| **SSE Streaming** | Real-time thought/tool/result streaming to the chat UI |
| **Multi-Provider LLM** | Groq (cloud, recommended), LM Studio (local), Ollama — switchable via env |
| **Structured Logging** | Automatic file rotation, performance tracking, error tracing — see `friday-backend/LOGGING.md` |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- **Groq API key** (recommended) **or** LM Studio **or** Ollama

### ⚠️ Migration Note (v0.2.0)

If upgrading from a previous version, delete the old checkpoint database to avoid compatibility issues:

```powershell
Remove-Item -Force friday-backend/checkpoints/friday_state.sqlite*
```

This is required because v0.2.0 migrated from synchronous `SqliteSaver` to async `AsyncSqliteSaver`.

### One-Command Launch

```powershell
.\run-friday.ps1
```

### Manual Setup

**Backend:**

```powershell
cd friday-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then edit .env with your keys
uvicorn main:app --reload --port 8000
```

**Frontend:**

```powershell
cd friday-frontend
npm install
copy .env.example .env.local
npm run dev
```

## API Endpoints

### Backend (`:8000`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | SSE streaming chat (ReAct loop) |
| `GET` | `/workspace` | Recursive file tree of the sandbox |
| `GET` | `/skills` | Committed skill scripts |
| `GET` | `/agents` | Registered Skill Agents |

### Frontend Proxy (`:3000`)

| Method | Path | Proxies to |
|---|---|---|
| `POST` | `/api/friday` | `/chat` |
| `GET` | `/api/friday` | `/workspace` |
| `GET` | `/api/friday/skills` | `/skills` |
| `GET` | `/api/friday/agents` | `/agents` |

## Key Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `MODEL_PROVIDER` | `groq` | LLM provider: `groq` (recommended), `lmstudio`, or `ollama` |
| `GROQ_API_KEY` | *(required)* | Your Groq API key for cloud LLM access |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model to use |
| `MAX_TOKENS` | `8000` | Maximum tokens per LLM response |
| `RECURSION_LIMIT` | `50` | LangGraph recursion hard cap |
| `MAX_HISTORY_MESSAGES` | `50` | Number of recent messages to keep in context |
| `MAX_INPUT_CHARS` | `100000` | Maximum input characters (for large context models) |
| `WORKSPACE_DIR` | `./workspace` | Sandboxed file-system root |
| `SKILLS_DIR` | `./skills` | Skill library + agents directory |
| `COMMAND_TIMEOUT` | `120` | Max seconds for subprocess execution |
| `COMMAND_ALLOWLIST` | `python,npm,...` | Comma-separated allowed command prefixes |
| `ALLOWED_TARGET_DIRS` | *(empty)* | Dirs where agent can scaffold projects |
| `MAX_TOOL_ATTEMPTS` | `3` | Retry budget for failed tool executions |

## Skill Agent System

Skill Agents are framework-specific knowledge bundles stored in `skills/agents/<name>/`:

```
skills/agents/nextjs/
├── manifest.json       # Metadata, trigger patterns, dos/don'ts
├── style_guide.md      # Auto-generated best-practice guide
└── templates/          # Optional starter files
```

The agent **auto-creates** these when it encounters a framework it hasn't seen before. On subsequent requests, it loads the existing agent's rules into its context.

## Security Model

| Layer | Mechanism |
|---|---|
| **Path sandboxing** | `safe_path()` blocks traversal, symlinks, and protected segments |
| **Command allowlist** | Only permitted command prefixes execute; shell chaining blocked |
| **External dirs** | `ALLOWED_TARGET_DIRS` gates access outside the sandbox |
| **Retry cap** | `MAX_TOOL_ATTEMPTS=3` prevents infinite loops |
| **Recursion limit** | `RECURSION_LIMIT=25` hard-caps LangGraph cycles |
| **Token budget** | `MAX_TOKENS=2048` per LLM call |

## Documentation

Full architecture and API docs are in `docs/`. Build PDFs:

```powershell
cd docs
pdflatex friday_architecture.tex
pdflatex friday_api_reference.tex
```

### Logging

Friday includes a comprehensive logging system for debugging and monitoring. See `friday-backend/LOGGING.md` for:
- Log file locations and rotation
- What gets logged (graph events, tool calls, performance, errors)
- How to use logs for troubleshooting
- Best practices for adding logging to new code

**Quick log access:**
```powershell
# View main log
tail -f friday-backend/logs/friday.log

# View errors only
tail -f friday-backend/logs/friday_errors.log

# Search for specific thread
grep "thread_id=abc123" friday-backend/logs/friday.log
```

---

*Stack: Python 3.11+ · FastAPI · LangGraph · LangChain · Next.js 15 · React 19 · TypeScript*
