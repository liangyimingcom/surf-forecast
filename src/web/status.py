"""R2 §2/§3.2 数据健康状态 —— /api/status 的组装层（公开状态页唯一数据源）。

双重定位：站长每日一瞥的运维仪表（决策5：无推送告警，这里是唯一防线）
+ 对用户的信任背书（系统坦白数据健康，与「先验证过去再相信未来」同构）。
全部派生自 manifest + registry + 缓存，无新持久化。
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Optional

from . import governance, recommend
from . import refresh as refresh_mod  # 避免与本模块局部变量 refresh（manifest 摘要）遮蔽

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
        # R1.2：manifest 里 failed 本就是 {slug: 原因}，旧版只暴露 slug 列表 → 站长看不出
        # "为什么失败"（是上游格点无数据、validate 不过、还是取数异常）。
        # 保持 failed 为 slug 列表（前端/契约向后兼容），另加带原因的明细。
        "failed_detail": {k: str(v) for k, v in sorted((m.get("failed") or {}).items())},
        "is_today": m_today,
    } if m else None

    # 并发预取一次全量 latest（原实现每区域串行逐点 S3 读 → /api/status ~2s）
    all_slugs = [r.get("slug") for r in pool if r.get("slug")]
    reports = refresh_mod.bulk_latest(reader, all_slugs)

    regions = []
    for item in recommend.list_regions(rows):
        reg = item["region"]
        rec = recommend.build_recommendation(reg, registry_rows, reader,
                                             now=n, manifest=manifest,
                                             reports=reports)
        regions.append({
            "region": reg,
            "spots": item["count"],
            "pool": rec["total_count"],
            "fresh": rec["fresh_count"],
            "available": rec["best"] is not None,
            "degraded": rec["degraded"],
        })

    _dupes = governance.coord_duplicate_groups(rows)
    return {
        "generated_at": n.strftime("%Y-%m-%d %H:%M GMT+8"),
        "refresh": refresh,
        "coverage": {
            "pool": len(pool),
            "fresh": sum(r["fresh"] for r in regions),
        },
        "regions": regions,
        # R2：把「只能靠人肉翻库才看得见」的坏数据搬到唯一的故障发现渠道上。
        # 探测集用 visible_rows（已剔 is_test）——测试点不外泄到公开接口（决策6）。
        # 坐标重复只上报 severity=suspect（跨滩/跨区）——同滩不同机位是预期，
        # 一并报会让 3 组里 2 组是误报，告警随即被无视（狼来了）。
        "data_issues": {
            "coord_invalid": governance.coord_invalid_rows(rows),
            "coord_duplicates": [g for g in _dupes if g["severity"] == "suspect"],
            "coord_duplicates_benign_n": sum(1 for g in _dupes if g["severity"] != "suspect"),
        },
        "history": list((m.get("history") or []))[::-1],  # 最新在前
    }
