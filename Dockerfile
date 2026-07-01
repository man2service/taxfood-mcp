# Built in CI (GitHub Actions) and pushed to a container registry, then deployed to
# Kakao Cloud (PlayMCP in KC) via "이미지 등록". Building in CI avoids the managed
# Git-source builder's tight (~40s) build-time budget. The server speaks MCP over
# Streamable HTTP (stateless) at /mcp/ — see src/taxmatjip_mcp/server.py.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 8080

# Honors $PORT / $HOST if the platform injects them.
CMD ["python", "-m", "taxmatjip_mcp"]
