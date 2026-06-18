# Embedding service and server

Async document embedding with **Amazon Bedrock Cohere** (`cohere.embed-multilingual-v3`) and **OpenSearch** k-NN storage.

**Repo-level docs:** [local OpenSearch](../../README.md#local-services-postgresql--opensearch), [project structure](../../README.md#project-structure).

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

```bash
cd src/embedding
cp .env.example .env
uv sync
```

Start local OpenSearch from the repo root:

```bash
make up
```

Requires AWS credentials with Bedrock access to `cohere.embed-multilingual-v3` in `ap-southeast-1`.

## Document IDs

On **embed**, `document_id` is optional:

| Provided? | Behavior |
|-----------|----------|
| No | Server generates a UUID v4; returned in the response — **save it** for remove/list |
| Yes | Must be a valid UUID; enables idempotent uploads and `--replace` / `replace=true` overwrites |

Remove and list always require an explicit `document_id`.

## CLI

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
uv run python -m api.server
# → http://localhost:8090
```

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | OpenSearch health |
| `POST` | `/documents` | multipart: `file`, optional `document_id`, optional `replace` |
| `DELETE` | `/documents/{document_id}` | Remove all chunks |
| `GET` | `/documents` | List indexed documents |
| `GET` | `/documents/{document_id}/chunks` | List chunks |

Example upload:

```bash
# Server-generated document_id
curl -X POST http://localhost:8090/documents -F "file=@sample.md"

# Client-provided document_id
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
