# Kakao Cloud (PlayMCP in KC) builds this image from the Git repo and exposes the
# container's HTTP port as the MCP Endpoint URL. The server speaks MCP over
# Streamable HTTP (stateless) at /mcp/ — see src/taxmatjip_mcp/server.py.
#
# The managed builder has a tight (~40s) build-time budget, so we install with `uv`
# (parallel, much faster than pip) to fit inside it. No `# syntax=` directive on
# purpose — the builder may not fetch a BuildKit frontend.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0 \
    UV_NO_CACHE=1 \
    UV_HTTP_TIMEOUT=120

WORKDIR /app

# Fast dependency install: fetch uv, then resolve+install the app in parallel.
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
COPY src ./src
RUN uv pip install --system .

EXPOSE 8080

# Honors $PORT / $HOST if the platform injects them.
CMD ["python", "-m", "taxmatjip_mcp"]
