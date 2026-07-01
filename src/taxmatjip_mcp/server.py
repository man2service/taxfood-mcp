"""FastMCP server wiring. Registers the 7 read-only tools with full annotations and
service-name-bearing descriptions (PlayMCP review requirements), renders results as
Markdown, and warms the cache in the background at startup.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import config, format, tools
from .data import DataStore

store = DataStore()

_INSTRUCTIONS = (
    "TaxMatjip(세금맛집) exposes where Korean public institutions spent tax money "
    "(업무추진비) on dining, nationwide (~86,000 places), each backed by official "
    "open-government disclosure links. Use it to search restaurants, find nearby ones "
    "from a location, rank areas, summarize an institution's dining spend, and pull the "
    "official source records. Data is public-interest transparency information; present "
    "it neutrally."
)


@asynccontextmanager
async def _lifespan(_server: FastMCP):
    # Warm the index in the background so the port binds immediately (KC health
    # check friendly) while the first queries stay fast (avg≤100ms / p99≤3s).
    task = asyncio.create_task(store.warmup())
    try:
        yield
    finally:
        task.cancel()
        await store.aclose()


mcp: FastMCP = FastMCP(name="세금맛집 TaxMatjip", instructions=_INSTRUCTIONS, lifespan=_lifespan)


def _ro(title: str) -> ToolAnnotations:
    # openWorldHint=True: every tool reads a live, externally-maintained dataset
    # (taxfood.kr) whose contents change over time.
    return ToolAnnotations(
        title=title,
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )


@mcp.tool(
    name="search_tax_restaurants",
    description=(
        "Search restaurants where Korean public institutions spent tax money (업무추진비) "
        "on dining, from TaxMatjip(세금맛집). Filter by name query, region key, and/or "
        "district; sort by visit_count, total_spend, or avg_spend. Returns a ranked "
        "markdown list with each place's id (for follow-up tools), totals, top "
        "institutions, and a KakaoMap link."
    ),
    annotations=_ro("Search tax-spending restaurants"),
)
async def search_tax_restaurants(
    query: str | None = None,
    region: str | None = None,
    district: str | None = None,
    sort_by: str = "visit_count",
    limit: int = config.DEFAULT_LIMIT,
) -> str:
    return format.search(
        await tools.search_tax_restaurants(store, query, region, district, sort_by, limit)
    )


@mcp.tool(
    name="find_nearby_tax_restaurants",
    description=(
        "Find TaxMatjip(세금맛집) tax-spending restaurants near a latitude/longitude "
        "(e.g. a shared KakaoTalk location), sorted by distance. Returns nearby places "
        "with distance in meters, spend totals, and KakaoMap links."
    ),
    annotations=_ro("Find nearby tax-spending restaurants"),
)
async def find_nearby_tax_restaurants(
    latitude: float,
    longitude: float,
    radius_m: int = config.DEFAULT_RADIUS_M,
    limit: int = config.DEFAULT_LIMIT,
    min_visit_count: int | None = None,
) -> str:
    return format.nearby(
        await tools.find_nearby_tax_restaurants(
            store, latitude, longitude, radius_m, limit, min_visit_count
        )
    )


@mcp.tool(
    name="rank_tax_restaurants_in_area",
    description=(
        "Rank the top tax-spending restaurants in a Korean region (and optional "
        "district) by total_spend, visit_count, or avg_spend, from TaxMatjip(세금맛집)."
    ),
    annotations=_ro("Rank tax-spending restaurants in an area"),
)
async def rank_tax_restaurants_in_area(
    region: str,
    district: str | None = None,
    metric: str = "total_spend",
    limit: int = config.DEFAULT_LIMIT,
) -> str:
    return format.rank(
        await tools.rank_tax_restaurants_in_area(store, region, district, metric, limit)
    )


@mcp.tool(
    name="get_agency_dining_summary",
    description=(
        "Summarize where a given Korean public institution (e.g. 강남구청, 서울특별시청) "
        "spent tax money on dining, from TaxMatjip(세금맛집): number of matching places, "
        "total spend, visits, and the top spots. Institution match is a substring."
    ),
    annotations=_ro("Summarize an institution's dining spend"),
)
async def get_agency_dining_summary(
    institution: str,
    region: str | None = None,
    limit: int = config.DEFAULT_LIMIT,
) -> str:
    return format.agency(
        await tools.get_agency_dining_summary(store, institution, region, limit)
    )


@mcp.tool(
    name="get_place_spending_detail",
    description=(
        "Get a restaurant's recent disclosed spending records from TaxMatjip(세금맛집): "
        "the latest executions (date, department, amount, purpose, headcount) as a "
        "preview, plus an agency rollup, total count, and per-head cost. Pass a place id "
        "from another tool. region is optional (resolved automatically)."
    ),
    annotations=_ro("Get a restaurant's full spending detail"),
)
async def get_place_spending_detail(place_id: str, region: str | None = None) -> str:
    return format.detail(await tools.get_place_spending_detail(store, place_id, region))


@mcp.tool(
    name="get_spend_source_records",
    description=(
        "Return the official government source records (title + URL) backing a "
        "restaurant's tax spending in TaxMatjip(세금맛집), for verification and citation. "
        "Pass a place id from another tool."
    ),
    annotations=_ro("Get official source records for a place"),
)
async def get_spend_source_records(
    place_id: str, region: str | None = None, limit: int = 5
) -> str:
    return format.sources(
        await tools.get_spend_source_records(store, place_id, region, limit)
    )


@mcp.tool(
    name="list_regions_overview",
    description=(
        "List TaxMatjip(세금맛집) coverage by Korean region (시/도) with place counts and "
        "total tax dining spend, plus nationwide totals. Use to discover or disambiguate "
        "which regions have data before a narrower query."
    ),
    annotations=_ro("List regional coverage overview"),
)
async def list_regions_overview() -> str:
    return format.regions(await tools.list_regions_overview(store))


def main() -> None:
    asyncio.run(
        mcp.run_http_async(
            transport="http",
            host=config.HOST,
            port=config.PORT,
            path=config.MCP_PATH,
            stateless_http=True,
            show_banner=False,
        )
    )
