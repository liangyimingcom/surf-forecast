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

from . import governance

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


# 晨风风质：`WindKind` 的**枚举值**（models.WindKind：off/cross/on）→ 人话。
# 为什么必须在后端做：`dawnWind` 原样透出会让「off」被读成「关闭 / 没风」，
# 而它其实是**最好**的风况（离岸风梳直浪面）——2026-08-06 零上下文可用性评审实测到这个误读。
# 前端也有一层同样的翻译作兜底（读旧缓存时用），但根治必须在这里：否则任何新接入的
# 客户端都会重踩。措辞与 `charts.WIND_META` 保持一致，避免两处口径分叉。
_DAWN_CN = {
    "off": "晨风离岸·梳面",
    "cross": "晨风侧岸·尚可",
    "on": "晨风向岸·吹乱",
}


def _headline(day: dict) -> str:
    """行动首句：窗口 + 板型（Fable5「早上7点到，带鱼板」），退回小白建议。"""
    win = (day.get("window") or "").strip()
    board = (day.get("board") or "").strip()
    parts = []
    if win:
        # 明写「下水」而非「到」：引擎的 window 是**最佳可冲时段**（人在水里的时间），
        # 而详情页另有「几点出门」倒推。只说「到」会被理解成到达时间 → 按窗口起点出门
        # 就会整整迟到一个车程（零上下文评审判定为最严重歧义）。
        parts.append(f"{win} 下水")
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
        # 认得的枚举翻成人话；认不出的原样透出（不猜、不吞——将来枚举扩了也不会静默丢因子）
        kf.append(_DAWN_CN.get(dw, dw))
    tp = [x for x in (day.get("tp2") or day.get("tp") or []) if isinstance(x, (int, float))]
    if tp:
        # 「Tp」对非物理背景用户是纯噪音；口径仍是谱峰周期，只是把名字说出来
        kf.append(f"峰周期 {max(tp):.0f}s")
    return kf[:3]


def build_recommendation(
    region: str,
    registry_rows: list[dict],
    reader: Any,
    now: Optional[_dt.datetime] = None,
    manifest: Optional[dict] = None,
    reports: Optional[dict] = None,
) -> dict:
    """返回 Recommendation（Fable5 §1.1）。region 空 = 全部浪点。

    reader: 具 .get(key)->dict|None 的缓存读取器（deps._cache_reader()），None=无缓存桶。
    manifest: 当日刷新 manifest（R2 决策9）。今日 manifest 存在 → 只认 succeeded 集
    （刷新中间态对外不可见）；无/非今日 → 退回逐报告 calibratedAt 判新鲜（兼容旧缓存）。
    reports: 可选预取的 slug->report 映射（bulk_latest 并发读）；提供则不再逐点打 reader。
    """
    n = _now_gmt8(now)
    today = n.strftime("%Y-%m-%d")
    in_region = (
        [r for r in registry_rows if (r.get("region_cn") or "其他") == region]
        if region else list(registry_rows)
    )
    # R2 §1.3 三道过滤（决策2）：剔 is_test → 剔非 open。
    # coverage 分母 = 可推荐池（不含永不参与推荐的维护/测试点，避免虚增降级感）。
    pool = governance.recommendable_rows(in_region)
    total = len(pool)
    # R2 决策9：今日 manifest 在场 → succeeded 集是新鲜性唯一裁判（中间态不可见）
    succeeded: Optional[set] = None
    if manifest and manifest.get("date") == today:
        succeeded = set(manifest.get("succeeded") or [])
    scored: list[dict] = []
    for r in pool:
        slug = r.get("slug")
        if not slug or (reader is None and reports is None):
            continue
        if succeeded is not None and slug not in succeeded:
            continue
        if reports is not None:
            rep = reports.get(slug)
        else:
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
            "beach_group": r.get("beach_group"),
            "_bd": bd,
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    fresh = len(scored)  # 新鲜计数在同滩去重前：coverage 反映数据健康，去重只影响展示条目
    scored = governance.dedup_by_beach(scored)  # 第三道：每滩只推最高分机位（决策8）
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
