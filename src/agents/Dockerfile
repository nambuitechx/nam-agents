# AgentCore Runtime requires linux/arm64, port 8080, and a non-root user.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

COPY general_agent.py settings.py runtime.py ./

RUN useradd -m -u 1000 agent && chown -R agent:agent /app
USER agent

EXPOSE 8080

CMD ["uv", "run", "python", "runtime.py"]
