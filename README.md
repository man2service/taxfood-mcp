# 세금맛집 MCP 서버 (taxfood-mcp)

전국 공공기관이 **업무추진비(세금)**로 식사한 식당 데이터를 AI 에이전트가 쓸 수 있는
**MCP(Model Context Protocol) 도구**로 노출하는 서버입니다. 카카오 **PlayMCP / AGENTIC PLAYER 10**
출품용. 모든 근거에 공식 정보공개 출처 링크가 붙는 **투명성·정보공개** 서비스입니다.

> 데이터 원본/지도 서비스: https://taxfood.kr

## 설계 원칙

- **Streamable HTTP, 스테이트리스** 원격 MCP 서버 (PlayMCP 요구사항). 단일 `POST /mcp/`.
- **데이터 무동봉**: 데이터셋은 런타임에 공개 CDN(`https://taxfood.kr/data/*.json`)에서 fetch + 인메모리 캐시.
  → 이 **공개 레포에는 데이터·개인정보·시크릿이 일절 포함되지 않습니다.**
- **응답 단계 PII 스크럽**: 혹시 모를 이름+직함 패턴을 응답에서 제거.
- 모든 출력에 **카카오맵 딥링크**(`map.kakao.com/link/...`) 동봉.

## 도구 (7)

| 도구 | 기능 |
|---|---|
| `search_tax_restaurants` | 이름/지역/구 검색 + 정렬 |
| `find_nearby_tax_restaurants` | 좌표 기반 주변 검색(카톡 위치공유) |
| `rank_tax_restaurants_in_area` | 시/도·구 지출 랭킹 |
| `get_agency_dining_summary` | 기관별 지출 집계 |
| `get_place_spending_detail` | 근거 원장(날짜·부서·금액·목적) |
| `get_spend_source_records` | 공식 출처 링크만 반환(검증) |
| `list_regions_overview` | 지역 커버리지/총계 |

## 로컬 실행

```bash
pip install -e ".[dev]"
python -m taxmatjip_mcp          # http://0.0.0.0:8080/mcp/

# 검증
pytest
npx @modelcontextprotocol/inspector   # tools/list, tools/call 스모크
```

## 배포 (카카오 클라우드 / PlayMCP in KC)

`playmcp.kakaocloud.io` → `+ 새 MCP 서버 등록` → **Git 소스 빌드** → 이 레포 URL + `Dockerfile`
→ Endpoint URL 발급 → PlayMCP 콘솔에 `<endpoint>/mcp/` 등록.

환경변수: `PORT`(기본 8080), `TAXMATJIP_DATA_BASE_URL`(기본 `https://taxfood.kr/data`).

## 라이선스

MIT (코드). 데이터는 각 공공기관 정보공개 자료가 원본이며 본 레포에 포함되지 않습니다.
