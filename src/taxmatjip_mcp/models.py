"""Typed views over the raw taxfood.kr JSON. Parsers are tolerant of null/missing
fields (the dataset carries null coords, null headcount, and evolving id prefixes)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(slots=True, frozen=True)
class PlaceSummary:
    """One entry of search-index.json / slim-<region>.json."""

    id: str
    name: str
    region: str
    region_label: str
    district: str
    latitude: float | None
    longitude: float | None
    visit_count: int
    total_spend_krw: int
    avg_spend_krw: int
    top_institutions: tuple[str, ...]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PlaceSummary":
        return cls(
            id=str(d.get("id", "")),
            name=str(d.get("name", "")),
            region=str(d.get("region", "")),
            region_label=str(d.get("regionLabel", "")),
            district=str(d.get("district", "")),
            latitude=_as_float_or_none(d.get("latitude")),
            longitude=_as_float_or_none(d.get("longitude")),
            visit_count=_as_int(d.get("visitCount")),
            total_spend_krw=_as_int(d.get("totalSpendKrw")),
            avg_spend_krw=_as_int(d.get("avgSpendKrw")),
            top_institutions=tuple(str(x) for x in (d.get("topInstitutions") or [])),
        )

    @property
    def has_coords(self) -> bool:
        return self.latitude is not None and self.longitude is not None


@dataclass(slots=True, frozen=True)
class Execution:
    """One disclosed tax-money (업무추진비) dining execution, as served by the web app's
    detail API (GET /api/places/<id>?region=<region>). Each is backed by an official
    government source URL."""

    date: str
    agency: str
    dept: str
    head: int | None
    amount: int
    purpose: str
    source_url: str
    source_title: str

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> "Execution":
        head = d.get("head")
        return cls(
            date=str(d.get("date", "")),
            agency=str(d.get("agency", "")),
            dept=str(d.get("dept", "")),
            head=_as_int(head) if head is not None else None,
            amount=_as_int(d.get("amount")),
            purpose=str(d.get("purpose", "")),
            source_url=str(d.get("sourceUrl", "")),
            source_title=str(d.get("sourceTitle", "")),
        )


@dataclass(slots=True, frozen=True)
class AgencyRollup:
    """Per-institution rollup at one place (detail API `agencies[]`)."""

    agency: str
    visits: int
    amount: int

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> "AgencyRollup":
        return cls(
            agency=str(d.get("agency", "")),
            visits=_as_int(d.get("visits")),
            amount=_as_int(d.get("amount")),
        )


@dataclass(slots=True, frozen=True)
class PlaceDetail:
    """Full detail-API payload for one place."""

    executions: tuple[Execution, ...]
    agencies: tuple[AgencyRollup, ...]
    total_heads: int
    per_head: int
    has_heads: bool
    source_region_label: str
    source_district: str

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> "PlaceDetail":
        return cls(
            executions=tuple(Execution.from_api(x) for x in (d.get("executions") or [])),
            agencies=tuple(AgencyRollup.from_api(x) for x in (d.get("agencies") or [])),
            total_heads=_as_int(d.get("totalHeads")),
            per_head=_as_int(d.get("perHead")),
            has_heads=bool(d.get("hasHeads")),
            source_region_label=str(d.get("sourceRegionLabel", "")),
            source_district=str(d.get("sourceDistrict", "")),
        )
