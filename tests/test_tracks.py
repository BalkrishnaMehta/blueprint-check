"""Independent graphs, not the billing story the sample was written to tell."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from blueprint.api import app
from blueprint.service import execute

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_orders_graph_matches_its_diagram():
    findings = execute(ROOT / "tracks" / "clean", claims_path=ROOT / "tracks" / "clean" / "claims.json")
    assert findings.has_findings is False
    assert findings.missing == ()
    assert findings.forbidden == ()
    assert findings.cycles == ()
    assert findings.surprise_hub is None


def test_warehouse_graph_has_a_different_shape_than_the_sample():
    findings = execute(ROOT / "tracks" / "drift", claims_path=ROOT / "tracks" / "drift" / "claims.json")
    assert [(edge.source, edge.target) for edge in findings.missing] == [("checkout", "shipping")]
    assert ("checkout", "warehouse") in {(edge.source, edge.target) for edge in findings.forbidden}
    assert findings.cycles == (("inventory", "warehouse"),)
    assert findings.surprise_hub == "inventory"
    assert findings.surprise_hub_degree == 1
    assert "warehouse/service.py" in findings.surprise_hub_evidence


def test_examples_run_through_the_api():
    listed = client.get("/v1/examples")
    assert listed.status_code == 200
    by_id = {item["id"]: item for item in listed.json()}
    assert set(by_id) == {"sample", "orders", "warehouse"}

    orders = client.post(
        "/v1/checks",
        data={"repo": by_id["orders"]["repo"], "claims": json.dumps(by_id["orders"]["claims"])},
    )
    assert orders.status_code == 200
    assert orders.json()["has_findings"] is False

    warehouse = client.post(
        "/v1/checks",
        data={"repo": by_id["warehouse"]["repo"], "claims": json.dumps(by_id["warehouse"]["claims"])},
    )
    assert warehouse.status_code == 200
    body = warehouse.json()
    assert body["missing"][0]["target"] == "shipping"
    assert body["surprise_hub"]["name"] == "inventory"


def test_image_without_a_gemini_key_names_the_offline_path(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    response = client.post(
        "/v1/checks",
        data={"provider": "gemini", "repo": "sample/app"},
        files={"image": ("diagram.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert response.status_code == 400
    assert "GEMINI_API_KEY" in response.json()["detail"]
    assert "--claims" in response.json()["detail"]
