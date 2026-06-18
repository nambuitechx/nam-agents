# Embedding service and server

Async document embedding with **Amazon Bedrock Cohere** (`cohere.embed-multilingual-v3`) and **OpenSearch** k-NN storage.

**Repo-level docs:** [Local development quickstart](../../README.md#local-development-quickstart), [Makefile cheat sheet](../../README.md#make-vs-raw-commands-cheat-sheet), [local OpenSearch](../../README.md#local-services-postgresql--opensearch).

## Quick start (local)

Full step-by-step (OpenSearch → embed → test with KB agent): **[README — Local development quickstart](../../README.md#local-development-quickstart)**.

Minimal commands from repo root:

```bash
make up && make embed-env embed-sync
make embed FILE=/path/to/doc.md
make embed-list
```

## Architecture

```
Upload (CLI / FastAPI)
        │
        ▼
core/loaders  →  core/chunker  →  core/embedder (Bedrock Cohere)  →  core/opensearch_store
```

Each document is split into chunks (≤ 2048 chars), embedded (1024-dim vectors, batch ≤ 96), and stored in OpenSearch with metadata.

## Layout

| Path | Purpose |
|------|---------|
| `core/service.py` | Orchestration — embed, remove, list |
| `core/loaders.py` | Extract text from `.txt`, `.md`, `.pdf`, `.docx`, `.doc` |
| `core/chunker.py` | Split text for Cohere limits |
| `core/embedder.py` | Async Bedrock Cohere client |
| `core/opensearch_store.py` | Async OpenSearch index CRUD |
| `configs/settings.py` | Settings from env / `.env` |
| `cmd/cli.py` | CLI: `embed`, `remove`, `list` |
| `api/server.py` | FastAPI on `:8090` |

## Setup

See [README — Before you start](../../README.md#before-you-start) for AWS and tool prerequisites.

From repo root:

```bash
make embed-env && make embed-sync
make up   # local OpenSearch on :9200
```

Or manually from `src/embedding/`: `cp .env.example .env` and `uv sync`.

Requires AWS credentials with Bedrock access to `cohere.embed-multilingual-v3` in `ap-southeast-1`.

## Local usage

Canonical walkthrough: [README — Path A (embed + KB agent)](../../README.md#path-a--index-documents-then-test-the-kb-agent).

**CLI vs API:** `make embed` / `uv run … cmd.cli embed` talk to OpenSearch directly — **no API server required**. Use `make embed-server` only for HTTP uploads (`make embed-upload` or `POST /documents`).

Makefile wrappers (from repo root — run `make help` for all targets):

| Target | Purpose |
|--------|---------|
| `make embed-env` | Create `src/embedding/.env` from example |
| `make embed-sync` | Install dependencies (`uv sync`) |
| `make embed-server` | FastAPI on `:8090` |
| `make embed-health` | Health check (`GET /health`) |
| `make embed-list` | List all indexed documents (CLI) |
| `make embed FILE=…` | Embed a file (CLI); optional `DOCUMENT_ID=`, `REPLACE=true` |
| `make embed-remove DOCUMENT_ID=…` | Remove a document (CLI) |
| `make embed-upload FILE=…` | Upload via API (server must be running) |
| `make embed-cli ARGS="…"` | Pass-through to CLI subcommands |

Direct `uv` equivalents below.

## Document IDs

On **embed**, `document_id` is optional:

| Provided? | Behavior |
|-----------|----------|
| No | Server generates a UUID v4; returned in the response — **save it** for remove/list |
| Yes | Must be a valid UUID; enables idempotent uploads and `--replace` / `replace=true` overwrites |

Remove and list always require an explicit `document_id`.

## CLI

Makefile: `make embed FILE=…`, `make embed-list`, `make embed-remove DOCUMENT_ID=…`, or `make embed-cli ARGS="list --document-id …"`.

From `src/embedding/`:

```bash
# Embed — server generates document_id
uv run python -m cmd.cli embed --file ./sample.md

# Embed — client-provided UUID (idempotent / replaceable)
uv run python -m cmd.cli embed --file ./sample.md --document-id 550e8400-e29b-41d4-a716-446655440000
uv run python -m cmd.cli embed --file ./sample.md --document-id 550e8400-e29b-41d4-a716-446655440000 --replace

# List all indexed documents
uv run python -m cmd.cli list --all

# List chunks for a document
uv run python -m cmd.cli list --document-id 550e8400-e29b-41d4-a716-446655440000

# Remove a document
uv run python -m cmd.cli remove --document-id 550e8400-e29b-41d4-a716-446655440000
```

Supported formats: `.txt`, `.md`, `.pdf`, `.docx`, `.doc` (legacy `.doc` requires `antiword`).

## FastAPI server

```bash
make embed-server
# → http://localhost:8090
```

Or from `src/embedding/`: `uv run python -m api.server`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | OpenSearch health |
| `POST` | `/documents` | multipart: `file`, optional `document_id`, optional `replace` |
| `DELETE` | `/documents/{document_id}` | Remove all chunks |
| `GET` | `/documents` | List indexed documents |
| `GET` | `/documents/{document_id}/chunks` | List chunks |

Example upload (with `make embed-server` running):

```bash
make embed-upload FILE=sample.md
make embed-upload FILE=sample.md DOCUMENT_ID=550e8400-e29b-41d4-a716-446655440000
```

Or via curl:

```bash
curl -X POST http://localhost:8090/documents -F "file=@sample.md"
curl -X POST http://localhost:8090/documents \
  -F "document_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "file=@sample.md"
```

Embed response:

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "sample.md",
  "chunk_count": 3
}
```

## Configuration

See [`.env.example`](.env.example).

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `ap-southeast-1` | Bedrock region |
| `MODEL_ID` | `cohere.embed-multilingual-v3` | Embedding model |
| `EMBEDDING_DIM` | `1024` | Vector dimension (must match model) |
| `MAX_BATCH_SIZE` | `96` | Texts per Bedrock invocation (Cohere cap) |
| `MAX_CHARS_PER_TEXT` | `2048` | Max chars per chunk (~512 tokens) |
| `OPENSEARCH_URL` | `http://localhost:9200` | OpenSearch endpoint |
| `INDEX_NAME` | `nam-documents` | k-NN index name |
| `API_HOST` | `0.0.0.0` | FastAPI bind host |
| `API_PORT` | `8090` | FastAPI port |

## Related docs

- [Repo README](../../README.md) — Makefile, local services
- [Agents package](../agents/README.md) — main Q&A agent
