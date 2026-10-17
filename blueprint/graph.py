"""Load a Graphify graph.json and roll files up to top-level packages."""

from __future__ import annotations

import json
import re
from pathlib import Path

from blueprint.diff import Edge

_IMPORT_HINTS = ("import", "call", "depend", "uses", "reference", "invoke")
_SKIP_HINTS = ("contain", "define", "document", "semant", "similar")
_SKIP_DIRS = {"graphify-out", "__pycache__", ".git", "tests", ".venv", "node_modules"}
_LINE_SUFFIX = re.compile(r":\d+(?:-\d+)?$")
_LINE_TOKEN = re.compile(r"^L(\d+)$")


def load_component_edges(graph_path: Path, repo: Path) -> list[Edge]:
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes = data.get("nodes") or []
    if isinstance(nodes, dict):
        nodes = list(nodes.values())
    raw_edges = data.get("edges") or data.get("links") or []

    by_id: dict[str, dict] = {}
    for node in nodes:
        if isinstance(node, dict) and node.get("id") is not None:
            by_id[str(node["id"])] = node

    selected = [edge for edge in raw_edges if isinstance(edge, dict) and _keep(edge, strict=True)]
    if not selected:
        selected = [edge for edge in raw_edges if isinstance(edge, dict) and _keep(edge, strict=False)]

    rolled: dict[tuple[str, str], Edge] = {}
    for edge in selected:
        src_id = str(edge.get("source") or edge.get("from") or "")
        dst_id = str(edge.get("target") or edge.get("to") or "")
        src_node = by_id.get(src_id, {"id": src_id})
        dst_node = by_id.get(dst_id, {"id": dst_id})
        src = _component(_node_path(src_node), repo)
        dst = _component(_node_path(dst_node), repo)
        if not src or not dst or src == dst:
            continue
        evidence = _node_evidence(src_node) or src_id
        key = (src, dst)
        if key not in rolled or (evidence and not rolled[key].evidence):
            rolled[key] = Edge(src, dst, evidence)
    return list(rolled.values())


def _keep(edge: dict, strict: bool) -> bool:
    relation = str(edge.get("relation") or edge.get("type") or edge.get("label") or "").lower()
    if any(hint in relation for hint in _SKIP_HINTS):
        return False
    if not relation:
        return True
    if any(hint in relation for hint in _IMPORT_HINTS):
        return True
    return not strict


def _node_file(node: dict) -> str:
    for key in ("source_file", "file", "path", "source_location", "loc"):
        value = node.get(key)
        if not isinstance(value, str):
            continue
        text = value.strip().replace("\\", "/")
        if "/" not in text:
            continue
        return _LINE_SUFFIX.sub("", text)
    return ""


def _line_number(node: dict) -> str:
    location = node.get("source_location")
    if not isinstance(location, str):
        return ""
    text = location.strip()
    token = _LINE_TOKEN.match(text)
    if token:
        return token.group(1)
    match = re.search(r":(\d+)$", text)
    return match.group(1) if match else ""


def _node_evidence(node: dict) -> str:
    file = _node_file(node)
    line = _line_number(node)
    if file and line:
        return f"{file}:{line}"
    return file or str(node.get("id", ""))


def _node_path(node: dict) -> str:
    return _node_file(node)


def _component(source: str, repo: Path) -> str | None:
    text = source.replace("\\", "/")
    repo_text = repo.resolve().as_posix().rstrip("/")
    if repo_text and repo_text.lower() in text.lower():
        index = text.lower().rfind(repo_text.lower())
        text = text[index + len(repo_text) :]
    if "/" not in text:
        return None
    text = text.lstrip("/")
    parts = [part for part in text.split("/") if part and part != "."]
    while parts and parts[0].lower() in {"sample", "app"}:
        parts = parts[1:]
    if not parts:
        return None
    name = parts[0]
    if name.endswith(".py") or name.lower() in _SKIP_DIRS or name.startswith("."):
        return None
    return name.lower()


def resolve_graph(repo: Path, explicit: Path | None = None) -> Path:
    path = explicit or (repo / "graphify-out" / "graph.json")
    if not path.is_file():
        raise FileNotFoundError(f"No graph at {path}. Run Graphify on the repo, or pass --graph.")
    return path
