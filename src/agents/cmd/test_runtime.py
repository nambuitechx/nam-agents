"""Interactive CLI for a deployed Bedrock AgentCore Runtime (aioboto3).

Usage:
    uv run python -m cmd.test_runtime arn:aws:bedrock-agentcore:...
    AGENT_RUNTIME_ARN=arn:... uv run python -m cmd.test_runtime
    uv run python -m cmd.test_runtime --region ap-southeast-1 arn:...
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import uuid

import aioboto3

from configs.settings import get_settings

_ARN_REGION_RE = re.compile(r"^arn:aws:bedrock-agentcore:([^:]+):")


def parse_region_from_arn(arn: str) -> str | None:
    match = _ARN_REGION_RE.match(arn)
    return match.group(1) if match else None


def new_session_id() -> str:
    # AgentCore requires runtimeSessionId length >= 33.
    return uuid.uuid4().hex + uuid.uuid4().hex[:1]


def format_response(data: object) -> str:
    if not isinstance(data, dict):
        return str(data)

    if "result" in data:
        return str(data["result"])
    if "error" in data:
        return f"Error: {data['error']}"

    output = data.get("output")
    if isinstance(output, dict):
        if "message" in output:
            return str(output["message"])
        return json.dumps(output, indent=2)
    if output is not None:
        return str(output)

    return json.dumps(data, indent=2)


async def read_response_body(body: object, content_type: str) -> str:
    if "text/event-stream" in content_type and hasattr(body, "iter_lines"):
        chunks: list[str] = []
        async for line in body.iter_lines():  # type: ignore[attr-defined]
            if not line:
                continue
            text = line.decode("utf-8") if isinstance(line, bytes) else str(line)
            if text.startswith("data: "):
                chunks.append(text[6:])
        return "\n".join(chunks) if chunks else ""

    raw = await body.read()  # type: ignore[attr-defined]
    if isinstance(raw, bytes):
        text = raw.decode("utf-8")
    else:
        text = str(raw)

    if not text.strip():
        return ""

    try:
        return format_response(json.loads(text))
    except json.JSONDecodeError:
        return text


async def invoke_agent(
    client: object,
    *,
    runtime_arn: str,
    prompt: str,
    session_id: str,
) -> str:
    payload = json.dumps({"prompt": prompt}).encode()
    response = await client.invoke_agent_runtime(  # type: ignore[attr-defined]
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=session_id,
        qualifier="DEFAULT",
        payload=payload,
    )

    return await read_response_body(
        response["response"],
        response.get("contentType", ""),
    )


async def run_chat(runtime_arn: str, region: str) -> None:
    session_id = new_session_id()

    print("AgentCore Runtime Client (aioboto3)")
    print(f"Runtime ARN: {runtime_arn}")
    print(f"Region: {region}")
    print(f"Session ID: {session_id}")
    print("Ask anything. Type 'exit' or 'quit' to stop.\n")

    session = aioboto3.Session()
    async with session.client("bedrock-agentcore", region_name=region) as client:
        while True:
            try:
                question = (await asyncio.to_thread(input, "You: ")).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not question:
                continue
            if question.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break

            try:
                answer = await invoke_agent(
                    client,
                    runtime_arn=runtime_arn,
                    prompt=question,
                    session_id=session_id,
                )
                print(f"\nAgent: {answer}\n")
            except Exception as exc:
                print(f"\nError: {exc}\n", file=sys.stderr)


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Interactive CLI for a deployed Bedrock AgentCore Runtime.",
    )
    parser.add_argument(
        "runtime_arn",
        nargs="?",
        default=None,
        help="AgentCore Runtime ARN (or set AGENT_RUNTIME_ARN)",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="AWS region (default: parsed from ARN or BEDROCK_REGION)",
    )
    args = parser.parse_args()

    runtime_arn = args.runtime_arn or os.environ.get("AGENT_RUNTIME_ARN")
    if not runtime_arn:
        parser.error("runtime ARN is required (positional argument or AGENT_RUNTIME_ARN)")

    region = args.region or parse_region_from_arn(runtime_arn) or settings.region
    asyncio.run(run_chat(runtime_arn, region))


if __name__ == "__main__":
    main()
