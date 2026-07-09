"""validate.py 单测 —— 星期GMT+8/月相潮型/周期口径/阵风/历史互斥（Task 4.3, A2/A3/A4/A9）。"""

from datetime import date, datetime

import pytest

from surf_forecast import validate
from surf_forecast.models import (
    DailyAnalysis,
    DailyForecast,
    ForecastPoint,
    ReportContext,
    TideExtreme,
)


def _pt(t, hs=0.8, tm=5.0, tp=6.5, ws=8.0, gust=12.0):
    return ForecastPoint(
        time=t, wave_height_m=hs, wave_direction_deg=160,
        wave_period_mean_s=tm, wave_period_peak_s=tp,
        swell_height_m=0.6, wind_speed_kn=ws, wind_direction_deg=157, wind_gust_kn=gust,
    )


def _day(d, pts=None, extremes=None):
    return DailyForecast(
        date=d,
        points=pts or [_pt(datetime(d.year, d.month, d.day, 6))],
        tide_extremes=extremes or [],
    )


def _ctx(days, history=None):
    return ReportContext(
        spot="青岛山东头", lat=36.092, lon=120.468,
        calibrated_at=datetime(2026, 6, 20, 10, 0),
        days=[DailyAnalysis(forecast=d) for d in days],
        history=DailyAnalysis(forecast=history) if history else None,
    )


def test_verify_weekday_ok_and_fail():
    validate.verify_weekday(date(2026, 6, 20), "周六")  # 不抛
    with pytest.raises(validate.ReportValidationError):
        validate.verify_weekday(date(2026, 6, 20), "周三")


def test_verify_period_citation():
    p = _pt(datetime(2026, 6, 20, 6), tm=5.0, tp=6.5)
    validate.verify_period_citation(5.0, p, "Tm")
    validate.verify_period_citation(6.5, p, "Tp")
    with pytest.raises(validate.ReportValidationError):
        validate.verify_period_citation(7.0, p, "Tp")
    with pytest.raises(validate.ReportValidationError):
        validate.verify_period_citation(5.0, p, "Foo")


def test_flag_gust_anomaly():
    normal = _pt(datetime(2026, 6, 20, 6), ws=8, gust=12)   # ratio 1.5
    weird = _pt(datetime(2026, 6, 20, 6), ws=2, gust=20)    # ratio 10
    assert validate.flag_gust_anomaly(normal) is False
    assert validate.flag_gust_anomaly(weird) is True


def test_history_forecast_disjoint():
    fdates = [date(2026, 6, 20), date(2026, 6, 21)]
    validate.verify_history_forecast_disjoint(date(2026, 6, 19), fdates)  # 不抛
    with pytest.raises(validate.ReportValidationError, match="重叠"):
        validate.verify_history_forecast_disjoint(date(2026, 6, 20), fdates)


def test_validate_report_blocks_overlap():
    days = [_day(date(2026, 6, 20)), _day(date(2026, 6, 21))]
    # 历史日期与预报区重叠 → 阻断
    with pytest.raises(validate.ReportValidationError):
        validate.validate_report(_ctx(days, history=_day(date(2026, 6, 20))))


def test_validate_report_collects_warnings():
    # 阵风异常进入 warning，不阻断
    weird = _pt(datetime(2026, 6, 20, 6), ws=2, gust=20)
    days = [_day(date(2026, 6, 20), pts=[weird])]
    warns = validate.validate_report(_ctx(days, history=_day(date(2026, 6, 19))))
    assert any("阵风" in w for w in warns)


def test_is_spring_tide_anchor():
    # 锚点新月 2026-01-18 应为大潮
    assert validate.is_spring_tide(date(2026, 1, 18)) is True
