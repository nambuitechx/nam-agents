"""OpenSearch knowledge-base retrieval for the KB agent."""

from __future__ import annotations

import json
from typing import Any

import boto3
from opensearchpy import OpenSearch

from configs.settings import Settings, get_settings


class KnowledgeBase:
    """Embed queries with Bedrock Cohere and search the OpenSearch k-NN index."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        url = self._settings.opensearch_url
        self._client = OpenSearch(
            hosts=[url],
            use_ssl=url.startswith("https://"),
            verify_certs=False,
            ssl_show_warn=False,
        )
        self._bedrock = boto3.client("bedrock-runtime", region_name=self._settings.region)

    def embed_query(self, query: str) -> list[float]:
        body = json.dumps({"texts": [query], "input_type": "search_query"})
        response = self._bedrock.invoke_model(
            modelId=self._settings.embedding_model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        data = json.loads(response["body"].read())
        embeddings = data.get("embeddings")
        if not embeddings:
            raise RuntimeError("Bedrock response missing 'embeddings'")
        vector = embeddings[0]
        if len(vector) != self._settings.embedding_dim:
            raise RuntimeError(
                f"Unexpected embedding dimension {len(vector)} "
                f"(expected {self._settings.embedding_dim})"
            )
        return vector

    def search(self, query: str, *, top_k: int | None = None) -> list[dict[str, Any]]:
        index = self._settings.opensearch_index_name
        if not self._client.indices.exists(index=index):
            return []

        k = top_k if top_k is not None else self._settings.kb_search_top_k
        vector = self.embed_query(query)
        body = {
            "size": k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": vector,
                        "k": k,
                    }
                }
            },
            "_source": ["document_id", "filename", "chunk_index", "content"],
        }
        response = self._client.search(index=index, body=body)
        return response["hits"]["hits"]

    @staticmethod
    def format_hits(hits: list[dict[str, Any]]) -> str:
        if not hits:
            return "No relevant documents found in the knowledge base."

        parts: list[str] = []
        for index, hit in enumerate(hits, start=1):
            source = hit["_source"]
            score = hit.get("_score", 0.0)
            parts.append(
                f"[{index}] {source.get('filename', 'unknown')} "
                f"(document_id={source.get('document_id')}, "
                f"chunk={source.get('chunk_index')}, score={score:.3f})\n"
                f"{source.get('content', '').strip()}"
            )
        return "\n\n".join(parts)
