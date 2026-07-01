"""Great-circle distance for the 'near me' tool."""

from __future__ import annotations

import math

_EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in meters between two WGS84 points."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    )
    # Clamp against float rounding for near-antipodal points (asin domain is [-1, 1]).
    a = min(1.0, max(0.0, a))
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))
