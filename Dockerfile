# Built in CI (GitHub Actions) and pushed to a container registry, then deployed to
# Kakao Cloud (PlayMCP in KC) via "이미지 등록". Building in CI avoids the managed
# Git-source builder's tight (~40s) build-time budget. The server speaks MCP over
# Streamable HTTP (stateless) at /mcp/ — see src/taxmatjip_mcp/server.py.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0 \
    TAXMATJIP_DATA_DIR=/app/data

WORKDIR /app

# README.md is required by pyproject's `readme = ...` at wheel-build time.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# The Kakao Cloud runtime blocks outbound network, so bake the place index into the
# image at build time (CI has egress). The server reads it from TAXMATJIP_DATA_DIR.
RUN mkdir -p /app/data \
    && python -c "import urllib.request; urllib.request.urlretrieve('https://taxfood.kr/data/search-index.json', '/app/data/search-index.json')" \
    && python -c "import json; d=json.load(open('/app/data/search-index.json')); assert len(d) > 1000, len(d); print('bundled search-index:', len(d), 'places')"

EXPOSE 8080

# Honors $PORT / $HOST if the platform injects them.
CMD ["python", "-m", "taxmatjip_mcp"]
