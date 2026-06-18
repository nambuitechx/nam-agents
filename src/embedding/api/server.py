"""FastAPI server for document embedding."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from configs.settings import get_settings
from core.service import (
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    EmbeddingService,
)


class ChunkResponse(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    content: str
    created_at: str | None = None


class DocumentSummary(BaseModel):
    document_id: str
    filename: str | None = None
    chunk_count: int
    created_at: str | None = None


class EmbedResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int


class RemoveResponse(BaseModel):
    document_id: str
    deleted_chunks: int


class HealthResponse(BaseModel):
    status: str
    opensearch: bool


def get_service() -> EmbeddingService:
    return app.state.service


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.service = EmbeddingService()
    yield
    await app.state.service.close()


app = FastAPI(
    title="NAM Embedding Service",
    description="Upload documents, embed with Bedrock Cohere, store in OpenSearch",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health(service: Annotated[EmbeddingService, Depends(get_service)]) -> HealthResponse:
    checks = await service.health()
    ok = checks.get("opensearch", False)
    return HealthResponse(status="ok" if ok else "degraded", opensearch=ok)


@app.post("/documents", response_model=EmbedResponse)
async def embed_document(
    file: UploadFile = File(...),
    document_id: Annotated[
        str | None,
        Form(description="Optional client UUID; server generates one if omitted"),
    ] = None,
    replace: bool = Form(default=False),
    service: Annotated[EmbeddingService, Depends(get_service)],
) -> EmbedResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    content = await file.read()
    try:
        result = await service.embed_bytes(
            document_id=document_id,
            filename=file.filename,
            content=content,
            replace=replace,
        )
    except DocumentAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return EmbedResponse(
        document_id=result.document_id,
        filename=result.filename,
        chunk_count=result.chunk_count,
    )


@app.delete("/documents/{document_id}", response_model=RemoveResponse)
async def remove_document(
    document_id: str,
    service: Annotated[EmbeddingService, Depends(get_service)],
) -> RemoveResponse:
    try:
        deleted = await service.remove_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return RemoveResponse(document_id=document_id, deleted_chunks=deleted)


@app.get("/documents/{document_id}/chunks", response_model=list[ChunkResponse])
async def list_document_chunks(
    document_id: str,
    service: Annotated[EmbeddingService, Depends(get_service)],
) -> list[ChunkResponse]:
    try:
        chunks = await service.list_chunks(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return [ChunkResponse(**chunk) for chunk in chunks]


@app.get("/documents", response_model=list[DocumentSummary])
async def list_documents(
    service: Annotated[EmbeddingService, Depends(get_service)],
) -> list[DocumentSummary]:
    documents = await service.list_documents()
    return [DocumentSummary(**doc) for doc in documents]


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
