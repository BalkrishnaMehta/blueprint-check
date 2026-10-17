import json
from pathlib import Path

import pytest

from blueprint.cli import main, run
from blueprint.vision import parse_model_json

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = json.loads((ROOT / "sample" / "claims.json").read_text(encoding="utf-8"))


def test_parse_fenced_gemma_json_matches_claims_file():
    body = json.dumps(CLAIMS)
    parsed = parse_model_json(f"Here is the diagram:\n```json\n{body}\n```\n")
    assert parsed["components"] == CLAIMS["components"]
    assert parsed["edges"] == CLAIMS["edges"]


def test_parse_rejects_prose():
    with pytest.raises(Exception, match="not valid architecture JSON"):
        parse_model_json("I think billing talks to auth.")


def test_cli_claims_exits_1_and_names_the_four_findings(capsys):
    code = run(
        [
            "check",
            str(ROOT / "sample" / "app"),
            "--claims",
            str(ROOT / "sample" / "claims.json"),
            "--graph",
            str(ROOT / "tests" / "fixtures" / "graph.json"),
        ]
    )
    assert code == 1
    out = capsys.readouterr().out
    assert "Missing" in out
    assert "billing -> auth" in out
    assert "Forbidden" in out
    assert "admin -> billing" in out
    assert "Cycle" in out
    assert "payments -> notifications -> payments" in out or "notifications -> payments -> notifications" in out
    assert "Surprise hub" in out
    assert "admin" in out


def test_image_without_key_points_at_claims(monkeypatch, capsys):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    code = run(
        [
            "check",
            str(ROOT / "sample" / "app"),
            "--image",
            str(ROOT / "sample" / "diagram.png"),
            "--provider",
            "gemini",
        ]
    )
    assert code == 2
    assert "--claims" in capsys.readouterr().out


def test_info_masks_a_missing_key(monkeypatch, capsys):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    code = run(["info", "--repo", str(ROOT / "sample" / "app")])
    assert code == 0
    out = capsys.readouterr().out
    assert "gemma-4-26b-a4b-it" in out
    assert "not set" in out


def test_main_uses_system_exit():
    with pytest.raises(SystemExit) as caught:
        main(["info", "--repo", str(ROOT / "sample" / "app")])
    assert caught.value.code == 0
