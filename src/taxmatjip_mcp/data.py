"""Runtime data access. Nothing is bundled in this repo: the dataset is fetched from
public taxfood.kr endpoints and cached in memory.

- search-index.json (all ~86k places, with coords) → search / nearby / rank / agency /
  regions. Fetched once and indexed by id, region, and coordinates.
- GET /api/places/<id>?region=<region> (the web app's maintained detail API) → the
  per-place evidence ledger (executions + agency rollup) for the detail / source tools.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from . import config
from .models import PlaceDetail, PlaceSummary, build_place_detail


@dataclass(slots=True)
class IndexBundle:
    """Everything derivable from search-index.json, built once per refresh."""

    places: list[PlaceSummary]
    by_id: dict[str, PlaceSummary]
    geo: list[PlaceSummary]  # only places with non-null coords
    by_region: dict[str, list[PlaceSummary]]
    region_count: dict[str, int]
    region_spend: dict[str, int]
    total_count: int
    total_spend: int


def _build_bundle(raw: list[dict]) -> IndexBundle:
    places = [PlaceSummary.from_dict(d) for d in raw]
    by_id: dict[str, PlaceSummary] = {}
    geo: list[PlaceSummary] = []
    by_region: dict[str, list[PlaceSummary]] = defaultdict(list)
    region_count: dict[str, int] = defaultdict(int)
    region_spend: dict[str, int] = defaultdict(int)
    total_spend = 0
    for p in places:
        by_id[p.id] = p
        if p.has_coords:
            geo.append(p)
        by_region[p.region].append(p)
        region_count[p.region] += 1
        region_spend[p.region] += p.total_spend_krw
        total_spend += p.total_spend_krw
    return IndexBundle(
        places=places,
        by_id=by_id,
        geo=geo,
        by_region=dict(by_region),
        region_count=dict(region_count),
        region_spend=dict(region_spend),
        total_count=len(places),
        total_spend=total_spend,
    )


@dataclass(slots=True)
class _Cached:
    value: object
    ts: float


class DataStore:
    """Async, in-memory, TTL-cached view of the taxfood.kr dataset."""

    def __init__(
        self,
        base_url: str | None = None,
        api_base_url: str | None = None,
        ttl_seconds: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self._base = (base_url or config.DATA_BASE_URL).rstrip("/")
        self._api = (api_base_url or config.API_BASE_URL).rstrip("/")
        self._ttl = ttl_seconds if ttl_seconds is not None else config.CACHE_TTL_SECONDS
        self._timeout = timeout if timeout is not None else config.HTTP_TIMEOUT_SECONDS
        self._client: httpx.AsyncClient | None = None
        self._index: _Cached | None = None
        # Bounded LRU keyed by "<region>/<place_id>".
        self._detail: OrderedDict[str, _Cached] = OrderedDict()
        self._index_lock = asyncio.Lock()
        # Striped locks (fixed count) instead of an unbounded per-key dict.
        self._detail_locks = [asyncio.Lock() for _ in range(config.LOCK_STRIPES)]

    # ── HTTP ────────────────────────────────────────────────────────────────
    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"accept": "application/json"},
                follow_redirects=True,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _read_local(filename: str):
        """Read a bundled data file from DATA_DIR (baked into the image). None if
        unset/missing — the Kakao Cloud runtime blocks egress, so search-index is
        served from here."""
        if not config.DATA_DIR:
            return None
        path = os.path.join(config.DATA_DIR, filename)
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    async def _get_json(self, url: str):
        """GET JSON, degrading to None on any failure (non-200, bad JSON, or an
        unreachable host — the KC runtime has no outbound network)."""
        try:
            resp = await self._http().get(url)
        except httpx.HTTPError:
            return None
        if resp.status_code != 200:
            return None
        try:
            return resp.json()
        except ValueError:
            return None

    def _fresh(self, cached: _Cached | None) -> bool:
        return cached is not None and (time.monotonic() - cached.ts) < self._ttl

    # ── Index (search-index.json) ───────────────────────────────────────────
    async def index(self) -> IndexBundle:
        if self._fresh(self._index):
            return self._index.value  # type: ignore[return-value]
        async with self._index_lock:
            if self._fresh(self._index):
                return self._index.value  # type: ignore[return-value]
            # Bundled file first (KC runtime), then the CDN (local dev).
            raw = self._read_local("search-index.json")
            if raw is None:
                raw = await self._get_json(f"{self._base}/search-index.json")
            bundle = _build_bundle(raw or [])
            self._index = _Cached(bundle, time.monotonic())
            return bundle

    async def by_id(self) -> dict[str, PlaceSummary]:
        return (await self.index()).by_id

    async def resolve_region(self, place_id: str) -> str | None:
        p = (await self.by_id()).get(place_id)
        return p.region if p else None

    async def get_place(self, place_id: str) -> PlaceSummary | None:
        return (await self.by_id()).get(place_id)

    # ── Detail (web app API: /api/places/<id>?region=<region>) ──────────────
    def _detail_lock(self, key: str) -> asyncio.Lock:
        return self._detail_locks[hash(key) % config.LOCK_STRIPES]

    def _detail_get(self, key: str) -> _Cached | None:
        cached = self._detail.get(key)
        if cached is not None:
            self._detail.move_to_end(key)  # LRU
        return cached

    def _detail_put(self, key: str, value: _Cached) -> None:
        self._detail[key] = value
        self._detail.move_to_end(key)
        while len(self._detail) > config.DETAIL_CACHE_MAX:
            self._detail.popitem(last=False)  # evict least-recently-used

    @staticmethod
    def _detail_db() -> str:
        """Path to the bundled per-place evidence DB (SQLite), or '' if not bundled."""
        return os.path.join(config.DATA_DIR, "detail.sqlite") if config.DATA_DIR else ""

    async def _detail_from_db(self, place_id: str) -> PlaceDetail | None:
        db = self._detail_db()
        if not db or not os.path.exists(db):
            return None

        def _query():
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                return con.execute(
                    "SELECT evidence, source_region_label, source_district "
                    "FROM detail WHERE place_id = ?",
                    (place_id,),
                ).fetchone()
            finally:
                con.close()

        row = await asyncio.to_thread(_query)
        if row is None:
            return None
        evidence_json, srl, sd = row
        try:
            evidence = json.loads(evidence_json)
        except (ValueError, TypeError):
            return None
        return build_place_detail(evidence, srl or "", sd or "")

    async def place_detail(
        self, place_id: str, region: str | None = None
    ) -> tuple[str | None, PlaceDetail | None]:
        """Fetch the place's evidence ledger with its official per-record source URLs.
        Served from the bundled SQLite DB (offline; the KC runtime has no egress); falls
        back to the web detail API for local dev. Authoritative region comes from the
        search index. Returns (region, detail) — detail is None if unknown."""
        region = await self.resolve_region(place_id) or region
        if not region or region not in config.REGION_SET:
            return None, None
        key = f"{region}/{place_id}"
        cached = self._detail_get(key)
        if self._fresh(cached):
            return region, cached.value  # type: ignore[return-value]
        async with self._detail_lock(key):
            cached = self._detail_get(key)
            if self._fresh(cached):
                return region, cached.value  # type: ignore[return-value]
            detail = await self._detail_from_db(place_id)
            if detail is None and not self._detail_db():
                # No bundled DB (local dev) → the web detail API.
                url = f"{self._api}/{quote(place_id, safe='')}?region={quote(region, safe='')}"
                raw = await self._get_json(url)
                if isinstance(raw, dict) and "executions" in raw:
                    detail = PlaceDetail.from_api(raw)
            self._detail_put(key, _Cached(detail, time.monotonic()))
            return region, detail

    # ── Startup warmup (meets the avg≤100ms / p99≤3s latency requirement) ────
    async def warmup(self) -> None:
        """Prefetch the index so the first user call is not cold."""
        try:
            await self.index()
        except Exception:  # noqa: BLE001 — warmup is best-effort; tools re-fetch lazily
            pass
