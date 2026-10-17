import json

import httpx

from blueprint.config import Settings
from blueprint.providers import read_image, select_provider
from blueprint.vision import DiagramError

CLAIMS = {
    "components": ["billing", "auth"],
    "edges": [{"from": "billing", "to": "auth"}],
}


def test_auto_uses_gemini_only_when_a_key_is_set():
    assert select_provider("auto", Settings(gemini_api_key="secret")) == "gemini"
    assert select_provider("auto", Settings(gemini_api_key="")) == "local"
    assert select_provider("vllm", Settings(gemini_api_key="secret")) == "local"
    assert select_provider("sglang", Settings()) == "local"


def test_local_provider_reads_openai_compatible_json(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "gemma4:e4b"
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(CLAIMS)}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr("blueprint.providers.httpx.post", client.post)
    monkeypatch.setattr(
        "blueprint.providers.get_settings",
        lambda: Settings(gemini_api_key="", vision_model="gemma4:e4b", vision_base_url="http://127.0.0.1:11434/v1"),
    )
    parsed = read_image(b"png", "image/png", None, "ollama")
    assert parsed["components"] == ["billing", "auth"]
    assert parsed["edges"] == [{"from": "billing", "to": "auth"}]


def test_unknown_provider_is_rejected():
    try:
        select_provider("hosted", Settings())
    except DiagramError as exc:
        assert "provider" in str(exc)
    else:
        raise AssertionError("expected DiagramError")
