"""Knowledge-base Q&A agent with OpenSearch retrieval."""

from strands import Agent, tool

from configs.settings import Settings, get_settings
from core.agent import create_bedrock_model
from core.knowledge_base import KnowledgeBase

SYSTEM_PROMPT = """You are a helpful assistant with access to a document knowledge base.

Guidelines:
- When a question may depend on indexed documents, call search_knowledge_base before answering.
- Ground answers in retrieved passages when they are relevant; cite the source filename.
- If search returns nothing useful, say so and answer from general knowledge only when appropriate.
- If you are unsure, say so rather than guessing.
- Be concise and well-structured unless the user asks for more detail.
"""

_knowledge_base = KnowledgeBase()


@tool
def search_knowledge_base(query: str, top_k: int = 5) -> dict:
    """Search indexed documents in OpenSearch for passages relevant to a question.

    Args:
        query: Natural-language search query describing what information you need.
        top_k: Maximum number of text chunks to return (default: 5).

    Returns:
        Matching document excerpts with source metadata.
    """
    try:
        hits = _knowledge_base.search(query, top_k=top_k)
        formatted = KnowledgeBase.format_hits(hits)
        return {
            "status": "success",
            "content": [{"text": formatted}],
        }
    except Exception as exc:
        return {
            "status": "error",
            "content": [{"text": f"Knowledge base search failed: {exc}"}],
        }


def create_kb_agent(settings: Settings | None = None) -> Agent:
    """Create a Strands agent that can search OpenSearch for document context."""
    global _knowledge_base
    settings = settings or get_settings()
    _knowledge_base = KnowledgeBase(settings)

    return Agent(
        model=create_bedrock_model(settings),
        system_prompt=SYSTEM_PROMPT,
        tools=[search_knowledge_base],
        callback_handler=None,
    )


kb_agent = create_kb_agent()
