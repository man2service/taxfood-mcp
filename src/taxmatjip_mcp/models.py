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

    @classmethod
    def from_evidence(cls, d: dict[str, Any]) -> "Execution":
        """One row of the raw detail-<region>.json evidence[] (bundled offline)."""
        head = d.get("headcount")
        return cls(
            date=str(d.get("spentOn", "")),
            agency=str(d.get("institution", "")),
            dept=str(d.get("department", "")),
            head=_as_int(head) if head is not None else None,
            amount=_as_int(d.get("amountKrw")),
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


def build_place_detail(
    evidence: list[dict[str, Any]],
    source_region_label: str = "",
    source_district: str = "",
) -> PlaceDetail:
    """Build a PlaceDetail from raw detail-<region>.json evidence rows (bundled offline)
    — mirrors the web app's buildDetail: executions newest-first, per-institution rollup,
    head totals, and per-head cost. Each execution keeps its official sourceUrl."""
    execs = sorted(
        (Execution.from_evidence(e) for e in evidence),
        key=lambda e: e.date,
        reverse=True,
    )
    rollup: dict[str, list[int]] = {}
    total_heads = 0
    total_amount = 0
    has_heads = False
    for e in execs:
        entry = rollup.setdefault(e.agency, [0, 0])
        entry[0] += 1
        entry[1] += e.amount
        total_amount += e.amount
        if e.head is not None:
            total_heads += e.head
            has_heads = True
    agencies = tuple(
        AgencyRollup(agency=name, visits=cnt, amount=amt)
        for name, (cnt, amt) in sorted(rollup.items(), key=lambda kv: kv[1][1], reverse=True)
    )
    per_head = total_amount // total_heads if total_heads > 0 else 0
    return PlaceDetail(
        executions=tuple(execs),
        agencies=agencies,
        total_heads=total_heads,
        per_head=per_head,
        has_heads=has_heads,
        source_region_label=source_region_label,
        source_district=source_district,
    )
