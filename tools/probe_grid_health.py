#!/usr/bin/env python3
"""上游格点健康巡检（R4）—— 纯标准库、**只读**，不写 DynamoDB / 不写 S3。

判定与引擎一致（`surf_forecast/fetch.py`）：总浪高优先 WAM025，缺则回退 best_match。
所以一个浪点只有在**两个源都无浪高**时才真正不可用。分类：

  ok_wam        主模型 WAM025 有数据（正常）
  ok_fallback   WAM025 该格点全空、best_match 有数据 → 引擎会用 best_match 救回
                （报告里 dataSource 会标 best_match(fallback)）
  dead          两个源都无浪高 → 真正的"上游无数据"，刷新会计 failed（R1）
                此时尝试邻近格点（±0.05°/±0.1°），给出可用坐标建议供人工核实
  bad_coord     坐标非法（如 lat>90），上游直接报错

用法：
  # 本地快照（零凭证，快）
  python3 tools/probe_grid_health.py
  # 生产注册表（只读 scan）
  SF_STORE=dynamo SF_TABLE_PREFIX=surf-forecast-dev AWS_PROFILE=oversea1 \
    AWS_REGION=ap-northeast-1 PYTHONPATH=src python3 tools/probe_grid_health.py --source store
  # 只看某几个点 / 限量 / 机器可读
  python3 tools/probe_grid_health.py --slug sl82 --slug sl75
  python3 tools/probe_grid_health.py --limit 5 --json

退出码：0 全部可用；2 存在 dead / bad_coord（可接 cron 告警，同 monitor_counts.py 约定）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
TIMEZONE = "Asia/Shanghai"
TIMEOUT = 20
SLEEP_S = 0.3                      # 对上游客气些（58 点顺序跑）
NEIGHBOR_OFFSETS = [0.05, -0.05, 0.1, -0.1]
SNAPSHOT = "reference/data/shilaoren_spots.json"


def _get(params: dict) -> dict:
    url = MARINE_URL + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:                      # 400 = 参数非法（坐标越界）
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:                                    # noqa: BLE001
            return {"error": True, "reason": f"HTTP {e.code}"}
    except Exception as e:                                   # noqa: BLE001
        return {"error": True, "reason": f"{type(e).__name__}: {e}"}


def probe(lat: float, lon: float, model: str | None) -> dict:
    """返回 {ok: bool, n: 非空点数, total: 时点数, grid: (lat,lon), error: str|None}。"""
    p = {"latitude": lat, "longitude": lon, "hourly": "wave_height",
         "timezone": TIMEZONE, "forecast_days": 1}
    if model:
        p["models"] = model
    d = _get(p)
    if d.get("error"):
        return {"ok": False, "n": 0, "total": 0, "grid": None,
                "error": str(d.get("reason"))}
    vals = (d.get("hourly") or {}).get("wave_height") or []
    n = sum(1 for v in vals if v is not None)
    return {"ok": n > 0, "n": n, "total": len(vals),
            "grid": (d.get("latitude"), d.get("longitude")), "error": None}


def suggest_neighbors(lat: float, lon: float) -> list[dict]:
    """仅对 dead 点调用：在邻近格点找有数据的候选（先动经度再动纬度）。"""
    out = []
    for off in NEIGHBOR_OFFSETS:
        for dlat, dlon in ((0.0, off), (off, 0.0)):
            cand_lat, cand_lon = round(lat + dlat, 6), round(lon + dlon, 6)
            r = probe(cand_lat, cand_lon, None)               # best_match 覆盖更广
            time.sleep(SLEEP_S)
            if r["ok"]:
                out.append({"lat": cand_lat, "lon": cand_lon,
                            "grid": r["grid"], "n": r["n"]})
                if len(out) >= 2:
                    return out
    return out


def classify(row: dict) -> dict:
    slug, spot = row.get("slug"), row.get("spot") or row.get("name")
    lat, lon = float(row["lat"]), float(row["lon"])
    wam = probe(lat, lon, "ecmwf_wam025")
    time.sleep(SLEEP_S)
    if wam["error"]:
        return {"slug": slug, "spot": spot, "lat": lat, "lon": lon,
                "verdict": "bad_coord", "detail": wam["error"]}
    if wam["ok"]:
        return {"slug": slug, "spot": spot, "lat": lat, "lon": lon,
                "verdict": "ok_wam", "detail": f"WAM {wam['n']}/{wam['total']} 点",
                "grid": wam["grid"]}
    best = probe(lat, lon, None)
    time.sleep(SLEEP_S)
    if best["ok"]:
        return {"slug": slug, "spot": spot, "lat": lat, "lon": lon,
                "verdict": "ok_fallback",
                "detail": f"WAM 全空({wam['total']}点) → best_match {best['n']}/{best['total']} 点",
                "grid": best["grid"]}
    return {"slug": slug, "spot": spot, "lat": lat, "lon": lon,
            "verdict": "dead", "detail": "WAM 与 best_match 均无浪高",
            "grid": wam["grid"], "suggestions": suggest_neighbors(lat, lon)}


def load_rows(source: str) -> list[dict]:
    if source == "store":
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
        from web import db, governance                        # noqa: PLC0415
        rows = db.get_store().list_listed_registry() or []
        return governance.visible_rows(rows)                  # 剔测试点
    with open(SNAPSHOT, encoding="utf-8") as f:
        snap = json.load(f)
    return [s for s in snap.get("spots", [])
            if s.get("lat") is not None and s.get("lon") is not None]


def main() -> int:
    ap = argparse.ArgumentParser(description="上游格点健康巡检（只读）")
    ap.add_argument("--source", choices=("snapshot", "store"), default="snapshot")
    ap.add_argument("--slug", action="append", default=[], help="只查指定 slug（可多次）")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--json", action="store_true", dest="as_json")
    a = ap.parse_args()

    rows = load_rows(a.source)
    if a.slug:
        rows = [r for r in rows if r.get("slug") in set(a.slug)]
    if a.limit:
        rows = rows[:a.limit]
    if not rows:
        print("没有可巡检的浪点（检查 --source / --slug）", file=sys.stderr)
        return 1

    results = []
    for i, r in enumerate(rows, 1):
        try:
            res = classify(r)
        except (KeyError, TypeError, ValueError) as e:
            res = {"slug": r.get("slug"), "spot": r.get("spot") or r.get("name"),
                   "verdict": "bad_coord", "detail": f"注册表行有问题: {e}"}
        results.append(res)
        if not a.as_json:
            mark = {"ok_wam": "✅", "ok_fallback": "🟡", "dead": "🔴",
                    "bad_coord": "⛔"}[res["verdict"]]
            print(f"[{i}/{len(rows)}] {mark} {res['slug']:<8} {str(res['spot'])[:14]:<16} "
                  f"{res['verdict']:<12} {res['detail']}")
            for s in res.get("suggestions") or []:
                print(f"            ↳ 建议坐标 {s['lat']},{s['lon']} → 格点 {s['grid']}（{s['n']} 点）")

    counts: dict[str, int] = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    if a.as_json:
        print(json.dumps({"counts": counts, "results": results}, ensure_ascii=False, indent=2))
    else:
        print(f"\n汇总（{a.source}，共 {len(results)} 点）：" +
              " · ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        if counts.get("ok_fallback"):
            print("🟡 ok_fallback 表示 WAM025 该格点无数据、由 best_match 救回 —— "
                  "引擎会在报告里标 dataSource=best_match(fallback)，属正常降级而非故障。")
        if counts.get("dead") or counts.get("bad_coord"):
            print("🔴 dead / ⛔ bad_coord 需人工处置（改坐标属生产数据写，需授权）。")
    return 2 if (counts.get("dead") or counts.get("bad_coord")) else 0


if __name__ == "__main__":
    raise SystemExit(main())
