# -*- coding: utf-8 -*-
"""W1 契约校验器单测：真实 render_json 过校验 + 各红线违规双侧钉死。"""
import copy
import importlib.util
import os
from datetime import date, datetime

from surf_forecast import analyze, render
from surf_forecast.models import DailyForecast, ForecastPoint, TideExtreme

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "validate_report", os.path.join(_ROOT, "tools", "validate_report.py"))
vr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vr)


def _pt(h, d):
    return ForecastPoint(
        time=datetime(d.year, d.month, d.day, h), wave_height_m=0.8, wave_direction_deg=160,
        wave_period_mean_s=5.0, wave_period_peak_s=6.5, swell_height_m=0.6,
        wind_speed_kn=8, wind_direction_deg=337, wind_gust_kn=11, sea_level_m=0.6)


def _day(d):
    return DailyForecast(
        date=d, points=[_pt(h, d) for h in (6, 9, 12)],
        tide_extremes=[TideExtreme(time=datetime(d.year, d.month, d.day, 9), level_m=0.9, kind="high")],
        sunrise=datetime(d.year, d.month, d.day, 4), sunset=datetime(d.year, d.month, d.day, 20))


def _real_report():
    ctx = analyze.build_context(36.092, 120.468, 2, "青岛山东头",
                                forecasts=[_day(date(2026, 6, 20)), _day(date(2026, 6, 21))],
                                calibrated_at=datetime(2026, 6, 20, 10, 0))
    return render.render_json(ctx)


# —— 正向：真实 render_json 合乎契约 ——
def test_real_render_json_passes():
    assert vr.validate_report(_real_report()) == []


# —— 红线违规：每条应被拒（负向）——
def test_reject_missing_wdeg():
    r = _real_report(); del r["days"][0]["wdeg"]
    assert any("wdeg" in e for e in vr.validate_report(r))

def test_reject_string_in_hs():
    r = _real_report(); r["days"][0]["hs"][0] = "x"
    assert any("hs" in e for e in vr.validate_report(r))

def test_reject_wdeg_length_mismatch():
    r = _real_report(); r["days"][0]["wdeg"] = r["days"][0]["wdeg"][:-1]
    assert any("wdeg" in e and "长度" in e for e in vr.validate_report(r))

def test_reject_calib_without_gmt8():
    r = _real_report(); r["calibratedAt"] = "2026-06-20 10:00"
    assert any("GMT+8" in e for e in vr.validate_report(r))

def test_reject_empty_days():
    r = _real_report(); r["days"] = []
    assert any("days" in e for e in vr.validate_report(r))

def test_reject_bad_tideevents():
    r = _real_report(); r["days"][0]["tideEvents"] = [[9.0]]  # 非 [小时,潮位] 对
    assert any("tideEvents" in e for e in vr.validate_report(r))

def test_best_count_boundary():
    # 恰好 1 个 best：0 个 → 拒；1 个 → 过（边界双侧）
    r = _real_report()
    for d in r["days"]:
        d["best"] = False
    assert any("best" in e for e in vr.validate_report(r))
    r["days"][0]["best"] = True
    assert vr.validate_report(r) == []

def test_reject_history_overlap():
    r = _real_report()
    d0 = copy.deepcopy(r["days"][0]); d0["predict"] = {"height": "0.8m"}
    r["history"] = d0  # date 与 days[0] 相同 → 违互斥红线
    assert any("重叠" in e for e in vr.validate_report(r))

def test_history_null_ok():
    r = _real_report(); r["history"] = None
    assert vr.validate_report(r) == []
