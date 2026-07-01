"""Static configuration for the 세금맛집 MCP server.

No secrets live here or anywhere in this repo. The dataset is fetched at runtime
from the PUBLIC taxfood.kr CDN (see DATA_BASE_URL); nothing is bundled, so no
personal data ever lands in this public repository.
"""

from __future__ import annotations

import os

# ── Data source (public CDN; overridable for tests/staging) ──────────────────
SITE_URL: str = os.environ.get("TAXMATJIP_SITE_URL", "https://taxfood.kr")
# search-index.json (all places + coords) lives under /data.
DATA_BASE_URL: str = os.environ.get("TAXMATJIP_DATA_BASE_URL", f"{SITE_URL}/data")
# When set, search-index.json is read from this local directory instead of the CDN.
# The Kakao Cloud runtime blocks outbound network, so the image bakes the index in at
# build time (see Dockerfile) and points here. Empty → fetch from the CDN (local dev).
DATA_DIR: str = os.environ.get("TAXMATJIP_DATA_DIR", "")
# Per-place evidence ledger is served by the web app's maintained detail API
# (GET {API_BASE_URL}/<id>?region=<region>) — the canonical source the site itself
# uses. (The former static detail-<region>.json shards are not always deployed.)
API_BASE_URL: str = os.environ.get("TAXMATJIP_API_BASE_URL", f"{SITE_URL}/api/places")

# 18 region shard keys (mirror of the web app's PLACE_REGION_KEYS). Shards for
# regions with no data return 404 and are treated as empty.
REGION_KEYS: tuple[str, ...] = (
    "seoul", "busan", "daegu", "incheon", "gwangju", "daejeon", "ulsan",
    "sejong", "gyeonggi", "gangwon", "chungbuk", "chungnam", "jeonbuk",
    "jeonnam", "gyeongbuk", "gyeongnam", "jeju", "unknown",
)
REGION_SET: frozenset[str] = frozenset(REGION_KEYS)

# Human label fallback (the data also carries regionLabel per place).
REGION_LABELS: dict[str, str] = {
    "seoul": "서울", "busan": "부산", "daegu": "대구", "incheon": "인천",
    "gwangju": "광주", "daejeon": "대전", "ulsan": "울산", "sejong": "세종",
    "gyeonggi": "경기", "gangwon": "강원", "chungbuk": "충북", "chungnam": "충남",
    "jeonbuk": "전북", "jeonnam": "전남", "gyeongbuk": "경북", "gyeongnam": "경남",
    "jeju": "제주", "unknown": "지역미확인",
}

# ── Server runtime ───────────────────────────────────────────────────────────
HOST: str = os.environ.get("HOST", "0.0.0.0")
PORT: int = int(os.environ.get("PORT", "8080"))
# FastMCP serves Streamable HTTP at this path; the registered Endpoint URL is
# <kc-endpoint>{MCP_PATH}.
MCP_PATH: str = os.environ.get("TAXMATJIP_MCP_PATH", "/mcp/")

# ── Query caps (protect token budget + memory) ───────────────────────────────
DEFAULT_LIMIT: int = 10
MAX_LIMIT: int = 50
DEFAULT_RADIUS_M: int = 1000
MAX_RADIUS_M: int = 5000
EVIDENCE_PREVIEW: int = 20  # max evidence rows returned inline by detail tool

# ── Data cache ──────────────────────────────────────────────────────────────
CACHE_TTL_SECONDS: int = int(os.environ.get("TAXMATJIP_CACHE_TTL", "900"))  # 15 min
HTTP_TIMEOUT_SECONDS: float = float(os.environ.get("TAXMATJIP_HTTP_TIMEOUT", "20"))
# Bound the per-place detail cache so a client issuing many distinct ids cannot grow
# memory without limit; locks are striped (fixed count) for the same reason.
DETAIL_CACHE_MAX: int = int(os.environ.get("TAXMATJIP_DETAIL_CACHE_MAX", "4096"))
LOCK_STRIPES: int = 64
