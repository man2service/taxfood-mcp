"""Tool logic — pure async functions over a DataStore, returning JSON-serializable
dicts. server.py wraps these and renders markdown; tests exercise these directly.
"""

from __future__ import annotations

from typing import Any

from . import config
from .data import DataStore
from .geo import haversine_m
from .links import place_map_url
from .models import PlaceSummary
from .sanitize import scrub_text

_SORT_ATTR = {
    "visit_count": "visit_count",
    "total_spend": "total_spend_krw",
    "avg_spend": "avg_spend_krw",
}


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def _limit(value: int | None) -> int:
    if value is None:
        return config.DEFAULT_LIMIT
    return _clamp(int(value), 1, config.MAX_LIMIT)


def _place_dict(p: PlaceSummary, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": p.id,
        "name": p.name,
        "region": p.region,
        "regionLabel": p.region_label,
        "district": p.district,
        "latitude": p.latitude,
        "longitude": p.longitude,
        "visitCount": p.visit_count,
        "totalSpendKrw": p.total_spend_krw,
        "avgSpendKrw": p.avg_spend_krw,
        "topInstitutions": list(p.top_institutions),
        "mapUrl": place_map_url(p),
    }
    if extra:
        d.update(extra)
    return d


def _region_error(region: str) -> dict[str, Any]:
    return {
        "error": f"unknown region '{region}'",
        "validRegions": list(config.REGION_KEYS),
    }


async def search_tax_restaurants(
    store: DataStore,
    query: str | None = None,
    region: str | None = None,
    district: str | None = None,
    sort_by: str = "visit_count",
    limit: int | None = None,
) -> dict[str, Any]:
    bundle = await store.index()
    if region and region not in config.REGION_SET:
        return _region_error(region)
    corpus = bundle.by_region.get(region, []) if region else bundle.places
    q = (query or "").strip().casefold()
    dist = (district or "").strip()
    results = [
        p
        for p in corpus
        if (not q or q in p.name.casefold())
        and (not dist or dist in p.district)
    ]
    attr = _SORT_ATTR.get(sort_by, "visit_count")
    results.sort(key=lambda p: getattr(p, attr), reverse=True)
    n = _limit(limit)
    return {
        "query": query,
        "region": region,
        "district": district,
        "sortBy": sort_by if sort_by in _SORT_ATTR else "visit_count",
        "count": len(results),
        "results": [_place_dict(p) for p in results[:n]],
    }


async def find_nearby_tax_restaurants(
    store: DataStore,
    latitude: float,
    longitude: float,
    radius_m: int | None = None,
    limit: int | None = None,
    min_visit_count: int | None = None,
) -> dict[str, Any]:
    bundle = await store.index()
    radius_val = config.DEFAULT_RADIUS_M if radius_m is None else int(radius_m)
    radius = _clamp(radius_val, 1, config.MAX_RADIUS_M)
    min_visits = int(min_visit_count) if min_visit_count else 0
    hits: list[tuple[float, PlaceSummary]] = []
    for p in bundle.geo:
        if p.visit_count < min_visits:
            continue
        d = haversine_m(latitude, longitude, p.latitude, p.longitude)  # type: ignore[arg-type]
        if d <= radius:
            hits.append((d, p))
    hits.sort(key=lambda t: t[0])
    n = _limit(limit)
    return {
        "center": {"latitude": latitude, "longitude": longitude},
        "radiusMeters": radius,
        "count": len(hits),
        "results": [
            _place_dict(p, {"distanceMeters": round(d)}) for d, p in hits[:n]
        ],
    }


async def rank_tax_restaurants_in_area(
    store: DataStore,
    region: str,
    district: str | None = None,
    metric: str = "total_spend",
    limit: int | None = None,
) -> dict[str, Any]:
    if region not in config.REGION_SET:
        return _region_error(region)
    bundle = await store.index()
    in_region = bundle.by_region.get(region, [])
    region_label = in_region[0].region_label if in_region else config.REGION_LABELS.get(region, region)
    dist = (district or "").strip()
    corpus = [p for p in in_region if not dist or dist in p.district]
    attr = _SORT_ATTR.get(metric, "total_spend_krw")
    corpus.sort(key=lambda p: getattr(p, attr), reverse=True)
    n = _limit(limit)
    ranked = [_place_dict(p, {"rank": i + 1}) for i, p in enumerate(corpus[:n])]
    return {
        "areaSummary": {
            "region": region,
            "regionLabel": region_label,
            "district": district,
            "placeCount": len(corpus),
            "totalSpendKrw": sum(p.total_spend_krw for p in corpus),
        },
        "metric": metric if metric in _SORT_ATTR else "total_spend",
        "results": ranked,
    }


