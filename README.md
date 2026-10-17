# Blueprint

Blueprint diffs an architecture diagram against the dependency graph of the code. The diagram is a claim. [Graphify](https://github.com/safishamsi/graphify) is the evidence. Gemma reads the picture.

The sample app draws Billing talking to Auth. The code never imports Auth. Admin imports Billing, and the diagram never drew that arrow. Payments and Notifications call each other. Admin is the module the diagram left off the page.

## Demo

Offline, no API key:

```text
blueprint check sample/app --claims sample/claims.json
```

Exit code 1 means the diagram and the code disagree. That is the CI check.

With Gemma 4 on the Gemini API:

```text
copy .env.example .env
blueprint check sample/app --image sample/diagram.png --provider gemini
```

`GEMINI_MODEL` defaults to `gemma-4-26b-a4b-it`.

## API

```text
uvicorn blueprint.api:app --reload
```

`POST /v1/checks` takes a multipart form: `claims` (JSON) or `image`, plus `provider` (`auto`, `gemini`, `ollama`, `vllm`, `sglang`). `GET /health`, `GET /info`, `GET /v1/sample/claims`, and `GET /v1/sample/diagram` are there for the demo page.

```text
cd web
npm install
npm run dev
```

The page is at `http://localhost:3000`. It calls `http://127.0.0.1:8000`.

## Local models

Ollama, vLLM, and SGLang all speak `/v1/chat/completions`. One client covers all three. Set `VISION_BASE_URL`:

- Ollama: `http://127.0.0.1:11434/v1` (the default)
- vLLM: `http://127.0.0.1:8000/v1`
- SGLang: `http://127.0.0.1:30000/v1`

```text
ollama pull gemma4:e4b
blueprint check sample/app --image sample/diagram.png --provider ollama
```

`docker compose up` starts the API and an Ollama container. Pull the model inside that container before using `--provider ollama`.

## Graph

The committed graph was produced with:

```text
graphify extract sample/app --code-only --no-cluster
```

Re-run that after you change the sample. The loader keeps import and call edges and rolls each file up to its top-level package.

## Tests

```text
pip install -e ".[dev]"
pytest
```

The default suite does not call Gemini or a local model.

## AI disclosure

Gemma 4 reads diagrams, through the Gemini API or through an OpenAI-compatible local server. Graphify builds the code graph. A coding assistant drafted the project code during Hacktoberfest Hack Day Vadodara 2026.

Apache License 2.0. See LICENSE.
