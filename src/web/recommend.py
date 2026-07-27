"""P1.1 区域推荐（决策助手首屏数据源）。

派生自每日评分缓存（`{slug}/latest.json` = render_json 输出），**不新增持久化表**。

数据诚实红线（north_star + R0.2 教训）：
- 只排「当日新鲜」（`calibratedAt` 日期 == 今日 GMT+8）的浪点；
- 缓存陈旧/不全/无新鲜点 → `degraded=True` + 显式计数，**绝不拿旧分/样例分冒充**（首屏=产品信誉）；
- 冷点炸弹近亲防护：不因刷新覆盖缺口而静默展示两天前的分。
"""
from __future__ import annotations

import collections
import datetime as _dt
from typing import Any, Callable, Optional

GMT8 = _dt.timezone(_dt.timedelta(hours=8))


def _now_gmt8(now: Optional[_dt.datetime]) -> _dt.datetime:
    n = now or _dt.datetime.now(GMT8)
    if n.tzinfo is None:
        n = n.replace(tzinfo=GMT8)
    return n.astimezone(GMT8)


def _is_fresh(report: dict, today: str) -> bool:
    """calibratedAt 形如 'YYYY-MM-DD HH:MM GMT+8'；前 10 位为 GMT+8 日期。"""
    return str(report.get("calibratedAt", ""))[:10] == today


def _best_day(report: dict) -> Optional[dict]:
    days = report.get("days") or []
    if not days:
        return None
    ranking = report.get("ranking") or []
    if ranking and isinstance(ranking[0], int) and 0 <= ranking[0] < len(days):
        return days[ranking[0]]
    for d in days:
        if d.get("best"):
            return d
    return days[0]


def _headline(day: dict) -> str:
    """行动首句：窗口 + 板型（Fable5「早上7点到，带鱼板」），退回小白建议。"""
    win = (day.get("window") or "").strip()
    board = (day.get("board") or "").strip()
    parts = []
    if win:
        parts.append(f"{win}到")
    if board:
        parts.append(f"带{board}")
    if parts:
        return "，".join(parts)
    return (day.get("novice") or "按窗口择时下水").strip()[:40]


def _key_factors(day: dict) -> list[str]:
    """≤3 项关键因子：浪高 · 晨风风质 · 峰周期。"""
    kf: list[str] = []
    hs = [x for x in (day.get("hs") or []) if isinstance(x, (int, float))]
    if hs:
        kf.append(f"{max(hs):.1f}m浪")
    dw = (day.get("dawnWind") or "").strip()
    if dw:
        kf.append(dw)
    tp = [x for x in (day.get("tp2") or day.get("tp") or []) if isinstance(x, (int, float))]
    if tp:
        kf.append(f"Tp{max(tp):.0f}s")
    return kf[:3]


def build_recommendation(
    region: str,
    registry_rows: list[dict],
    reader: Any,
    now: Optional[_dt.datetime] = None,
) -> dict:
    """返回 Recommendation（Fable5 §1.1）。region 空 = 全部浪点。

    reader: 具 .get(key)->dict|None 的缓存读取器（deps._cache_reader()），None=无缓存桶。
    """
    n = _now_gmt8(now)
    today = n.strftime("%Y-%m-%d")
    in_region = (
        [r for r in registry_rows if (r.get("region_cn") or "其他") == region]
        if region else list(registry_rows)
    )
    total = len(in_region)
    scored: list[dict] = []
    for r in in_region:
        slug = r.get("slug")
        if not slug or reader is None:
            continue
        try:
            rep = reader.get(f"{slug}/latest.json")
        except Exception:  # noqa: BLE001  一个坏缓存不拖垮整体推荐
            rep = None
        if not rep or not _is_fresh(rep, today):
            continue
        bd = _best_day(rep)
        if not bd or not isinstance(bd.get("score"), (int, float)):
            continue
        scored.append({
            "spot_slug": slug,
            "spot_name": r.get("spot") or rep.get("spot") or slug,
            "day": bd.get("date"),
            "week": bd.get("week"),
            "score": round(float(bd["score"]), 1),
            "_bd": bd,
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    fresh = len(scored)
    out: dict = {
        "region": region,
        "generated_at": n.strftime("%Y-%m-%d %H:%M GMT+8"),
        "fresh_count": fresh,
        "total_count": total,
        "degraded": fresh == 0 or fresh < total,
        "best": None,
        "alternatives": [],
    }
    if scored:
        top = scored[0]
        out["best"] = {
            "spot_slug": top["spot_slug"], "spot_name": top["spot_name"],
            "day": top["day"], "week": top.get("week"), "score": top["score"],
            "headline": _headline(top["_bd"]),
            "key_factors": _key_factors(top["_bd"]),
        }
        out["alternatives"] = [
            {"spot_slug": s["spot_slug"], "spot_name": s["spot_name"],
             "day": s["day"], "week": s.get("week"), "score": s["score"]}
            for s in scored[1:3]
        ]
    return out


def list_regions(registry_rows: list[dict]) -> list[dict]:
    """区域列表（聚合 catalog 的 region_cn），供首访选地区引导。"""
    c = collections.Counter((r.get("region_cn") or "其他") for r in registry_rows)
    return [{"region": k, "count": v} for k, v in sorted(c.items(), key=lambda kv: -kv[1])]
