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
    # 逐点朝向：把注册表的值与**校准标记**一起传给引擎。
    # 未校准时 analyze.resolve_facing 会忽略该值、退回全站口径 —— 所以这里传值是
    # 无害的，且把「校准一个点即刻生效」这条路打通（详见 resolve_facing 的说明）。
    ctx = analyze.build_context(
        spot_cfg["lat"], spot_cfg["lon"], spot_cfg.get("days", 6), spot_cfg["spot"],
        include_history=True, calibrated_at=calibrated_at,
        facing_deg=spot_cfg.get("spot_facing_deg"),
        facing_calibrated=bool(spot_cfg.get("facing_calibrated", False)),
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

        # R1（数据健康）：产出空报告 = 上游格点无浪场数据（如 WAM025 在近陆格点返回全 null）。
        # 旧行为照写 latest.json 且计 ok → manifest 显示 60/60 全绿而该点实际不可用
        # （2026-08-05 实例：sl82 Canggu 坐标正确，格点 -8.75/115.25 返回 48 时点全空）。
        # 与 validate 失败同策：跳过、**不覆盖上一版缓存**、记可读原因，让绿灯等于可用。
        if not (report.get("days") or []):
            logger.error("refresh %s 产出空报告(days=0)，保留上一版：上游格点疑无浪场数据", slug)
            summary[slug] = "skipped: empty_report(upstream grid all-null)"
            continue

        writer.put(f"{slug}/latest.json", report)
        writer.put(f"{slug}/{today}.json", report)
        if report.get("history"):
            writer.put(f"{slug}/history/{yesterday}.json", report["history"])
        summary[slug] = "ok"

    return summary


def bulk_latest(reader, slugs, max_workers: int = 12) -> dict:
    """并发读多点 {slug}/latest.json（提速：61 点串行 S3 ~2.5s → 并发 ~0.3s）。
    boto3 client 线程安全；单点异常吞掉返回 None（与串行语义一致）。"""
    out: dict = {}
    if reader is None or not slugs:
        return out
    import concurrent.futures

    def _get(slug):
        try:
            return slug, reader.get(f"{slug}/latest.json")
        except Exception:  # noqa: BLE001
            return slug, None

    with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(max_workers, max(1, len(slugs)))) as ex:
        for slug, rep in ex.map(_get, slugs):
            out[slug] = rep
    return out


# —— R2 决策9/10：刷新运行 manifest（一致性契约 + /status 数据源 + 补跑缺失点识别）——

MANIFEST_KEY = "manifest.json"
MANIFEST_HISTORY_MAX = 14  # /status 展示最近 7 天（主跑+补跑各一条）


def load_manifest(reader) -> dict | None:
    """读当前 manifest；无桶/无文件/坏 JSON → None（消费者自行降级）。"""
    if reader is None:
        return None
    try:
        return reader.get(MANIFEST_KEY)
    except Exception:  # noqa: BLE001
        return None


def build_manifest(prev: dict | None, kind: str, expected: list[str],
                   summary: dict, duration_s: float, clock=now_gmt8) -> dict:
    """构造新 manifest。retry 且同日 → succeeded 与主跑合并（哨兵语义：补齐而非替换）。

    失败点记原因（expected 内非 ok 的）；history 滚动保留最近 N 条摘要。
    """
    now = clock()
    date = now.date().isoformat()
    run_at = now.strftime("%Y-%m-%d %H:%M GMT+8")
    ok = [s for s, v in summary.items() if v == "ok"]
    succeeded = sorted(set(ok))
    if kind == "retry" and prev and prev.get("date") == date:
        succeeded = sorted(set(prev.get("succeeded") or []) | set(ok))
        expected = list(prev.get("expected") or expected)
    failed = {s: summary[s] for s in expected if s in summary and summary[s] != "ok"}
    history = list((prev or {}).get("history") or [])
    history.append({
        "run_id": f"{date}-{kind}", "run_at": run_at, "kind": kind,
        "expected_n": len(expected), "ok_n": len(ok), "duration_s": round(duration_s, 1),
    })
    history = history[-MANIFEST_HISTORY_MAX:]
    return {
        "run_id": f"{date}-{kind}", "run_at": run_at, "date": date, "kind": kind,
        "expected": sorted(expected), "succeeded": succeeded, "failed": failed,
        "duration_s": round(duration_s, 1), "history": history,
    }


def missing_from_manifest(manifest: dict | None, today: str) -> list[str] | None:
    """补跑输入：今日 manifest 的 expected − succeeded。
    无 manifest 或非今日（主跑没跑/挂了=断链）→ None，调用方退化为全量（哨兵兜底）。"""
    if not manifest or manifest.get("date") != today:
        return None
    return sorted(set(manifest.get("expected") or []) - set(manifest.get("succeeded") or []))


# —— R4 动态刷新编排（注册表驱动，替代硬编码 DEFAULT_SPOTS）——

REFRESH_BUDGET = 80   # 每次调度预算上限 N。须 ≥ 上架目录规模(现58)否则按last_viewed降序截断→无view的demo点被饿死、
                      # 首屏 recommend 覆盖缺口(R0.2 教训)。80=58+成长冗余；冷点回收仍由 recycle_cold_spots 独立管。
COLD_DAYS = 14        # last_viewed 超 K 天 → 暂停定时刷新（仅对"曾被查看后转冷"的点；无view的demo点被 skip 不回收）


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
        # 豁免 seeded 基线目录(source!="user")：Fable5 §1.1 首屏需全目录每日刷新，基线点永不冷回收；
        # 仅回收用户自建(source=="user")的冷点。防冷点炸弹撤销基线 refresh_enabled(v0.2.1 修复)。
        if r.get("source") != "user":
            continue
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
