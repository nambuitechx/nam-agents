"""Orchestration service for document embedding workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from configs.settings import Settings, get_settings
from core.chunker import chunk_text
from core.embedder import BedrockEmbedder
import aiofiles

from core.loaders import load_text
from core.opensearch_store import OpenSearchStore


@dataclass(frozen=True)
class EmbedResult:
    document_id: str
    filename: str
    chunk_count: int


class DocumentAlreadyExistsError(ValueError):
    """Raised when a client-provided document_id is already indexed."""


class DocumentNotFoundError(ValueError):
    """Raised when a document_id has no indexed chunks."""


class EmbeddingService:
    """Async core service: load → chunk → embed → store in OpenSearch."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._embedder = BedrockEmbedder(self._settings)
        self._store = OpenSearchStore(self._settings)

    async def close(self) -> None:
        await self._store.close()

    @staticmethod
    def resolve_document_id(document_id: str | None) -> str:
        """Validate a client UUID or generate a new one when omitted."""
        if document_id is None or not document_id.strip():
            return str(uuid4())
        return str(UUID(document_id.strip()))

    async def embed_bytes(
        self,
        *,
        document_id: str | None,
        filename: str,
        content: bytes,
        replace: bool = False,
    ) -> EmbedResult:
        document_id = self.resolve_document_id(document_id)
        await self._store.ensure_index()

        exists = await self._store.document_exists(document_id)
        if exists and not replace:
            raise DocumentAlreadyExistsError(
                f"Document '{document_id}' already exists. "
                "Pass replace=True to overwrite."
            )
        if exists and replace:
            await self._store.remove_document(document_id)

        text = await load_text(content, filename)
        chunks = chunk_text(text, max_chars=self._settings.max_chars_per_text)
        if not chunks:
            raise ValueError(f"No embeddable text found in '{filename}'")

        embeddings = await self._embedder.embed_batches(chunks)
        if any(len(vector) != self._settings.embedding_dim for vector in embeddings):
            raise RuntimeError(
                f"Unexpected embedding dimension (expected {self._settings.embedding_dim})"
            )

        await self._store.index_chunks(
            document_id=document_id,
            filename=filename,
            chunks=chunks,
            embeddings=embeddings,
        )
        return EmbedResult(document_id=document_id, filename=filename, chunk_count=len(chunks))

    async def embed_file(
        self,
        *,
        document_id: str | None,
        path: Path,
        replace: bool = False,
    ) -> EmbedResult:
        async with aiofiles.open(path, "rb") as handle:
            content = await handle.read()
        return await self.embed_bytes(
            document_id=document_id,
            filename=path.name,
            content=content,
            replace=replace,
        )

    async def remove_document(self, document_id: str) -> int:
        document_id = self.resolve_document_id(document_id)
        deleted = await self._store.remove_document(document_id)
        if deleted == 0:
            raise DocumentNotFoundError(f"Document '{document_id}' not found")
        return deleted

    async def list_chunks(self, document_id: str) -> list[dict[str, Any]]:
        document_id = self.resolve_document_id(document_id)
        chunks = await self._store.list_chunks(document_id)
        if not chunks:
            raise DocumentNotFoundError(f"Document '{document_id}' not found")
        return chunks

    async def list_documents(self) -> list[dict[str, Any]]:
        return await self._store.list_documents()

    async def health(self) -> dict[str, bool]:
        return {"opensearch": await self._store.ping()}
