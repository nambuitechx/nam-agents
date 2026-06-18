# AgentCore Runtime requires linux/arm64, port 8080, and a non-root user.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ARG RUNTIME_MODULE=runtimes.simple
ENV RUNTIME_MODULE=${RUNTIME_MODULE}

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

COPY core/ core/
COPY configs/ configs/
COPY runtimes/ runtimes/
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && useradd -m -u 1000 agent && chown -R agent:agent /app /entrypoint.sh
USER agent

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
