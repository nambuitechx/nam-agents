"""OpenSearch storage for document chunks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from opensearchpy import AsyncOpenSearch
from opensearchpy.helpers import async_bulk

if TYPE_CHECKING:
    from configs.settings import Settings


class OpenSearchStore:
    """Async OpenSearch client for chunk indexing and retrieval."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        url = settings.opensearch_url
        self._client = AsyncOpenSearch(
            hosts=[url],
            use_ssl=url.startswith("https://"),
            verify_certs=False,
            ssl_show_warn=False,
        )

    async def close(self) -> None:
        await self._client.close()

    async def ensure_index(self) -> None:
        index = self._settings.index_name
        if await self._client.indices.exists(index=index):
            return

        body = {
            "settings": {"index": {"knn": True}},
            "mappings": {
                "properties": {
                    "document_id": {"type": "keyword"},
                    "filename": {"type": "keyword"},
                    "chunk_index": {"type": "integer"},
                    "content": {"type": "text"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": self._settings.embedding_dim,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "lucene",
                        },
                    },
                    "created_at": {"type": "date"},
                }
            },
        }
        await self._client.indices.create(index=index, body=body)

    async def document_exists(self, document_id: str) -> bool:
        if not await self._client.indices.exists(index=self._settings.index_name):
            return False
        body = {
            "size": 0,
            "query": {"term": {"document_id": document_id}},
        }
        response = await self._client.search(index=self._settings.index_name, body=body)
        total = response["hits"]["total"]
        count = total["value"] if isinstance(total, dict) else int(total)
        return count > 0

    async def index_chunks(
        self,
        *,
        document_id: str,
        filename: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")

        created_at = datetime.now(UTC).isoformat()
        actions = []
        for index, (content, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            actions.append(
                {
                    "_index": self._settings.index_name,
                    "_id": f"{document_id}:{index}",
                    "_source": {
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_index": index,
                        "content": content,
                        "embedding": embedding,
                        "created_at": created_at,
                    },
                }
            )

        if not actions:
            return

        success, errors = await async_bulk(self._client, actions, refresh=True)
        if errors:
            raise RuntimeError(f"OpenSearch bulk index failed: {errors}")
        if success != len(actions):
            raise RuntimeError(f"Indexed {success}/{len(actions)} chunks")

    async def remove_document(self, document_id: str) -> int:
        if not await self._client.indices.exists(index=self._settings.index_name):
            return 0
        body = {"query": {"term": {"document_id": document_id}}}
        response = await self._client.delete_by_query(
            index=self._settings.index_name,
            body=body,
            refresh=True,
        )
        return int(response.get("deleted", 0))

    async def list_chunks(self, document_id: str) -> list[dict[str, Any]]:
        if not await self._client.indices.exists(index=self._settings.index_name):
            return []
        body = {
            "size": 10000,
            "query": {"term": {"document_id": document_id}},
            "sort": [{"chunk_index": {"order": "asc"}}],
            "_source": ["document_id", "filename", "chunk_index", "content", "created_at"],
        }
        response = await self._client.search(index=self._settings.index_name, body=body)
        return [hit["_source"] for hit in response["hits"]["hits"]]

    async def list_documents(self) -> list[dict[str, Any]]:
        if not await self._client.indices.exists(index=self._settings.index_name):
            return []
        body = {
            "size": 0,
            "aggs": {
                "documents": {
                    "terms": {"field": "document_id", "size": 10000},
                    "aggs": {
                        "meta": {
                            "top_hits": {
                                "size": 1,
                                "_source": ["filename", "created_at"],
                                "sort": [{"chunk_index": {"order": "asc"}}],
                            }
                        },
                        "chunk_count": {"value_count": {"field": "chunk_index"}},
                    },
                }
            },
        }
        response = await self._client.search(index=self._settings.index_name, body=body)
        documents: list[dict[str, Any]] = []

        for bucket in response["aggregations"]["documents"]["buckets"]:
            source = bucket["meta"]["hits"]["hits"][0]["_source"]
            documents.append(
                {
                    "document_id": bucket["key"],
                    "filename": source.get("filename"),
                    "chunk_count": int(bucket["chunk_count"]["value"]),
                    "created_at": source.get("created_at"),
                }
            )

        documents.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return documents

    async def ping(self) -> bool:
        try:
            health = await self._client.cluster.health()
            return health.get("status") in {"green", "yellow"}
        except Exception:
            return False
