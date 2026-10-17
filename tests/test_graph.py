import json
from pathlib import Path

from blueprint.graph import load_component_edges

ROOT = Path(__file__).resolve().parents[1]


def test_loader_rolls_files_up_to_packages():
    edges = load_component_edges(ROOT / "tests" / "fixtures" / "graph.json", ROOT / "sample" / "app")
    pairs = {(edge.source, edge.target) for edge in edges}
    assert pairs == {
        ("admin", "billing"),
        ("auth", "admin"),
        ("billing", "payments"),
        ("payments", "notifications"),
        ("notifications", "payments"),
    }
    admin = next(edge for edge in edges if edge.source == "admin")
    assert "admin/service.py" in admin.evidence


def test_committed_graphify_graph_tells_the_sample_story():
    from blueprint.diff import diff_architecture

    claims = json.loads((ROOT / "sample" / "claims.json").read_text(encoding="utf-8"))
    edges = load_component_edges(
        ROOT / "sample" / "app" / "graphify-out" / "graph.json",
        ROOT / "sample" / "app",
    )
    findings = diff_architecture(
        claims["components"],
        [(edge["from"], edge["to"]) for edge in claims["edges"]],
        edges,
    )
    assert [(edge.source, edge.target) for edge in findings.missing] == [("billing", "auth")]
    assert ("admin", "billing") in {(edge.source, edge.target) for edge in findings.forbidden}
    assert any(set(cycle) == {"payments", "notifications"} for cycle in findings.cycles)
    assert findings.surprise_hub == "admin"


def test_loader_ignores_contains_edges(tmp_path: Path):
    graph = tmp_path / "graph.json"
    graph.write_text(
        """
        {
          "nodes": [
            {"id": "a", "source_file": "billing/service.py"},
            {"id": "b", "source_file": "payments/service.py"}
          ],
          "edges": [
            {"source": "a", "target": "b", "relation": "contains"},
            {"source": "a", "target": "b", "relation": "imports"}
          ]
        }
        """,
        encoding="utf-8",
    )
    edges = load_component_edges(graph, tmp_path)
    assert [(edge.source, edge.target) for edge in edges] == [("billing", "payments")]
