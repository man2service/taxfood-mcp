"""Render tool result dicts as compact Markdown (the PlayMCP dev guide recommends
cleaned text over raw JSON). Every place line carries its `id` so the agent can chain
into the detail/source tools, and a KakaoMap link for one-tap navigation.
"""

from __future__ import annotations

from typing import Any


def _won(n: Any) -> str:
    try:
        return f"{int(n):,}원"
    except (TypeError, ValueError):
        return "0원"


def _insts(top: list[str], k: int = 3) -> str:
    return ", ".join(top[:k]) if top else "-"


def _place_line(i: int, p: dict[str, Any], extra: str = "") -> str:
    loc = f"{p.get('regionLabel', '')} {p.get('district', '')}".strip()
    return (
        f"{i}. **{p.get('name', '')}** · {loc}{extra} · "
        f"방문 {p.get('visitCount', 0)}회 · 총 {_won(p.get('totalSpendKrw'))} · "
        f"평균 {_won(p.get('avgSpendKrw'))} · 주요기관 {_insts(p.get('topInstitutions', []))} · "
        f"`id:{p.get('id', '')}` · [지도]({p.get('mapUrl', '')})"
    )


def _error(res: dict[str, Any]) -> str | None:
    if "error" in res:
        msg = f"⚠️ {res['error']}"
        if res.get("validRegions"):
            msg += "\n\n사용 가능한 지역: " + ", ".join(res["validRegions"])
        return msg
    return None


def search(res: dict[str, Any]) -> str:
    err = _error(res)
    if err:
        return err
    results = res.get("results", [])
    if not results:
        return "검색 결과가 없습니다."
    scope = f" ({res['region']})" if res.get("region") else ""
    head = f"## 세금맛집 검색 결과{scope} — 총 {res.get('count', 0)}곳 (상위 {len(results)}곳)"
    lines = [_place_line(i + 1, p) for i, p in enumerate(results)]
    return head + "\n" + "\n".join(lines)


def nearby(res: dict[str, Any]) -> str:
    results = res.get("results", [])
    if not results:
        return f"반경 {res.get('radiusMeters', 0)}m 내에 세금맛집이 없습니다."
    head = f"## 내 주변 세금맛집 — 반경 {res.get('radiusMeters', 0)}m, {res.get('count', 0)}곳 중 가까운 {len(results)}곳"
    lines = [
        _place_line(i + 1, p, extra=f" · {p.get('distanceMeters', 0)}m")
        for i, p in enumerate(results)
    ]
    return head + "\n" + "\n".join(lines)


def rank(res: dict[str, Any]) -> str:
    err = _error(res)
    if err:
        return err
    summary = res.get("areaSummary", {})
    results = res.get("results", [])
    if not results:
        return f"{summary.get('regionLabel', '')} 지역 데이터가 없습니다."
    dist = f" {summary['district']}" if summary.get("district") else ""
    head = (
        f"## {summary.get('regionLabel', '')}{dist} 세금 지출 랭킹 "
        f"(기준: {res.get('metric', 'total_spend')}) — {summary.get('placeCount', 0)}곳, "
        f"합계 {_won(summary.get('totalSpendKrw'))}"
    )
    lines = [_place_line(p.get("rank", i + 1), p) for i, p in enumerate(results)]
    return head + "\n" + "\n".join(lines)


def agency(res: dict[str, Any]) -> str:
    err = _error(res)
    if err:
        return err
    places = res.get("topPlaces", [])
    if not places:
        return f"'{res.get('institution', '')}' 기관의 지출 기록을 찾지 못했습니다."
    head = (
        f"## '{res.get('institution', '')}' 업무추진비 식당 요약 — "
        f"{res.get('placeCount', 0)}곳 · 총 {_won(res.get('totalSpendKrw'))} · 방문 {res.get('totalVisits', 0)}회"
    )
    lines = [_place_line(i + 1, p) for i, p in enumerate(places)]
    note = f"\n\n_{res['note']}_" if res.get("note") else ""
    return head + "\n" + "\n".join(lines) + note


def detail(res: dict[str, Any]) -> str:
    err = _error(res)
    if err:
        return err
    head = (
        f"## {res.get('name', '')} ({res.get('regionLabel', '')} {res.get('district', '')})\n"
        f"- 방문 {res.get('visitCount', 0)}회 · 총 {_won(res.get('totalSpendKrw'))} · "
        f"1인당 {_won(res.get('perHeadKrw'))} · [지도]({res.get('mapUrl', '')})"
    )
    ag = res.get("agencies", [])
    if ag:
        head += "\n\n**사용 기관**\n" + "\n".join(
            f"- {a.get('name', '')}: {a.get('count', 0)}회 · {_won(a.get('amountKrw'))}" for a in ag
        )
    execs = res.get("executions", [])
    if execs:
        shown = len(execs)
        total = res.get("executionCount", shown)
        head += f"\n\n**집행 내역 (최근 {shown}/{total}건)**\n" + "\n".join(
            f"- {e.get('date', '')} · {e.get('department', '')} · {_won(e.get('amountKrw'))}"
            + (f" · {e.get('headcount')}명" if e.get("headcount") else "")
            + f" · {e.get('purpose', '')} · [출처]({e.get('sourceUrl', '')})"
            for e in execs
        )
    if res.get("note"):
        head += f"\n\n_{res['note']}_"
    return head


def sources(res: dict[str, Any]) -> str:
    err = _error(res)
    if err:
        return err
    records = res.get("records", [])
    if not records:
        note = res.get("note") or "공식 출처 기록이 없습니다."
        name = res.get("name", "")
        return f"## {name} — 공식 출처\n{note}" if name else note
    head = f"## {res.get('name', '')} — 공식 출처 (전체 {res.get('recordCount', 0)}건 중 {len(records)}건)"
    lines = [
        f"- {r.get('date', '')} · {r.get('institution', '')} · {_won(r.get('amountKrw'))} · "
        f"{r.get('purpose', '')} · [{r.get('sourceTitle', '출처')}]({r.get('sourceUrl', '')})"
        for r in records
    ]
    return head + "\n" + "\n".join(lines)


def regions(res: dict[str, Any]) -> str:
    rows = res.get("regions", [])
    nation = res.get("nationwide", {})
    head = (
        f"## 세금맛집 지역 커버리지 — 전국 {nation.get('placeCount', 0):,}곳 · "
        f"총 {_won(nation.get('totalSpendKrw'))}"
    )
    lines = [
        f"- {r.get('regionLabel', '')} (`{r.get('regionKey', '')}`): {r.get('placeCount', 0):,}곳 · {_won(r.get('totalSpendKrw'))}"
        for r in rows
        if r.get("placeCount", 0) > 0
    ]
    return head + "\n" + "\n".join(lines)
