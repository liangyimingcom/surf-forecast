"""每日自动更新 —— refresh_job（deployment-and-ops D5, design §3）。

读写解耦的「写」侧：定时预算所有上架浪点的预报+昨日历史，过 validate 后写缓存。
红线：validate 不通过不覆盖上一版（保留旧数据，不白屏）；全程 GMT+8。
缓存键：{slug}/latest.json（在线读）、{slug}/{today}.json、{slug}/history/{yesterday}.json。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from surf_forecast import analyze, render
from surf_forecast.validate import ReportValidationError

logger = logging.getLogger("surf_forecast.refresh")

GMT8 = ZoneInfo("Asia/Shanghai")

# 上架浪点（青岛山东头默认；多浪点在此追加）
DEFAULT_SPOTS = [
    {"slug": "shandongtou", "spot": "青岛山东头", "lat": 36.092, "lon": 120.468, "days": 6},
]


# —— 缓存写抽象 ——
class InMemoryCacheWriter:
    """测试/dev：内存缓存。"""

    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    def put(self, key: str, report: dict) -> None:
        self.store[key] = report

    def get(self, key: str):
        return self.store.get(key)


class S3CacheWriter:
    """生产：写 S3 预算 JSON 桶（boto3）。"""

    def __init__(self, bucket: str, client=None):
        import boto3
        self.bucket = bucket
        self.s3 = client or boto3.client("s3")

    def put(self, key: str, report: dict) -> None:
        self.s3.put_object(
            Bucket=self.bucket, Key=key,
            Body=json.dumps(report, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json; charset=utf-8",
        )


class S3CacheReader:
    """生产：读 S3 预算 JSON（在线读侧，读写解耦的「读」）。"""

    def __init__(self, bucket: str, client=None):
        import boto3
        self.bucket = bucket
        self.s3 = client or boto3.client("s3")

    def get(self, key: str):
        try:
            resp = self.s3.get_object(Bucket=self.bucket, Key=key)
            return json.loads(resp["Body"].read())
        except Exception:  # noqa: BLE001  缓存未命中/不可用 → None 走回退
            return None


def find_spot(lat: float, lon: float, spots=None) -> dict | None:
    """按坐标（小数 2 位）匹配上架浪点，命中则返回其配置（含 slug）。"""
    spots = spots if spots is not None else DEFAULT_SPOTS
    for s in spots:
        if round(s["lat"], 2) == round(lat, 2) and round(s["lon"], 2) == round(lon, 2):
            return s
    return None


def default_report_fn(spot_cfg: dict, *, calibrated_at: datetime | None = None) -> dict:
    """默认：调引擎出含昨日回看的 REPORT（validate 在 build_context 内守门）。"""
    ctx = analyze.build_context(
        spot_cfg["lat"], spot_cfg["lon"], spot_cfg.get("days", 6), spot_cfg["spot"],
        include_history=True, calibrated_at=calibrated_at,
    )
    return render.render_json(ctx)


def now_gmt8() -> datetime:
    return datetime.now(GMT8)


def refresh_spots(spots, writer, report_fn=default_report_fn,
                  clock=now_gmt8) -> dict:
    """遍历上架浪点预算并写缓存。返回每点结果摘要（ok/skipped+原因）。

    validate 失败或取数异常 → 跳过该点，**不覆盖**上一版缓存（R5.4）。
    """
    now = clock()
    today = now.date().isoformat()
    yesterday = (now.date() - timedelta(days=1)).isoformat()
    summary: dict[str, str] = {}

    for cfg in spots:
        slug = cfg["slug"]
        try:
            report = report_fn(cfg, calibrated_at=now.replace(tzinfo=None))
        except ReportValidationError as e:
            logger.error("refresh %s validate 失败，保留上一版: %s", slug, e)
            summary[slug] = f"skipped: validate({e.field})"
            continue
        except Exception as e:  # noqa: BLE001
            logger.error("refresh %s 取数/分析失败，保留上一版: %s", slug, e)
            summary[slug] = f"skipped: error({type(e).__name__})"
            continue

        writer.put(f"{slug}/latest.json", report)
        writer.put(f"{slug}/{today}.json", report)
        if report.get("history"):
            writer.put(f"{slug}/history/{yesterday}.json", report["history"])
        summary[slug] = "ok"

    return summary


# —— R4 动态刷新编排（注册表驱动，替代硬编码 DEFAULT_SPOTS）——

REFRESH_BUDGET = 50   # 每次调度预算上限 N（超出冷点降级按需）
COLD_DAYS = 14        # last_viewed 超 K 天 → 暂停定时刷新


def _reg_to_cfg(row: dict) -> dict:
    """注册表行 → refresh_spots 期望的 spot cfg。"""
    return {
        "slug": row["slug"], "spot": row.get("spot", row["slug"]),
        "lat": float(row["lat"]), "lon": float(row["lon"]),
        "days": int(row.get("days", 6)),
    }


def active_registry_spots(store, budget: int = REFRESH_BUDGET,
                          default_spots=None) -> list[dict]:
    """动态注册表驱动的上架浪点：active+refresh_enabled 行 + DEFAULT_SPOTS 兜底，按 last_viewed 降序，截断 budget。"""
    default_spots = default_spots if default_spots is not None else DEFAULT_SPOTS
    rows = list(store.list_active_registry() or [])
    rows.sort(key=lambda r: r.get("last_viewed_at_gmt8") or "", reverse=True)
    cfgs = [_reg_to_cfg(r) for r in rows]
    seen = {c["slug"] for c in cfgs}
    for d in default_spots:                       # 兜底默认浪点（注册表为空或缺失时）
        if d["slug"] not in seen:
            cfgs.append(dict(d))
            seen.add(d["slug"])
    return cfgs[:budget]


def scheduled_refresh(store, writer, budget: int = REFRESH_BUDGET,
                      report_fn=default_report_fn, clock=now_gmt8) -> dict:
    """每日调度入口：注册表驱动遍历预算，逐点 validate 守门，回写 last_refresh。"""
    spots = active_registry_spots(store, budget=budget)
    summary = refresh_spots(spots, writer, report_fn=report_fn, clock=clock)
    now_iso = clock().isoformat(timespec="seconds")
    for slug, result in summary.items():
        if result == "ok":
            reg = store.get_registry(slug)
            if reg:
                reg["last_refresh_at_gmt8"] = now_iso
                store.upsert_registry(reg)
    return summary


def budget_one(writer, registry_row: dict, report_fn=default_report_fn,
               clock=now_gmt8) -> dict:
    """即时预算：新建浪点首次入册时预算一次，使其立即可读（R4.3 / C4）。"""
    return refresh_spots([_reg_to_cfg(registry_row)], writer,
                         report_fn=report_fn, clock=clock)


def recycle_cold_spots(store, cold_days: int = COLD_DAYS, clock=now_gmt8) -> list[str]:
    """冷浪点回收：last_viewed 超 K 天 → refresh_enabled=False（仅按需计算，R4.6 / C8）。"""
    now = clock()
    recycled = []
    for r in list(store.list_active_registry() or []):
        lv = r.get("last_viewed_at_gmt8")
        if not lv:
            continue
        try:
            seen = datetime.fromisoformat(lv)
        except ValueError:
            continue
        if (now - seen).days >= cold_days:
            store.set_refresh_enabled(r["slug"], False)
            recycled.append(r["slug"])
    return recycled
