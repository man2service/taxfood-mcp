from taxmatjip_mcp.models import PlaceDetail, PlaceSummary


def test_place_summary_tolerates_null_coords_and_missing():
    p = PlaceSummary.from_dict(
        {"id": "x", "name": "n", "region": "seoul", "latitude": None, "longitude": None}
    )
    assert p.id == "x"
    assert p.has_coords is False
    assert p.visit_count == 0
    assert p.top_institutions == ()


def test_place_summary_with_coords():
    p = PlaceSummary.from_dict(
        {"id": "x", "name": "n", "region": "busan", "latitude": 35.1, "longitude": 129.0}
    )
    assert p.has_coords is True


def test_place_detail_from_api():
    d = PlaceDetail.from_api(
        {
            "executions": [
                {"date": "2026-01-01", "agency": "A", "dept": "B", "head": None, "amount": 100}
            ],
            "agencies": [{"agency": "A", "visits": 1, "amount": 100}],
            "totalHeads": 0,
            "perHead": 0,
            "hasHeads": False,
        }
    )
    assert len(d.executions) == 1
    assert d.executions[0].head is None
    assert d.executions[0].amount == 100
    assert d.agencies[0].agency == "A"
