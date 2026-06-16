"""General-purpose Q&A agent powered by the Strands Agents SDK."""

from strands import Agent
from strands.models import BedrockModel

from configs.settings import Settings, get_settings

SYSTEM_PROMPT = """You are a helpful assistant that answers general questions clearly and accurately.

Guidelines:
- Give concise, well-structured answers unless the user asks for more detail.
- If you are unsure, say so rather than guessing.
- Be friendly and professional.
"""


def create_bedrock_model(settings: Settings | None = None) -> BedrockModel:
    """Create a Bedrock model instance from application settings."""
    settings = settings or get_settings()

    kwargs: dict = {
        "model_id": settings.model_id,
        "region_name": settings.region,
    }

    if settings.temperature is not None:
        kwargs["temperature"] = settings.temperature

    if settings.max_tokens is not None:
        kwargs["max_tokens"] = settings.max_tokens

    return BedrockModel(**kwargs)


def create_agent(settings: Settings | None = None) -> Agent:
    """Create a Strands agent configured for general Q&A on Amazon Bedrock."""
    return Agent(
        model=create_bedrock_model(settings),
        system_prompt=SYSTEM_PROMPT,
        callback_handler=None,
    )


agent = create_agent()