async def get_agency_dining_summary(
    store: DataStore,
    institution: str,
    region: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    bundle = await store.index()
    if region and region not in config.REGION_SET:
        return _region_error(region)
    needle = institution.strip().casefold()
    corpus = bundle.by_region.get(region, []) if region else bundle.places
    matches = [
        p for p in corpus if any(needle in inst.casefold() for inst in p.top_institutions)
    ]
    matches.sort(key=lambda p: p.total_spend_krw, reverse=True)
    n = _limit(limit)
    return {
        "institution": institution,
        "region": region,
        "placeCount": len(matches),
        "totalSpendKrw": sum(p.total_spend_krw for p in matches),
        "totalVisits": sum(p.visit_count for p in matches),
        "note": "Approximate: places where the institution is among the top spenders; "
        "amounts are each place's total tax dining spend.",
        "topPlaces": [_place_dict(p) for p in matches[:n]],
    }


async def get_place_spending_detail(
    store: DataStore,
    place_id: str,
    region: str | None = None,
) -> dict[str, Any]:
    place = await store.get_place(place_id)
    resolved_region, detail = await store.place_detail(place_id, region)
    if place is None and detail is None:
        return {"error": f"place '{place_id}' not found", "placeId": place_id}
    executions = []
    if detail is not None:
        for e in detail.executions[: config.EVIDENCE_PREVIEW]:
            executions.append(
                {
                    "date": e.date,
                    "institution": e.agency,
                    "department": e.dept,
                    "headcount": e.head,
                    "amountKrw": e.amount,
                    "purpose": scrub_text(e.purpose),
                    "sourceTitle": scrub_text(e.source_title),
                    "sourceUrl": e.source_url,
                }
            )
    out: dict[str, Any] = {
        "id": place_id,
        "name": place.name if place else "",
        "region": resolved_region,
        "regionLabel": place.region_label if place else "",
        "district": place.district if place else (detail.source_district if detail else ""),
        "visitCount": place.visit_count if place else (len(detail.executions) if detail else 0),
        "totalSpendKrw": place.total_spend_krw if place else 0,
        "mapUrl": place_map_url(place) if place else "",
        "executionCount": len(detail.executions) if detail else 0,
        "executions": executions,
        "agencies": [
            {"name": a.agency, "count": a.visits, "amountKrw": a.amount}
            for a in (detail.agencies if detail else ())
        ],
        "totalHeadcount": detail.total_heads if detail else 0,
        "perHeadKrw": detail.per_head if detail else 0,
    }
    return out


async def get_spend_source_records(
    store: DataStore,
    place_id: str,
    region: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    place = await store.get_place(place_id)
    _resolved, detail = await store.place_detail(place_id, region)
    if detail is None:
        return {"error": f"no source records for place '{place_id}'", "placeId": place_id, "records": []}
    n = _clamp(int(limit) if limit else 5, 1, config.MAX_LIMIT)
    records = [
        {
            "date": e.date,
            "institution": e.agency,
            "purpose": scrub_text(e.purpose),
            "amountKrw": e.amount,
            "sourceTitle": scrub_text(e.source_title),
            "sourceUrl": e.source_url,
        }
        for e in detail.executions[:n]
    ]
    return {
        "id": place_id,
        "name": place.name if place else "",
        "recordCount": len(detail.executions),
        "records": records,
    }


async def list_regions_overview(store: DataStore) -> dict[str, Any]:
    bundle = await store.index()
    regions = [
        {
            "regionKey": key,
            "regionLabel": config.REGION_LABELS.get(key, key),
            "placeCount": bundle.region_count.get(key, 0),
            "totalSpendKrw": bundle.region_spend.get(key, 0),
        }
        for key in config.REGION_KEYS
    ]
    regions.sort(key=lambda r: r["placeCount"], reverse=True)
    return {
        "regions": regions,
        "nationwide": {
            "placeCount": bundle.total_count,
            "totalSpendKrw": bundle.total_spend,
        },
    }
