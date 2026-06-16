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


@lru_cache
def get_settings() -> Settings:
    return Settings()
