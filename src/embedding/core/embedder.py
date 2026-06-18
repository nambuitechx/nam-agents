"""Bedrock Cohere embedding client."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import aioboto3

if TYPE_CHECKING:
    from configs.settings import Settings


class BedrockEmbedder:
    """Async Bedrock client for Cohere embed-multilingual-v3."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = aioboto3.Session()

    async def embed_texts(
        self,
        texts: list[str],
        *,
        input_type: str = "search_document",
    ) -> list[list[float]]:
        if not texts:
            return []

        body = json.dumps({"texts": texts, "input_type": input_type})
        async with self._session.client(
            "bedrock-runtime",
            region_name=self._settings.region,
        ) as client:
            response = await client.invoke_model(
                modelId=self._settings.model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            payload = await response["body"].read()

        data = json.loads(payload)
        embeddings = data.get("embeddings")
        if not embeddings:
            raise RuntimeError("Bedrock response missing 'embeddings'")
        if len(embeddings) != len(texts):
            raise RuntimeError(
                f"Expected {len(texts)} embeddings, got {len(embeddings)}"
            )
        return embeddings

    async def embed_batches(
        self,
        texts: list[str],
        *,
        input_type: str = "search_document",
    ) -> list[list[float]]:
        batch_size = self._settings.max_batch_size
        all_embeddings: list[list[float]] = []

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            batch_embeddings = await self.embed_texts(batch, input_type=input_type)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings
