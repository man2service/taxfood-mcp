from taxmatjip_mcp import tools


async def test_search_by_name(store):
    res = await tools.search_tax_restaurants(store, query="밥집")
    assert res["count"] == 1
    assert res["results"][0]["id"] == "p-seoul-2"
    assert res["results"][0]["mapUrl"].startswith("https://map.kakao.com/link/map/")


async def test_search_region_scope_and_sort(store):
    res = await tools.search_tax_restaurants(store, region="seoul", sort_by="total_spend")
    ids = [r["id"] for r in res["results"]]
    assert ids[0] == "p-seoul-1"  # highest total_spend in seoul
    assert "p-busan-1" not in ids


async def test_search_invalid_region(store):
    res = await tools.search_tax_restaurants(store, region="atlantis")
    assert "error" in res
    assert "seoul" in res["validRegions"]


async def test_nearby_sorts_by_distance_and_skips_nulls(store):
    # Near Seoul City Hall — p-seoul-1 is ~0m; p-nocoord must never appear.
    res = await tools.find_nearby_tax_restaurants(store, 37.5665, 126.9780, radius_m=5000)
    ids = [r["id"] for r in res["results"]]
    assert ids[0] == "p-seoul-1"
    assert "p-nocoord" not in ids
    assert res["results"][0]["distanceMeters"] < 5


async def test_nearby_radius_excludes_far(store):
    res = await tools.find_nearby_tax_restaurants(store, 37.5665, 126.9780, radius_m=1000)
    ids = [r["id"] for r in res["results"]]
    assert ids == ["p-seoul-1"]  # 강남/부산 are far


async def test_rank_in_area(store):
    res = await tools.rank_tax_restaurants_in_area(store, "seoul", metric="total_spend")
    assert res["results"][0]["rank"] == 1
    assert res["results"][0]["id"] == "p-seoul-1"
    assert res["areaSummary"]["placeCount"] == 3


async def test_agency_summary_matches_substring(store):
    res = await tools.get_agency_dining_summary(store, "강남구청")
    assert res["placeCount"] == 1
    assert res["topPlaces"][0]["id"] == "p-seoul-2"


async def test_detail_scrubs_pii(store):
    res = await tools.get_place_spending_detail(store, "p-seoul-1")
    assert res["executionCount"] == 2
    purposes = " ".join(e["purpose"] for e in res["executions"])
    titles = " ".join(e["sourceTitle"] for e in res["executions"])
    assert "홍길동" not in purposes
    assert "홍길동" not in titles
    assert "ㅇㅇㅇ 과장" in purposes
    assert res["agencies"][0]["name"] == "서울특별시청"


async def test_detail_not_found(store):
    res = await tools.get_place_spending_detail(store, "ghost-id")
    assert "error" in res


async def test_sources_scrubbed(store):
    res = await tools.get_spend_source_records(store, "p-seoul-1", limit=5)
    assert res["recordCount"] == 2
    blob = " ".join(r["purpose"] + r["sourceTitle"] for r in res["records"])
    assert "홍길동" not in blob
    assert res["records"][0]["sourceUrl"].startswith("https://opengov.seoul.go.kr/")


async def test_regions_overview(store):
    res = await tools.list_regions_overview(store)
    assert res["nationwide"]["placeCount"] == 4
    top = res["regions"][0]
    assert top["regionKey"] == "seoul"
    assert top["placeCount"] == 3
