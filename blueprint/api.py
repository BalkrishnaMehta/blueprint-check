"""HTTP API for the architecture check."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from blueprint import __version__
from blueprint.config import get_settings
from blueprint.schemas import CheckOut, InfoOut, to_check_out
from blueprint.service import execute
from blueprint.vision import DiagramError, _mime

app = FastAPI(title="Blueprint", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


_EXAMPLES = (
    ("sample", "Billing", "The diagram draws billing to auth. The code does not.", "sample/app", "sample/claims.json"),
    ("orders", "Orders", "The diagram matches the imports.", "tracks/clean", "tracks/clean/claims.json"),
    ("warehouse", "Warehouse", "The diagram draws shipping. The code cycles warehouse and inventory.", "tracks/drift", "tracks/drift/claims.json"),
)


def _root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "sample").is_dir():
            return parent
    return Path.cwd()


def _resolve(root: Path, value: str | None, default: Path | None = None) -> Path | None:
    if not value:
        return default
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path


def serve() -> None:
    import uvicorn

    uvicorn.run("blueprint.api:app", host="127.0.0.1", port=8000)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/info", response_model=InfoOut)
def info() -> InfoOut:
    settings = get_settings()
    root = _root()
    graph = root / "sample" / "app" / "graphify-out" / "graph.json"
    key = settings.gemini_api_key.strip()
    masked = "not set" if not key else "set" if len(key) <= 4 else f"set (...{key[-4:]})"
    return InfoOut(
        version=__version__,
        gemini_model=settings.gemini_model,
        gemini_api_key=masked,
        vision_base_url=settings.vision_base_url,
        vision_model=settings.vision_model,
        graph="present" if graph.is_file() else "missing",
    )


@app.get("/v1/sample/claims")
def sample_claims() -> dict:
    return json.loads((_root() / "sample" / "claims.json").read_text(encoding="utf-8"))


@app.get("/v1/examples")
def examples() -> list[dict]:
    root = _root()
    listed = []
    for example_id, title, detail, repo, claims in _EXAMPLES:
        listed.append(
            {
                "id": example_id,
                "title": title,
                "detail": detail,
                "repo": repo,
                "claims": json.loads((root / claims).read_text(encoding="utf-8")),
            }
        )
    return listed


@app.get("/v1/sample/diagram")
def sample_diagram() -> FileResponse:
    path = _root() / "sample" / "diagram.png"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Sample diagram has not been rendered")
    return FileResponse(path, media_type="image/png")


@app.post("/v1/checks", response_model=CheckOut)
async def create_check(
    claims: str | None = Form(None),
    provider: str = Form("auto"),
    model: str | None = Form(None),
    repo: str | None = Form(None),
    graph: str | None = Form(None),
    image: UploadFile | None = File(None),
) -> CheckOut:
    root = _root()
    repo_path = _resolve(root, repo, root / "sample" / "app")
    graph_path = _resolve(root, graph)
    claims_data = None
    image_payload = None
    if claims:
        try:
            claims_data = json.loads(claims)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"claims is not JSON: {exc}") from exc
    elif image is not None:
        image_payload = (await image.read(), image.content_type or _mime(Path(image.filename or "diagram.png")))
    else:
        raise HTTPException(status_code=400, detail="Send claims or an image")
    try:
        findings = execute(
            repo_path,
            image=image_payload,
            graph_path=graph_path,
            provider=provider,
            model=model or None,
            claims_data=claims_data,
        )
    except (DiagramError, FileNotFoundError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return to_check_out(findings)
