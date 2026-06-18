"""Application settings loaded from environment variables and .env."""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Bedrock and agent configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    model_id: str = Field(
        default="apac.anthropic.claude-sonnet-4-20250514-v1:0",
        validation_alias=AliasChoices("bedrock_model_id", "strands_model_id"),
    )
    region: str = Field(
        default="ap-southeast-1",
        validation_alias=AliasChoices("bedrock_region", "aws_region"),
    )
    temperature: float | None = Field(default=None, validation_alias="bedrock_temperature")
    max_tokens: int | None = Field(default=None, validation_alias="bedrock_max_tokens")

    embedding_model_id: str = Field(
        default="cohere.embed-multilingual-v3",
        validation_alias=AliasChoices("embedding_model_id", "bedrock_embedding_model_id"),
    )
    embedding_dim: int = Field(default=1024)
    opensearch_url: str = Field(default="http://localhost:9200")
    opensearch_index_name: str = Field(
        default="nam-documents",
        validation_alias=AliasChoices("opensearch_index_name", "index_name"),
    )
    kb_search_top_k: int = Field(default=5)


@lru_cache
def get_settings() -> Settings:
    return Settings()
