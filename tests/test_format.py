from taxmatjip_mcp import format


def test_search_markdown():
    md = format.search(
        {
            "count": 1,
            "region": "seoul",
            "results": [
                {
                    "id": "p1",
                    "name": "밥집",
                    "regionLabel": "서울",
                    "district": "중구",
                    "visitCount": 3,
                    "totalSpendKrw": 12345,
                    "avgSpendKrw": 4115,
                    "topInstitutions": ["구청"],
                    "mapUrl": "https://map.kakao.com/link/map/x,1,2",
                }
            ],
        }
    )
    assert "밥집" in md
    assert "`id:p1`" in md
    assert "[지도]" in md
    assert "12,345원" in md


def test_error_markdown():
    md = format.search({"error": "unknown region 'x'", "validRegions": ["seoul"]})
    assert "⚠️" in md
    assert "seoul" in md


def test_empty_results():
    assert "없" in format.search({"count": 0, "results": []})


def test_regions_markdown():
    md = format.regions(
        {
            "regions": [{"regionKey": "seoul", "regionLabel": "서울", "placeCount": 3, "totalSpendKrw": 100}],
            "nationwide": {"placeCount": 3, "totalSpendKrw": 100},
        }
    )
    assert "전국" in md
    assert "서울" in md
