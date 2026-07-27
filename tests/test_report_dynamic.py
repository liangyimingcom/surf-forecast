"""P1.2 报告动态化单测：checklist/disclaimer 去硬编码 + 大浪边界双侧钉死 + 动态 SST。"""
from datetime import date, datetime
from types import SimpleNamespace as NS

from surf_forecast import analyze, render
from surf_forecast.models import DailyForecast, ForecastPoint, TideExtreme


def _pt(h, d, hs=0.8, sst=0.0):
    return ForecastPoint(
        time=datetime(d.year, d.month, d.day, h), wave_height_m=hs, wave_direction_deg=160,
        wave_period_mean_s=5.0, wave_period_peak_s=6.5, swell_height_m=0.6,
        wind_speed_kn=8, wind_direction_deg=337, wind_gust_kn=11, sea_level_m=0.6, sst_c=sst)


def _day(d, hs=0.8, sst=0.0):
    return DailyForecast(
        date=d, points=[_pt(h, d, hs, sst) for h in (6, 9, 12)],
        tide_extremes=[TideExtreme(time=datetime(d.year, d.month, d.day, 9), level_m=0.9, kind="high")],
        sunrise=datetime(d.year, d.month, d.day, 4), sunset=datetime(d.year, d.month, d.day, 20))


def _ctx(hs=0.8, sst=22.0):
    return analyze.build_context(
        36.092, 120.468, 2, "青岛山东头",
        forecasts=[_day(date(2026, 6, 20), hs, sst), _day(date(2026, 6, 21), hs, sst)],
        calibrated_at=datetime(2026, 6, 20, 10, 0))


# —— render_json 输出含动态字段且无硬编码泄漏 ——
def test_render_json_has_dynamic_fields_no_hardcode():
    r = render.render_json(_ctx())
    assert isinstance(r["checklist"], list) and r["checklist"]
    assert isinstance(r["disclaimer"], str) and r["disclaimer"]
    blob = " ".join(r["checklist"]) + r["disclaimer"]
    assert "青岛" not in blob and "王者" not in blob and "22.6" not in blob  # 去硬编码地名/日期/水温值


def test_checklist_always_has_generic_tide_note():
    r = render.render_json(_ctx())
    assert any("官方潮汐表" in x for x in r["checklist"])


# —— 大浪核对项：边界双侧钉死（mutation：> 改 >= 或阈值±0.1 应变红）——
def test_bigwave_item_absent_at_threshold():
    ck = render._checklist(NS(days=[NS(forecast=_day(date(2026, 6, 20), hs=1.0))]))
    assert not any("大浪日" in x for x in ck)          # hs==1.0 不触发


def test_bigwave_item_present_above_threshold():
    ck = render._checklist(NS(days=[NS(forecast=_day(date(2026, 6, 20), hs=1.01))]))
    assert any("大浪日" in x for x in ck)               # hs>1.0 触发


# —— 免责水温动态：有 SST 则出范围，无则不编造 ——
def test_disclaimer_dynamic_sst_present():
    dc = render._disclaimer(NS(days=[NS(forecast=_day(date(2026, 6, 20), sst=23.4))]))
    assert "23.4" in dc


def test_disclaimer_no_sst_no_fabricated_temp():
    dc = render._disclaimer(NS(days=[NS(forecast=_day(date(2026, 6, 20), sst=0.0))]))
    assert "水温" not in dc                            # 无 SST 不编造温度
    assert "GMT+8" in dc and "Open-Meteo" in dc        # 通用口径仍在
