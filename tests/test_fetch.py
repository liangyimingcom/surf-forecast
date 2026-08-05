"""fetch.py 单测 —— 离线样例 JSON 验证对齐合并/GMT+8 分组/回退/中期降级/潮汐/past_days。"""

from datetime import datetime

import pytest

from surf_forecast import fetch
from surf_forecast.models import Confidence

TIMES = [
    "2026-06-20T06:00", "2026-06-20T09:00", "2026-06-20T12:00", "2026-06-21T06:00",
]
WAM = {"hourly": {
    "time": TIMES,
    "wave_height": [0.8, 0.9, 0.7, 0.5],
    "wave_direction": [160, 165, 158, 150],
    "wave_period": [5.0, 5.2, 4.8, 4.0],
    "wave_peak_period": [6.5, 6.8, 6.2, 5.0],
}}
BEST = {"hourly": {
    "time": TIMES,
    "swell_wave_height": [0.6, 0.6, 0.5, 0.3],
    "swell_wave_direction": [155, 155, 150, 150],
    "wind_wave_height": [0.3, 0.4, 0.3, 0.2],
    "sea_level_height_msl": [0.6, 0.9, 0.5, 0.4],
    "sea_surface_temperature": [21, 21, 21, 20],
}}
WIND = {
    "hourly": {
        "time": TIMES,
        "wind_speed_10m": [8, 10, 6, 7],
        "wind_direction_10m": [157, 337, 200, 160],
        "wind_gusts_10m": [12, 15, 9, 10],
    },
    "daily": {
        "time": ["2026-06-20", "2026-06-21"],
        "sunrise": ["2026-06-20T04:46", "2026-06-21T04:46"],
        "sunset": ["2026-06-20T19:26", "2026-06-21T19:26"],
    },
}


def test_merge_groups_by_gmt8_date():
    days = fetch.build_daily_forecasts(WAM, BEST, WIND)
    assert len(days) == 2
    assert str(days[0].date) == "2026-06-20" and len(days[0].points) == 3
    assert str(days[1].date) == "2026-06-21" and len(days[1].points) == 1
    assert days[0].weekday == "周六"


def test_merge_fields_and_purity():
    days = fetch.build_daily_forecasts(WAM, BEST, WIND)
    p0 = days[0].points[0]
    assert p0.wave_height_m == 0.8
    assert p0.wave_period_peak_s == 6.5
    assert p0.swell_purity == pytest.approx(75.0)   # 0.6/0.8
    assert p0.wind_speed_kn == 8 and p0.wind_direction_deg == 157
    assert p0.source == "ecmwf_wam025"
    assert days[0].sunrise == datetime(2026, 6, 20, 4, 46)


def test_wam_missing_falls_back_to_best():
    wam = {"hourly": dict(WAM["hourly"])}
    wam["hourly"] = {**WAM["hourly"], "wave_height": [None, 0.9, 0.7, 0.5]}
    best = {"hourly": {**BEST["hourly"], "wave_height": [0.85, 0.9, 0.7, 0.5]}}
    days = fetch.build_daily_forecasts(wam, best, WIND)
    p0 = days[0].points[0]
    assert p0.wave_height_m == 0.85
    assert "fallback" in p0.source


def test_midrange_downgrades_confidence():
    days = fetch.build_daily_forecasts(WAM, BEST, WIND, midrange_threshold=1)
    assert days[0].is_midrange is False
    assert days[1].is_midrange is True
    assert days[1].points[0].confidence is Confidence.LOW


def test_extract_tide_extremes():
    times = [datetime(2026, 6, 20, h) for h in (6, 9, 12)]
    ext = fetch.extract_tide_extremes([0.6, 0.9, 0.5], times)
    assert len(ext) == 1 and ext[0].kind == "high" and ext[0].level_m == 0.9
    ext2 = fetch.extract_tide_extremes([0.9, 0.4, 0.8], times)
    assert ext2[0].kind == "low"


def test_build_marine_params_past_days():
    p = fetch._build_marine_params(36.092, 120.468, 6, 1, ["wave_height"], model="ecmwf_wam025")
    assert p["past_days"] == 1 and p["timezone"] == "Asia/Shanghai"
    assert p["models"] == "ecmwf_wam025" and p["forecast_days"] == 6


class _FakeResp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._p


