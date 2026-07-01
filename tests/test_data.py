async def test_index_bundle_counts(store):
    b = await store.index()
    assert b.total_count == 4
    assert b.region_count["seoul"] == 3
    assert b.region_count["busan"] == 1
    assert len(b.geo) == 3  # p-nocoord excluded


async def test_resolve_region(store):
    assert await store.resolve_region("p-busan-1") == "busan"
    assert await store.resolve_region("does-not-exist") is None


async def test_place_detail_via_api(store):
    region, detail = await store.place_detail("p-seoul-1")
    assert region == "seoul"
    assert detail is not None
    assert len(detail.executions) == 2
    assert detail.agencies[0].agency == "서울특별시청"


async def test_place_detail_missing_returns_none(store):
    region, detail = await store.place_detail("p-seoul-2")  # not in API_DETAILS -> 404
    assert region == "seoul"
    assert detail is None


async def test_index_is_cached(store):
    await store.index()
    b = await store.index()  # served from cache
    assert b.total_count == 4
