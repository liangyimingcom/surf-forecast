"""verify_narrative_support 单测 —— 虚构物理叙事拦截（Task 4.3, A5）。

v1 教训：把『先行波/频散上升』安在周期最低谷那天。叙事须有当日数据支撑。
"""

from datetime import datetime

from surf_forecast import validate
from surf_forecast.models import DailyForecast, ForecastPoint


def _pts(periods, hs=0.8):
    return [
        ForecastPoint(
            time=datetime(2026, 6, 20, 6 + 3 * i),
            wave_height_m=hs, wave_direction_deg=160,
            wave_period_mean_s=p, wave_period_peak_s=p + 1.0,
            swell_height_m=0.6, wind_speed_kn=8, wind_direction_deg=157, wind_gust_kn=12,
        )
        for i, p in enumerate(periods)
    ]


def _day(periods, hs=0.8):
    from datetime import date
    return DailyForecast(date=date(2026, 6, 20), points=_pts(periods, hs))


def test_dispersion_supported_when_rising():
    # 周期持续上升 → 频散叙事成立
    assert validate.verify_narrative_support("dispersion", _day([3.2, 3.4, 3.7, 4.05])) is True


def test_dispersion_rejected_when_falling():
    # 周期下降 → 不可声称频散（v1 反面教材）
    assert validate.verify_narrative_support("dispersion", _day([4.4, 4.0, 3.1, 2.75])) is False


def test_forerunner_supported_small_waves_long_period():
    # 浪小(0.3)周期长(>=6) → 先行波侦察兵成立
    assert validate.verify_narrative_support("forerunner", _day([5.5, 5.6, 5.7], hs=0.3)) is True


def test_forerunner_rejected_when_big_waves():
    # 浪已经很大 → 不是先行波
    assert validate.verify_narrative_support("forerunner", _day([5.5, 5.6, 5.7], hs=1.2)) is False


def test_unknown_claim_passes():
    assert validate.verify_narrative_support("whatever", _day([5.0, 5.1])) is True
