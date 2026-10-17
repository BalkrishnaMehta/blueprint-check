"""JSON shapes returned by the API."""

from pydantic import BaseModel, Field

from blueprint.diff import Findings


class EdgeOut(BaseModel):
    source: str
    target: str
    evidence: str = ""


class HubOut(BaseModel):
    name: str
    degree: int
    evidence: str = ""


class CheckOut(BaseModel):
    has_findings: bool
    missing: list[EdgeOut] = Field(default_factory=list)
    forbidden: list[EdgeOut] = Field(default_factory=list)
    cycles: list[list[str]] = Field(default_factory=list)
    surprise_hub: HubOut | None = None


class InfoOut(BaseModel):
    version: str
    gemini_model: str
    gemini_api_key: str
    vision_base_url: str
    vision_model: str
    graph: str


def to_check_out(findings: Findings) -> CheckOut:
    hub = None
    if findings.surprise_hub:
        hub = HubOut(
            name=findings.surprise_hub,
            degree=findings.surprise_hub_degree,
            evidence=findings.surprise_hub_evidence,
        )
    return CheckOut(
        has_findings=findings.has_findings,
        missing=[EdgeOut(source=edge.source, target=edge.target, evidence=edge.evidence) for edge in findings.missing],
        forbidden=[EdgeOut(source=edge.source, target=edge.target, evidence=edge.evidence) for edge in findings.forbidden],
        cycles=[list(cycle) for cycle in findings.cycles],
        surprise_hub=hub,
    )
