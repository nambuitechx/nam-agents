"""Interactive CLI for the knowledge-base agent."""

from core.kb_agent import kb_agent
from configs.settings import get_settings


def main() -> None:
    settings = get_settings()

    print("Knowledge Base Agent (Strands + Bedrock + OpenSearch)")
    print(f"Model: {settings.model_id}")
    print(f"Region: {settings.region}")
    print(f"OpenSearch: {settings.opensearch_url} / {settings.opensearch_index_name}")
    print("Ask anything. Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        result = kb_agent(question)
        print(f"\nAgent: {result.message}\n")


if __name__ == "__main__":
    main()
