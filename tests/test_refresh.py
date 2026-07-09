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
