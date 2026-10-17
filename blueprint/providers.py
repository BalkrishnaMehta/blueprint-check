"""Diagram readers.

Gemini hosts Gemma 4. Ollama, vLLM, and SGLang share one OpenAI-compatible client.
"""

from __future__ import annotations

import base64

import httpx

from blueprint.config import Settings, get_settings
from blueprint.vision import PROMPT, DiagramError, parse_model_json

_LOCAL_ALIASES = {"local", "ollama", "vllm", "sglang"}


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
    raise DiagramError("provider must be auto, gemini, local, ollama, vllm, or sglang")


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
            f"Local vision server is not reachable at {settings.vision_base_url}. "
            "Start Ollama, point VISION_BASE_URL at vLLM (:8000/v1) or SGLang (:30000/v1), "
            "or re-run with --claims for the offline check."
        ) from exc
    if response.status_code >= 400:
        raise DiagramError(f"Local vision server returned {response.status_code}: {response.text[:300]}")
    body = response.json()
    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DiagramError("Local vision server returned no message content") from exc
