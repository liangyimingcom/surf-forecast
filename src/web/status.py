"""R2 §2/§3.2 数据健康状态 —— /api/status 的组装层（公开状态页唯一数据源）。

双重定位：站长每日一瞥的运维仪表（决策5：无推送告警，这里是唯一防线）
+ 对用户的信任背书（系统坦白数据健康，与「先验证过去再相信未来」同构）。
全部派生自 manifest + registry + 缓存，无新持久化。
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Optional

from . import governance, recommend

GMT8 = _dt.timezone(_dt.timedelta(hours=8))


def build_status(registry_rows: list[dict], reader: Any,
                 manifest: Optional[dict],
                 now: Optional[_dt.datetime] = None) -> dict:
    """组装状态页数据：今日刷新概况 + 各区域推荐可用性 + 最近运行记录。"""
    n = (now or _dt.datetime.now(GMT8)).astimezone(GMT8)
    today = n.strftime("%Y-%m-%d")
    rows = governance.visible_rows(registry_rows)
    pool = governance.recommendable_rows(rows)

    m = manifest or {}
    m_today = m.get("date") == today
    refresh = {
        "date": m.get("date"),
        "kind": m.get("kind"),
        "run_at": m.get("run_at"),
        "expected": len(m.get("expected") or []),
        "succeeded": len(m.get("succeeded") or []),
        "failed": sorted((m.get("failed") or {}).keys()),
        "is_today": m_today,
    } if m else None

    regions = []
    for item in recommend.list_regions(rows):
        reg = item["region"]
        rec = recommend.build_recommendation(reg, registry_rows, reader,
                                             now=n, manifest=manifest)
        regions.append({
            "region": reg,
            "spots": item["count"],
            "pool": rec["total_count"],
            "fresh": rec["fresh_count"],
            "available": rec["best"] is not None,
            "degraded": rec["degraded"],
        })

    return {
        "generated_at": n.strftime("%Y-%m-%d %H:%M GMT+8"),
        "refresh": refresh,
        "coverage": {
            "pool": len(pool),
            "fresh": sum(r["fresh"] for r in regions),
        },
        "regions": regions,
        "history": list((m.get("history") or []))[::-1],  # 最新在前
    }
