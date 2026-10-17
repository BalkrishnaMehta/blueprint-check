"""Turn a Gemma reply, or a claims file, into components and edges."""

from __future__ import annotations

import json
import re
from pathlib import Path

from blueprint.diff import normalize_name

DEFAULT_MODEL = "gemma-4-26b-a4b-it"

PROMPT = """Read this architecture diagram.
Return one JSON object and nothing else:
{"components": ["billing"], "edges": [{"from": "billing", "to": "auth"}]}
Rules:
- components are the words inside boxes, lowercased
- edges are arrows you can see, from the box at the tail to the box at the head
- do not invent a box or an arrow that is not drawn
- no markdown
"""


class DiagramError(RuntimeError):
    """The diagram could not be turned into claims."""


def load_claims(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DiagramError(f"{path} is not JSON: {exc}") from exc
    return claims_from_mapping(data)


def parse_model_json(text: str) -> dict:
    if not text or not text.strip():
        raise DiagramError("Gemma returned an empty response")
    return claims_from_mapping(_extract_json(text))


def read_diagram(image_path: Path, model: str | None = None, provider: str = "auto") -> dict:
    if not image_path.is_file():
        raise DiagramError(f"Diagram not found: {image_path}")
    from blueprint.providers import read_image

    return read_image(image_path.read_bytes(), _mime(image_path), model, provider)


def claims_from_mapping(data: object) -> dict:
    if not isinstance(data, dict):
        raise DiagramError("Architecture JSON must be an object")
    raw_components = data.get("components")
    raw_edges = data.get("edges")
    if not isinstance(raw_components, list) or not isinstance(raw_edges, list):
        raise DiagramError("Architecture JSON needs components and edges arrays")

    components: list[str] = []
    for item in raw_components:
        name = normalize_name(str(item))
        if name and name not in components:
            components.append(name)

    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in raw_edges:
        if not isinstance(item, dict):
            raise DiagramError("Each edge must be an object")
        src = normalize_name(str(item.get("from") or item.get("source") or ""))
        dst = normalize_name(str(item.get("to") or item.get("target") or ""))
        if not src or not dst or src == dst:
            continue
        if (src, dst) not in seen:
            seen.add((src, dst))
            edges.append({"from": src, "to": dst})
    if not components:
        raise DiagramError("Architecture JSON listed no components")
    return {"components": components, "edges": edges}


def _extract_json(text: str) -> object:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    payload = fenced.group(1) if fenced else text
    start = payload.find("{")
    end = payload.rfind("}")
    if start < 0 or end <= start:
        raise DiagramError("Gemma response was not valid architecture JSON")
    try:
        return json.loads(payload[start : end + 1])
    except json.JSONDecodeError as exc:
        raise DiagramError("Gemma response was not valid architecture JSON") from exc


def _mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"
