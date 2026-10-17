"""Rich terminal interface for Blueprint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from blueprint import __version__
from blueprint.config import get_settings
from blueprint.diff import Findings
from blueprint.service import execute
from blueprint.vision import DiagramError

console = Console()


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(run(argv))


def run(argv: list[str] | None = None) -> int:
    global console
    console = Console(file=sys.stdout, force_terminal=False, no_color=True, width=88, highlight=False)
    parser = argparse.ArgumentParser(prog="blueprint")
    sub = parser.add_subparsers(dest="cmd", required=True)

    check = sub.add_parser("check", help="Diff a diagram or claims file against the code graph")
    check.add_argument("repo", type=Path)
    check.add_argument("--image", type=Path)
    check.add_argument("--claims", type=Path)
    check.add_argument("--graph", type=Path)
    check.add_argument("--model")
    check.add_argument("--provider", default="auto", choices=["auto", "gemini", "local", "ollama", "vllm", "sglang"])

    info = sub.add_parser("info", help="Show model, key, and graph status")
    info.add_argument("--repo", type=Path, default=Path("sample/app"))

    args = parser.parse_args(argv)
    if args.cmd == "info":
        return _info(args.repo)
    return _check(args)


def _check(args: argparse.Namespace) -> int:
    try:
        findings = execute(
            args.repo,
            claims_path=args.claims,
            image_path=args.image,
            graph_path=args.graph,
            provider=args.provider,
            model=args.model,
        )
    except (DiagramError, FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        console.print(str(exc))
        return 2
    _render(findings)
    return 1 if findings.has_findings else 0


def _info(repo: Path) -> int:
    settings = get_settings()
    graph_file = repo / "graphify-out" / "graph.json"
    key = settings.gemini_api_key.strip()
    console.print(f"blueprint {__version__}")
    console.print(f"gemini model: {settings.gemini_model}")
    console.print(f"GEMINI_API_KEY: {_mask(key)}")
    console.print(f"local vision: {settings.vision_base_url} ({settings.vision_model})")
    state = "present" if graph_file.is_file() else "not found"
    console.print(f"graph: {graph_file if graph_file.is_file() else 'missing'} ({state})")
    return 0


def _render(findings: Findings) -> None:
    console.print(Panel(escape(_edge_block(findings.missing)), title="Missing"))
    console.print(Panel(escape(_edge_block(findings.forbidden)), title="Forbidden"))
    cycle_lines = [" -> ".join([*cycle, cycle[0]]) for cycle in findings.cycles] or ["None"]
    console.print(Panel(escape("\n".join(cycle_lines)), title="Cycle"))
    if findings.surprise_hub:
        hub = f"{findings.surprise_hub} ({findings.surprise_hub_degree} inbound)"
        if findings.surprise_hub_evidence:
            hub = f"{hub}\n{findings.surprise_hub_evidence}"
    else:
        hub = "None"
    console.print(Panel(escape(hub), title="Surprise hub"))


def _edge_block(edges) -> str:
    if not edges:
        return "None"
    return "\n".join(
        f"{edge.source} -> {edge.target}" + (f"\n  {edge.evidence}" if edge.evidence else "")
        for edge in edges
    )


def _mask(value: str) -> str:
    if not value:
        return "not set"
    if len(value) <= 4:
        return "set"
    return f"set (...{value[-4:]})"


if __name__ == "__main__":
    main()
