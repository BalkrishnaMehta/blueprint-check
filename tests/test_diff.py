from blueprint.diff import Edge, diff_architecture


def test_sample_story_finds_missing_forbidden_cycle_and_hub():
    findings = diff_architecture(
        ["billing", "auth", "payments", "notifications"],
        [
            ("billing", "auth"),
            ("billing", "payments"),
            ("payments", "notifications"),
            ("notifications", "payments"),
        ],
        [
            Edge("admin", "billing", "admin/service.py:1"),
            Edge("auth", "admin", "auth/service.py:1"),
            Edge("billing", "payments", "billing/service.py:1"),
            Edge("payments", "notifications", "payments/service.py:1"),
            Edge("notifications", "payments", "notifications/service.py:1"),
        ],
    )

    assert [(edge.source, edge.target) for edge in findings.missing] == [("billing", "auth")]
    assert findings.missing[0].evidence == "no import path in the graph"
    assert ("admin", "billing") in {(edge.source, edge.target) for edge in findings.forbidden}
    assert any(set(cycle) == {"payments", "notifications"} for cycle in findings.cycles)
    assert findings.surprise_hub == "admin"
    assert findings.surprise_hub_degree == 1
    assert "auth/service.py:1" in findings.surprise_hub_evidence
    assert findings.has_findings


def test_highest_unlisted_degree_wins_the_hub():
    findings = diff_architecture(
        ["billing", "auth"],
        [("billing", "auth")],
        [
            Edge("auth", "core", "auth/a.py:1"),
            Edge("billing", "core", "billing/a.py:1"),
            Edge("payments", "core", "payments/a.py:1"),
            Edge("admin", "billing", "admin/a.py:2"),
        ],
    )
    assert findings.surprise_hub == "core"
    assert findings.surprise_hub_degree == 3


def test_matching_diagram_has_no_findings():
    findings = diff_architecture(
        ["billing", "payments"],
        [("billing", "payments")],
        [Edge("billing", "payments", "billing/service.py:1")],
    )
    assert findings.has_findings is False
    assert findings.surprise_hub is None
