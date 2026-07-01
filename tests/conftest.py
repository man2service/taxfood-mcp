"""Test fixtures. The CDN (search-index.json) and the detail API are mocked with
respx using SYNTHETIC data only — no real personal information. One execution purpose
carries a fake "홍길동 과장" so tests prove the PII scrub fires through the pipeline.
"""

from __future__ import annotations

import re
from urllib.parse import unquote

import httpx
import pytest_asyncio
import respx

from taxmatjip_mcp import config
from taxmatjip_mcp.data import DataStore

SEARCH_INDEX = [
    {
        "id": "p-seoul-1",
        "name": "서울시청 간담회장",
        "region": "seoul",
        "regionLabel": "서울",
        "district": "중구",
        "latitude": 37.5665,
        "longitude": 126.9780,
        "visitCount": 100,
        "totalSpendKrw": 5_000_000,
        "avgSpendKrw": 50_000,
        "topInstitutions": ["서울특별시청", "행정국 총무과"],
    },
    {
        "id": "p-seoul-2",
        "name": "강남밥집",
        "region": "seoul",
        "regionLabel": "서울",
        "district": "강남구",
        "latitude": 37.4979,
        "longitude": 127.0276,
        "visitCount": 50,
        "totalSpendKrw": 3_000_000,
        "avgSpendKrw": 60_000,
        "topInstitutions": ["강남구청"],
    },
    {
        "id": "p-busan-1",
        "name": "부산해장국",
        "region": "busan",
        "regionLabel": "부산",
        "district": "부산진구",
        "latitude": 35.1580,
        "longitude": 129.0596,
        "visitCount": 30,
        "totalSpendKrw": 2_000_000,
        "avgSpendKrw": 66_667,
        "topInstitutions": ["부산광역시청", "부산 부산진구청"],
    },
    {
        "id": "p-nocoord",
        "name": "좌표없는집",
        "region": "seoul",
        "regionLabel": "서울",
        "district": "종로구",
        "latitude": None,
        "longitude": None,
        "visitCount": 10,
        "totalSpendKrw": 500_000,
        "avgSpendKrw": 50_000,
        "topInstitutions": ["종로구청"],
    },
]

API_DETAILS = {
    "p-seoul-1": {
        "executions": [
            {
                "date": "2026-05-01",
                "agency": "서울특별시청",
                "dept": "총무과",
                "head": 8,
                "amount": 250_000,
                "purpose": "홍길동 과장 주재 부서 간담회",
                "sourceUrl": "https://opengov.seoul.go.kr/expense/1",
                "sourceTitle": "2026년 5월 업무추진비 - 홍길동 과장 승인",
            },
            {
                "date": "2026-04-10",
                "agency": "서울특별시청",
                "dept": "총무과",
                "head": 6,
                "amount": 180_000,
                "purpose": "국제교류과 정책 간담회",
                "sourceUrl": "https://opengov.seoul.go.kr/expense/2",
                "sourceTitle": "2026년 4월 업무추진비",
            },
        ],
        "agencies": [{"agency": "서울특별시청", "visits": 2, "amount": 430_000}],
        "totalHeads": 14,
        "perHead": 30_714,
        "hasHeads": True,
        "sourceRegionLabel": "서울",
        "sourceDistrict": "서울 중구",
    },
}


def _api_side_effect(request: httpx.Request) -> httpx.Response:
    pid = unquote(request.url.path.rstrip("/").rsplit("/", 1)[-1])
    data = API_DETAILS.get(pid)
    if data is None:
        return httpx.Response(404, text="not found")
    return httpx.Response(200, json=data)


def setup_routes(router: respx.Router) -> None:
    router.get(f"{config.DATA_BASE_URL}/search-index.json").mock(
        return_value=httpx.Response(200, json=SEARCH_INDEX)
    )
    router.route(
        method="GET", url__regex=re.escape(config.API_BASE_URL) + r"/.+"
    ).mock(side_effect=_api_side_effect)


@pytest_asyncio.fixture
async def store():
    with respx.mock(assert_all_called=False) as router:
        setup_routes(router)
        s = DataStore(ttl_seconds=3600)
        try:
            yield s
        finally:
            await s.aclose()