class _FakeClient:
    """按请求的 hourly 字段判定返回哪路样例，验证 fetch_forecast 编排不触网。"""

    def get(self, url, params):
        hourly = params.get("hourly", "")
        if "swell_wave_height" in hourly:
            return _FakeResp(BEST)
        if "wave_height" in hourly:
            return _FakeResp(WAM)
        return _FakeResp(WIND)


def test_fetch_forecast_orchestration_offline():
    days = fetch.fetch_forecast(36.092, 120.468, 6, client=_FakeClient())
    assert len(days) == 2
    assert days[0].points[0].wave_height_m == 0.8
    assert days[0].sunrise == datetime(2026, 6, 20, 4, 46)


def test_get_raises_on_empty_field():
    class Empty:
        def get(self, url, params):
            return _FakeResp({"hourly": {"time": [], "wave_height": []}})
    with pytest.raises(fetch.DataSourceError):
        fetch.fetch_forecast(36.092, 120.468, 6, client=Empty())


# ============================================================
# 2026-08-05：WAM→best_match 回退是**死代码**的修复回归
#
# 需求 1.5 写着「总浪高优先 WAM，缺则回退 best_match」，代码里也有该分支，
# 但 best 请求的 hourly 里从来没要 wave_height/direction/period
# → `_at(best_h, "wave_height", bi)` 恒为 None → 回退永不触发。
# 受害者 sl82 Canggu：WAM025 在格点 -8.75/115.25 返回 48 时点全 null，
# 而 best_match 在 -8.625/115.125（更贴近实际位置）有完整数据（1.36m / 12.9s），
# 本可救回却产出 days=0 的空报告，还把 manifest 撑成"60/60 全绿"。
# ============================================================
WAM_EMPTY = {"hourly": {
    "time": TIMES,
    "wave_height": [None, None, None, None],
    "wave_direction": [None, None, None, None],
    "wave_period": [None, None, None, None],
    "wave_peak_period": [None, None, None, None],
}}
BEST_WITH_WAVES = {"hourly": dict(BEST["hourly"], **{
    "wave_height": [1.36, 1.36, 1.30, 1.20],
    "wave_direction": [200, 200, 205, 210],
    "wave_period": [12.9, 12.95, 12.5, 12.0],
})}


def test_best_match_request_asks_for_fallback_fields():
    """请求层回归：不要这三个字段，回退分支就是死代码（本次 bug 的根因）。"""
    p = fetch._build_marine_params(
        1.0, 2.0, 6, 0,
        ["wave_height", "wave_direction", "wave_period",
         "swell_wave_height", "swell_wave_direction", "wind_wave_height",
         "sea_level_height_msl", "sea_surface_temperature"])
    for f in ("wave_height", "wave_direction", "wave_period"):
        assert f in p["hourly"], f
    assert "models" not in p           # best_match 不带 models 参数


def test_wam_all_null_falls_back_to_best_match():
    days = fetch.build_daily_forecasts(WAM_EMPTY, BEST_WITH_WAVES, WIND)
    assert days, "WAM 全空但 best_match 有数据时不应产出空报告"
    pts = [p for d in days for p in d.points]
    assert pts and all(p.source == "best_match(fallback)" for p in pts)
    assert pts[0].wave_height_m == 1.36          # 用的是 best_match 的值
    assert pts[0].wave_period_mean_s == 12.9
    assert pts[0].wave_period_peak_s is None     # Tp 仅 WAM 有，回退时留空不编造


def test_both_sources_empty_still_yields_no_points():
    """两个源都无浪高 → 仍然产不出点（此时才是真正的"上游无数据"）。
    R1 的 days>0 判定会把它计入 failed，而不是伪装成 60/60 全绿。"""
    best_no_waves = {"hourly": dict(BEST["hourly"])}   # 不含 wave_height
    assert fetch.build_daily_forecasts(WAM_EMPTY, best_no_waves, WIND) == []


def test_wam_present_keeps_primary_source():
    """另一侧边界：WAM 有数据时不得被 best_match 顶替（WAM 是主源）。"""
    days = fetch.build_daily_forecasts(WAM, BEST_WITH_WAVES, WIND)
    pts = [p for d in days for p in d.points]
    assert all(p.source == "ecmwf_wam025" for p in pts)
    assert pts[0].wave_height_m == 0.8            # WAM 的值，不是 best 的 1.36
