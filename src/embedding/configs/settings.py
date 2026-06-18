"""Application settings for the embedding service."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Bedrock embedding and OpenSearch configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    region: str = Field(default="ap-southeast-1", validation_alias="aws_region")
    model_id: str = Field(default="cohere.embed-multilingual-v3")
    embedding_dim: int = Field(default=1024)
    max_batch_size: int = Field(default=96)
    max_chars_per_text: int = Field(default=2048)

    opensearch_url: str = Field(default="http://localhost:9200")
    index_name: str = Field(default="nam-documents")

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8090)


@lru_cache
def get_settings() -> Settings:
    return Settings()
