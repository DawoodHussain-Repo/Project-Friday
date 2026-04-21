# Project Friday

Friday is a ReAct-style personal AI agent with sandboxed tools, SSE streaming, and a skill library.

## Monorepo Layout

- `friday-backend`: FastAPI + LangGraph + tools
- `friday-frontend`: Next.js chat UI + API proxy

## Local Model Setup (LM Studio)

Google/Gemini is intentionally not included. Local testing uses LM Studio by default to avoid Groq quota burn.

Backend environment example:

- `MODEL_PROVIDER=lmstudio`
- `LMSTUDIO_BASE_URL=http://localhost:1234/v1`
- `LMSTUDIO_MODEL=local-model`

Optional fallback:

- `MODEL_PROVIDER=groq`
- `GROQ_API_KEY=...`
- `GROQ_MODEL=llama-3.3-70b-versatile`

## Run Backend

```powershell
cd friday-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000
```

## Run Frontend

```powershell
cd friday-frontend
npm install
copy .env.example .env.local
npm run dev
```

## API Endpoints

Backend:

- `POST /chat` (SSE stream)
- `GET /workspace`
- `GET /skills`

Frontend proxy:

- `POST /api/friday` (chat stream)
- `GET /api/friday` (workspace tree)
