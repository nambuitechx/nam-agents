"""Amazon Bedrock AgentCore Runtime entry point.

Exposes /invocations and /ping via the bedrock-agentcore SDK (no AgentCore CLI).
Run locally:  uv run python -m runtimes.simple
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from core.agent import create_agent

app = BedrockAgentCoreApp()
agent = create_agent()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Handle AgentCore invocation requests."""
    user_message = payload.get("prompt", "")
    if not user_message:
        return {"error": "Missing 'prompt' in payload. Send {\"prompt\": \"your question\"}."}

    result = agent(user_message)
    return {"result": result.message}


if __name__ == "__main__":
    app.run()
