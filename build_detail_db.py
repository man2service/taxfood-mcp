"""Build the bundled per-place evidence SQLite DB from taxfood.kr detail shards.

Run at image-build time (CI has network). The runtime reads this DB offline — the
Kakao Cloud deploy has no outbound network — so the detail/source tools can return
each disclosed spend's OFFICIAL source URL (opengov.seoul.go.kr, pen.go.kr, etc.).

Usage: python build_detail_db.py [output.sqlite]
"""

from __future__ import annotations

import json
import sqlite3
import sys
import urllib.error
import urllib.request

from taxmatjip_mcp.config import DATA_BASE_URL, REGION_KEYS


def _fetch(url: str):
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:  # noqa: S310 — fixed public host
        if resp.status != 200:
            return None
        return json.load(resp)


def build(out_path: str) -> int:
    con = sqlite3.connect(out_path)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    con.execute(
        "CREATE TABLE IF NOT EXISTS detail ("
        "place_id TEXT PRIMARY KEY, region TEXT, evidence TEXT, "
        "source_region_label TEXT, source_district TEXT)"
    )
    total = 0
    for region in REGION_KEYS:
        url = f"{DATA_BASE_URL}/detail-{region}.json"
        try:
            data = _fetch(url)
        except urllib.error.HTTPError as e:
            print(f"skip {region}: HTTP {e.code}", flush=True)
            continue
        except Exception as e:  # noqa: BLE001
            print(f"skip {region}: {e}", flush=True)
            continue
        if not isinstance(data, dict):
            print(f"skip {region}: not a dict", flush=True)
            continue
        rows = []
        for pid, v in data.items():
            if not isinstance(v, dict):
                continue
            ev = v.get("evidence") or []
            if not ev:
                continue
            rows.append(
                (
                    pid,
                    region,
                    json.dumps(ev, ensure_ascii=False, separators=(",", ":")),
                    str(v.get("sourceRegionLabel", "")),
                    str(v.get("sourceDistrict", "")),
                )
            )
        con.executemany("INSERT OR REPLACE INTO detail VALUES (?,?,?,?,?)", rows)
        con.commit()
        total += len(rows)
        print(f"{region}: {len(rows)} places", flush=True)
    con.execute("CREATE INDEX IF NOT EXISTS idx_detail_region ON detail(region)")
    con.commit()
    con.execute("VACUUM")
    con.close()
    print(f"built {out_path}: {total} places", flush=True)
    if total < 1000:
        raise SystemExit(f"detail DB too small ({total} places)")
    return total


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "/app/data/detail.sqlite")
