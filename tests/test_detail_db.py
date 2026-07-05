"""The offline (bundled) path: search-index from a local file + per-place evidence from
a local SQLite DB, so the detail/source tools return each record's official source URL
without any network (as on the Kakao Cloud runtime)."""

import json
import sqlite3

import pytest_asyncio

from taxmatjip_mcp import config, format, tools
from taxmatjip_mcp.data import DataStore

_INDEX = [
    {
        "id": "p1",
        "name": "다금",
        "region": "busan",
        "regionLabel": "부산",
        "district": "부산진구",
        "latitude": 35.18,
        "longitude": 129.05,
        "visitCount": 2,
        "totalSpendKrw": 294000,
        "avgSpendKrw": 147000,
        "topInstitutions": ["부산광역시교육청"],
    }
]
_EVIDENCE = [
    {
        "spentOn": "2026-05-20",
        "institution": "부산광역시교육청",
        "department": "중등교육과",
        "purpose": "협의회",
        "amountKrw": 164000,
        "headcount": 12,
        "sourceUrl": "https://www.pen.go.kr/upload/x.xlsx",
        "sourceTitle": "2026년 5월 업무추진비",
    },
    {
        "spentOn": "2026-04-10",
        "institution": "부산광역시교육청",
        "department": "유아교육과",
        "purpose": "워크숍",
        "amountKrw": 130000,
        "headcount": None,
        "sourceUrl": "https://opengov.seoul.go.kr/expense/2",
        "sourceTitle": "2026년 4월 업무추진비",
    },
]


@pytest_asyncio.fixture
async def offline_store(tmp_path, monkeypatch):
    (tmp_path / "search-index.json").write_text(
        json.dumps(_INDEX, ensure_ascii=False), encoding="utf-8"
    )
    con = sqlite3.connect(str(tmp_path / "detail.sqlite"))
    con.execute(
        "CREATE TABLE detail (place_id TEXT PRIMARY KEY, region TEXT, evidence TEXT, "
        "source_region_label TEXT, source_district TEXT)"
    )
    con.execute(
        "INSERT INTO detail VALUES (?,?,?,?,?)",
        ("p1", "busan", json.dumps(_EVIDENCE, ensure_ascii=False), "부산", "부산 부산진구"),
    )
    con.commit()
    con.close()
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    store = DataStore()
    try:
        yield store
    finally:
        await store.aclose()


async def test_index_from_local_file(offline_store):
    bundle = await offline_store.index()
    assert bundle.total_count == 1
    assert bundle.region_count["busan"] == 1


async def test_place_detail_from_sqlite(offline_store):
    region, detail = await offline_store.place_detail("p1")
    assert region == "busan"
    assert detail is not None
    assert len(detail.executions) == 2
    assert detail.executions[0].date == "2026-05-20"  # newest first
    assert detail.executions[0].source_url == "https://www.pen.go.kr/upload/x.xlsx"
    assert detail.agencies[0].agency == "부산광역시교육청"
    assert detail.agencies[0].visits == 2
    assert detail.per_head == 294000 // 12  # only the first row has a headcount


async def test_source_records_return_real_urls(offline_store):
    res = await tools.get_spend_source_records(offline_store, "p1")
    assert res["recordCount"] == 2
    urls = [r["sourceUrl"] for r in res["records"]]
    assert "https://www.pen.go.kr/upload/x.xlsx" in urls
    assert "https://opengov.seoul.go.kr/expense/2" in urls
    md = format.sources(res)
    assert "pen.go.kr" in md and "opengov.seoul.go.kr" in md


async def test_detail_markdown_shows_executions(offline_store):
    md = format.detail(await tools.get_place_spending_detail(offline_store, "p1"))
    assert "집행 내역" in md
    assert "pen.go.kr" in md
