from taxmatjip_mcp.geo import haversine_m


def test_same_point_is_zero():
    assert haversine_m(37.5665, 126.9780, 37.5665, 126.9780) == 0.0


def test_seoul_to_busan_about_325km():
    # Seoul City Hall → Busan City Hall ≈ 325 km.
    d = haversine_m(37.5665, 126.9780, 35.1798, 129.0750)
    assert 315_000 < d < 335_000


def test_short_distance_reasonable():
    # ~100m north.
    d = haversine_m(37.5665, 126.9780, 37.5674, 126.9780)
    assert 90 < d < 110
