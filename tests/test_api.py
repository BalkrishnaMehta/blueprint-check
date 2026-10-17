import json
from pathlib import Path

from fastapi.testclient import TestClient

from blueprint.api import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_check_accepts_claims_json():
    claims = (ROOT / "sample" / "claims.json").read_text(encoding="utf-8")
    response = client.post(
        "/v1/checks",
        data={
            "claims": claims,
            "repo": str(ROOT / "sample" / "app"),
            "graph": str(ROOT / "tests" / "fixtures" / "graph.json"),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["has_findings"] is True
    assert body["missing"][0]["source"] == "billing"
    assert body["missing"][0]["target"] == "auth"
    assert any(edge["source"] == "admin" and edge["target"] == "billing" for edge in body["forbidden"])
    assert ["notifications", "payments"] in body["cycles"]
    assert body["surprise_hub"]["name"] == "admin"


def test_check_rejects_an_empty_request():
    response = client.post("/v1/checks")
    assert response.status_code == 400


def test_sample_claims_match_the_file():
    response = client.get("/v1/sample/claims")
    assert response.status_code == 200
    assert response.json() == json.loads((ROOT / "sample" / "claims.json").read_text(encoding="utf-8"))
