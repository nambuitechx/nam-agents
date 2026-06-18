#!/bin/sh
set -eu
exec uv run python -m "${RUNTIME_MODULE}"
