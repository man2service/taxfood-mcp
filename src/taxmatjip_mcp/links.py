"""KakaoMap deep links. These are destination URLs (map.kakao.com), not tool/server
names, so they carry no naming restriction. Output field is `mapUrl`."""

from __future__ import annotations

from urllib.parse import quote

from .models import PlaceSummary


def map_url(name: str, lat: float, lng: float) -> str:
    """One-tap KakaoMap pin link."""
    return f"https://map.kakao.com/link/map/{quote(name)},{lat},{lng}"


def search_url(query: str) -> str:
    """Name-based KakaoMap search link (fallback when coordinates are missing)."""
    return f"https://map.kakao.com/link/search/{quote(query)}"


def place_map_url(p: PlaceSummary) -> str:
    if p.has_coords:
        return map_url(p.name, p.latitude, p.longitude)
    query = f"{p.name} {p.district}".strip()
    return search_url(query or p.name)
