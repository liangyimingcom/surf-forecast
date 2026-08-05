"""refresh_job 单测 —— 缓存键/GMT+8/validate失败不覆盖/含wdeg+history（D5）。"""

from datetime import datetime
from zoneinfo import ZoneInfo

from surf_forecast.validate import ReportValidationError
from web import refresh

GMT8 = ZoneInfo("Asia/Shanghai")


def _fixed_clock():
    return datetime(2026, 6, 21, 2, 0, tzinfo=GMT8)


def _fake_report(cfg, *, calibrated_at=None):
    return {
        "spot": cfg["spot"], "calibratedAt": "2026-06-21 02:00 GMT+8",
        "days": [{"date": "2026-06-21", "week": "周日", "wdeg": [337, 312], "score": 7.0}],
        "history": {"date": "2026-06-20", "wdeg": [300], "predict": {"verdict": "x"}},
        "ranking": [0],
    }


def test_refresh_writes_expected_keys():
    w = refresh.InMemoryCacheWriter()
    summary = refresh.refresh_spots(
        [{"slug": "st", "spot": "山东头", "lat": 36.092, "lon": 120.468}],
        w, report_fn=_fake_report, clock=_fixed_clock)
    assert summary["st"] == "ok"
    # 缓存键：latest + today + history/yesterday（GMT+8）
    assert "st/latest.json" in w.store
    assert "st/2026-06-21.json" in w.store
    assert "st/history/2026-06-20.json" in w.store
    # 红线：含 wdeg
    assert "wdeg" in w.store["st/latest.json"]["days"][0]


def test_refresh_validate_fail_does_not_overwrite():
    w = refresh.InMemoryCacheWriter()
    # 预置上一版
    w.put("st/latest.json", {"days": [{"score": 9.9, "wdeg": [1]}], "stale": True})

    def _raise(cfg, *, calibrated_at=None):
        raise ReportValidationError("历史与预报重叠", "history_forecast_overlap")

    summary = refresh.refresh_spots(
        [{"slug": "st", "spot": "山东头", "lat": 36.092, "lon": 120.468}],
        w, report_fn=_raise, clock=_fixed_clock)
    assert summary["st"].startswith("skipped: validate")
    # 上一版保留，未被覆盖（R5.4）
    assert w.store["st/latest.json"].get("stale") is True


def test_refresh_error_does_not_overwrite():
    w = refresh.InMemoryCacheWriter()
    w.put("st/latest.json", {"keep": True})

    def _boom(cfg, *, calibrated_at=None):
        raise RuntimeError("Open-Meteo down")

    summary = refresh.refresh_spots(
        [{"slug": "st", "spot": "山东头", "lat": 1, "lon": 1}],
        w, report_fn=_boom, clock=_fixed_clock)
    assert summary["st"].startswith("skipped: error")
    assert w.store["st/latest.json"] == {"keep": True}


# ============================================================
# R1（数据健康）：绿灯必须等于可用 —— 产出空报告不得计 ok
#
# 真实事故（2026-08-05）：sl82 Canggu 坐标正确（巴厘岛），但 WAM025 在格点
# -8.75/115.25 返回 48 时点全 null → 引擎产出 days=0 的报告；旧逻辑照写 latest.json
# 并计 ok，于是 manifest 显示 60/60 全绿，而该点在首屏完全不可用
# （只能从 coverage 的 pool 37 / fresh 36 察觉）。
# ============================================================
def _empty_report(cfg, *, calibrated_at=None):
    """上游格点全空时引擎的产物：结构完整但 days 为空。"""
    return {"spot": cfg["spot"], "calibratedAt": "2026-06-21 02:00 GMT+8",
            "days": [], "ranking": []}


def test_refresh_empty_report_not_ok():
    w = refresh.InMemoryCacheWriter()
    summary = refresh.refresh_spots(
        [{"slug": "cg", "spot": "Canggu", "lat": -8.661, "lon": 115.133}],
        w, report_fn=_empty_report, clock=_fixed_clock)
    assert summary["cg"] != "ok"                        # 不得计成功
    assert "empty_report" in summary["cg"]              # 原因机器可读
    assert "upstream" in summary["cg"]                  # 指向上游而非代码


def test_refresh_empty_report_does_not_overwrite():
    """与 validate/error 同策：不用空报告把上一版好数据冲掉（R5.4 原则）。"""
    w = refresh.InMemoryCacheWriter()
    w.put("cg/latest.json", {"days": [{"score": 8.0, "wdeg": [180]}], "prev": True})
    refresh.refresh_spots(
        [{"slug": "cg", "spot": "Canggu", "lat": -8.661, "lon": 115.133}],
        w, report_fn=_empty_report, clock=_fixed_clock)
    assert w.store["cg/latest.json"].get("prev") is True
    assert "cg/2026-06-21.json" not in w.store          # 也不写当日快照


def test_refresh_nonempty_report_still_ok():
    """另一侧边界：有 days 就照旧计 ok（护栏不得误伤正常点）。"""
    w = refresh.InMemoryCacheWriter()
    summary = refresh.refresh_spots(
        [{"slug": "st", "spot": "山东头", "lat": 36.092, "lon": 120.468}],
        w, report_fn=_fake_report, clock=_fixed_clock)
    assert summary["st"] == "ok"
    assert "st/latest.json" in w.store


def test_empty_report_lands_in_manifest_failed_with_reason():
    """端到端：空报告 → manifest.failed 带原因（/status 据此展示"为什么失败"）。"""
    summary = {"st": "ok", "cg": "skipped: empty_report(upstream grid all-null)"}
    m = refresh.build_manifest(None, "main", ["st", "cg"], summary,
                               duration_s=1.0, clock=_fixed_clock)
    assert m["succeeded"] == ["st"]
    assert "cg" in m["failed"] and "empty_report" in m["failed"]["cg"]
    assert m["ok_n"] if "ok_n" in m else True            # history 里记 ok_n
    assert m["history"][-1]["ok_n"] == 1
