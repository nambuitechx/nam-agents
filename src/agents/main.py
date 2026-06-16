"""Interactive CLI for the general Q&A agent."""

from general_agent import agent
from settings import get_settings


def main() -> None:
    settings = get_settings()

    print("General Q&A Agent (Strands + Amazon Bedrock)")
    print(f"Model: {settings.model_id}")
    print(f"Region: {settings.region}")
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

        result = agent(question)
        print(f"\nAgent: {result.message}\n")


if __name__ == "__main__":
    main()
