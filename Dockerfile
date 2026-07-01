# Kakao Cloud (PlayMCP in KC) builds this image from the Git repo and exposes the
# container's HTTP port as the MCP Endpoint URL. The server speaks MCP over
# Streamable HTTP (stateless) at /mcp/ — see src/taxmatjip_mcp/server.py.
# NOTE: no `# syntax=` directive on purpose — the managed builder may not fetch a
# BuildKit frontend, and we use only plain Dockerfile features.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0

WORKDIR /app

# Install deps first (better layer caching), then the package.
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 8080

# Honors $PORT / $HOST if the platform injects them.
CMD ["python", "-m", "taxmatjip_mcp"]
