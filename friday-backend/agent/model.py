import os
from typing import Any

from dotenv import load_dotenv
import httpx
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

load_dotenv()


def _discover_lmstudio_model(base_url: str, api_key: str, requested_model: str) -> str:
    models_url = f"{base_url.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = httpx.get(models_url, headers=headers, timeout=4.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(
            "Could not connect to LM Studio model registry. "
            "Ensure LM Studio local server is running on http://localhost:1234."
        ) from exc

    payload: dict[str, Any]
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("LM Studio returned invalid JSON for /models.") from exc

    raw_models = payload.get("data", [])
    model_ids = [
        str(item.get("id", "")).strip()
        for item in raw_models
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    ]

    if not model_ids:
        raise RuntimeError(
            "No models loaded in LM Studio. Load a model in the Developer tab "
            "or run: lms load <model>."
        )

    if requested_model and requested_model != "local-model" and requested_model in model_ids:
        return requested_model

    return model_ids[0]


def get_local_llm(temperature: float | None = None):
    """Connects to the local LM Studio OpenAI-compatible server."""
    max_tokens = int(os.getenv("MAX_TOKENS", "1000"))
    base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    api_key = os.getenv("LMSTUDIO_API_KEY", "lm-studio")
    requested_model = os.getenv("LMSTUDIO_MODEL", "local-model")
    auto_select = os.getenv("LMSTUDIO_AUTO_SELECT", "true").lower() == "true"

    resolved_model = (
        _discover_lmstudio_model(base_url, api_key, requested_model)
        if auto_select
        else requested_model
    )

    resolved_temperature = (
        temperature
        if temperature is not None
        else float(os.getenv("LMSTUDIO_TEMPERATURE", "0.7"))
    )

    return ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        temperature=resolved_temperature,
        model=resolved_model,
        max_tokens=max_tokens,
    )


def get_llm():
    provider = os.getenv("MODEL_PROVIDER", "lmstudio").lower()
    max_tokens = int(os.getenv("MAX_TOKENS", "1000"))

    if provider == "lmstudio":
        return get_local_llm()

    if provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        return ChatOllama(model=model, temperature=0)

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return ChatGroq(model=model, temperature=0, max_tokens=max_tokens)
