from pathlib import Path

from blueprint.diagram import render_diagram


def test_render_diagram_writes_a_png(tmp_path: Path):
    target = tmp_path / "diagram.png"
    render_diagram(target)
    assert target.stat().st_size > 1000
