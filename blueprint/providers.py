"""Diagram readers.

Gemini hosts Gemma 4. Ollama, vLLM, SGLang, and any other OpenAI-compatible
host share one client. The host comes from VISION_BASE_URL.
"""

from __future__ import annotations

import base64
from urllib.parse import urlparse

import httpx

from blueprint.config import Settings, get_settings
from blueprint.vision import PROMPT, DiagramError, parse_model_json

_LOCAL_ALIASES = {"local", "ollama", "vllm", "sglang", "hosted"}
_LOOPBACK = {"127.0.0.1", "localhost", "0.0.0.0", "::1", "ollama"}


def read_image(image: bytes, mime: str, model: str | None, provider: str = "auto") -> dict:
    settings = get_settings()
    selected = select_provider(provider, settings)
    if selected == "gemini":
        text = _gemini_text(image, mime, model or settings.gemini_model, settings.gemini_api_key)
    else:
        text = _local_text(image, mime, model or settings.vision_model, settings)
    return parse_model_json(text)


def select_provider(provider: str, settings: Settings) -> str:
    name = (provider or "auto").strip().lower()
    if name == "auto":
        return "gemini" if settings.gemini_api_key.strip() else "local"
    if name == "gemini":
        return "gemini"
    if name in _LOCAL_ALIASES:
        return "local"
    raise DiagramError("provider must be auto, gemini, local, ollama, vllm, sglang, or hosted")


def _gemini_text(image: bytes, mime: str, model: str, api_key: str) -> str:
    if not api_key.strip():
        raise DiagramError("GEMINI_API_KEY is not set. Re-run with --claims for the offline check.")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key.strip())
    response = client.models.generate_content(
        model=model,
        contents=[types.Part.from_bytes(data=image, mime_type=mime), PROMPT],
        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=1024),
    )
    return getattr(response, "text", None) or ""


def _local_text(image: bytes, mime: str, model: str, settings: Settings) -> str:
    if _remote(settings.vision_base_url) and settings.vision_api_key.strip() in {"", "ollama"}:
        raise DiagramError(
            "VISION_API_KEY is not set. Add the key to .env for a hosted vision server, "
            "or check the claims instead of sending an image."
        )
    url = settings.vision_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(image).decode()}"}},
                ],
            }
        ],
    }
    headers = {"Authorization": f"Bearer {settings.vision_api_key}"}
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=120)
    except httpx.HTTPError as exc:
        raise DiagramError(
            "The vision server is not reachable. "
            "Use a local Gemma through Ollama, vLLM, or SGLang, or set VISION_BASE_URL to an OpenAI-compatible host. "
            "Or check the claims instead of sending an image."
        ) from exc
    if response.status_code >= 400:
        detail = response.text[:180].replace(settings.vision_base_url, "vision server")
        raise DiagramError(
            f"The vision server returned {response.status_code}: {detail}. "
            "Check VISION_BASE_URL, VISION_MODEL, and VISION_API_KEY in .env."
        )
    body = response.json()
    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DiagramError("The vision server returned no message content") from exc


def _remote(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host not in _LOOPBACK
