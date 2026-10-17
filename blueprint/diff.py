"""Compare a claimed architecture with the dependency graph. No network."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    evidence: str = ""


@dataclass(frozen=True)
class Findings:
    missing: tuple[Edge, ...]
    forbidden: tuple[Edge, ...]
    cycles: tuple[tuple[str, ...], ...]
    surprise_hub: str | None
    surprise_hub_degree: int
    surprise_hub_evidence: str

    @property
    def has_findings(self) -> bool:
        return bool(self.missing or self.forbidden or self.cycles or self.surprise_hub)


def normalize_name(name: str) -> str:
    text = name.strip().lower().replace("_", "").replace("-", "").replace(" ", "")
    for suffix in ("service", "module", "component"):
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
    return text


def diff_architecture(
    diagram_components: list[str],
    diagram_edges: list[tuple[str, str]],
    graph_edges: list[Edge],
) -> Findings:
    """Return missing arrows, extra dependencies, cycles, and an unlisted hub."""
    listed = {normalize_name(name) for name in diagram_components if normalize_name(name)}
    claimed = {
        (normalize_name(src), normalize_name(dst))
        for src, dst in diagram_edges
        if normalize_name(src) and normalize_name(dst) and normalize_name(src) != normalize_name(dst)
    }
    actual: dict[tuple[str, str], Edge] = {}
    for edge in graph_edges:
        src, dst = normalize_name(edge.source), normalize_name(edge.target)
        if not src or not dst or src == dst:
            continue
        key = (src, dst)
        if key not in actual or (edge.evidence and not actual[key].evidence):
            actual[key] = Edge(src, dst, edge.evidence)

    missing = tuple(
        Edge(src, dst, "no import path in the graph")
        for src, dst in sorted(claimed - set(actual))
    )
    forbidden = tuple(actual[key] for key in sorted(set(actual) - claimed))
    cycles = _cycles(set(actual))

    inbound: dict[str, list[Edge]] = {}
    components: set[str] = set()
    for edge in actual.values():
        components.add(edge.source)
        components.add(edge.target)
        inbound.setdefault(edge.target, []).append(edge)

    unlisted = sorted(components - listed)
    hub: str | None = None
    degree = 0
    evidence = ""
    if unlisted:
        hub = max(unlisted, key=lambda name: (len(inbound.get(name, [])), name))
        incoming = inbound.get(hub, [])
        degree = len(incoming)
        evidence = "; ".join(edge.evidence for edge in incoming if edge.evidence)

    return Findings(missing, forbidden, cycles, hub, degree, evidence)


def _cycles(edges: set[tuple[str, str]]) -> tuple[tuple[str, ...], ...]:
    adjacency: dict[str, set[str]] = {}
    for src, dst in edges:
        adjacency.setdefault(src, set()).add(dst)
        adjacency.setdefault(dst, set())

    found: set[tuple[str, ...]] = set()

    def record(path: list[str]) -> None:
        rotations = [tuple(path[i:] + path[:i]) for i in range(len(path))]
        found.add(min(rotations))

    def walk(start: str, node: str, path: list[str], seen: set[str]) -> None:
        for nxt in sorted(adjacency.get(node, ())):
            if nxt == start and len(path) >= 2:
                record(path)
            elif nxt not in seen:
                walk(start, nxt, path + [nxt], seen | {nxt})

    for start in sorted(adjacency):
        walk(start, start, [start], {start})

    return tuple(sorted(found))
