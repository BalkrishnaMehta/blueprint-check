"""One check, used by the CLI and the API."""

from __future__ import annotations

from pathlib import Path

from blueprint.diff import Findings, diff_architecture
from blueprint.graph import load_component_edges, resolve_graph
from blueprint.providers import read_image
from blueprint.vision import DiagramError, load_claims


def execute(
    repo: Path,
    claims_path: Path | None = None,
    image_path: Path | None = None,
    image: tuple[bytes, str] | None = None,
    graph_path: Path | None = None,
    provider: str = "auto",
    model: str | None = None,
    claims_data: dict | None = None,
) -> Findings:
    if claims_path is None and image_path is None and image is None and claims_data is None:
        raise DiagramError("Pass --claims or --image.")
    edges = load_component_edges(resolve_graph(repo, graph_path), repo)
    claims = _claims(claims_path, image_path, image, claims_data, provider, model)
    return diff_architecture(
        claims["components"],
        [(edge["from"], edge["to"]) for edge in claims["edges"]],
        edges,
    )


def _claims(claims_path, image_path, image, claims_data, provider, model) -> dict:
    if claims_data is not None:
        from blueprint.vision import claims_from_mapping

        return claims_from_mapping(claims_data)
    if claims_path is not None:
        return load_claims(claims_path)
    if image is not None:
        data, mime = image
        return read_image(data, mime, model, provider)
    if image_path is None or not image_path.is_file():
        raise DiagramError(f"Diagram not found: {image_path}")
    from blueprint.vision import _mime

    return read_image(image_path.read_bytes(), _mime(image_path), model, provider)
