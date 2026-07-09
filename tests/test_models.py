"""models.py 单测 —— 计算属性、weekday GMT+8 派生只读、wind_kind 枚举映射（Task 1.1）。"""

from datetime import date, datetime

import pytest

from surf_forecast.models import (
    Confidence,
    DailyForecast,
    ForecastPoint,
    WindKind,
)


def _point(**kw) -> ForecastPoint:
    base = dict(
        time=datetime(2026, 6, 20, 6, 0),
        wave_height_m=0.8,
        wave_direction_deg=160,
        wave_period_mean_s=5.0,
        swell_height_m=0.6,
        wind_speed_kn=8.0,
        wind_direction_deg=157,
        wind_gust_kn=12.0,
    )
    base.update(kw)
    return ForecastPoint(**base)


def test_swell_purity_computed():
    p = _point(wave_height_m=0.8, swell_height_m=0.6)
    assert p.swell_purity == pytest.approx(75.0)


def test_gust_ratio_computed():
    p = _point(wind_speed_kn=8.0, wind_gust_kn=12.0)
    assert p.gust_ratio == pytest.approx(1.5)
    assert _point(wind_speed_kn=0.0).gust_ratio == 0.0


def test_wind_kind_mapping():
    # 浪点朝 SSE(157)
    assert _point(wind_direction_deg=157).wind_kind(157) is WindKind.ONSHORE
    assert _point(wind_direction_deg=337).wind_kind(157) is WindKind.OFFSHORE
    assert _point(wind_direction_deg=67).wind_kind(157) is WindKind.CROSS


def test_weekday_derived_gmt8():
    # 2026-06-20 是周六
    d = DailyForecast(date=date(2026, 6, 20))
    assert d.weekday == "周六"


def test_weekday_readonly():
    # weekday 是 computed_field，不可外部赋值（需求 2.1 禁手填）
    with pytest.raises((ValueError, AttributeError, TypeError)):
        DailyForecast(date=date(2026, 6, 20), weekday="周三")


def test_confidence_default_high():
    assert _point().confidence is Confidence.HIGH
