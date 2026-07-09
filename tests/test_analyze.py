"""analyze.py 单测 —— 白天过滤/评分聚合/短板/窗口/板型/排名/生命周期/编排（Task 5.x）。"""

from datetime import date, datetime

from surf_forecast import analyze, scoring
from surf_forecast.models import DailyForecast, ForecastPoint, WindKind

CFG = scoring.load_thresholds("config/thresholds.yaml")


def _pt(h, hs=0.8, tm=5.0, tp=6.5, ws=8.0, wdir=337, swell=0.6, level=0.6,
        d=date(2026, 6, 20)):
    return ForecastPoint(
        time=datetime(d.year, d.month, d.day, h), wave_height_m=hs, wave_direction_deg=160,
        wave_period_mean_s=tm, wave_period_peak_s=tp, swell_height_m=swell,
        wind_speed_kn=ws, wind_direction_deg=wdir, wind_gust_kn=ws * 1.4, sea_level_m=level,
    )


def _day(d, pts, sr=4, ss=20):
    return DailyForecast(
        date=d, points=pts,
        sunrise=datetime(d.year, d.month, d.day, sr),
        sunset=datetime(d.year, d.month, d.day, ss),
    )


def test_daytime_filter_excludes_night():
    pts = [_pt(2), _pt(6), _pt(12), _pt(22)]  # 2 点和 22 点是夜间
    df = _day(date(2026, 6, 20), pts)
    day_pts = analyze._daytime_points(df)
    assert all(6 <= p.time.hour <= 20 for p in day_pts)
    assert len(day_pts) == 2


def test_analyze_day_picks_best_window_and_weakest():
    # 两个白天时段：09 点纯度低(短板)，12 点全面更好
    low_purity = _pt(9, hs=0.8, swell=0.3)   # purity 37.5 → 差
    good = _pt(12, hs=0.9, tp=6.5, swell=0.85)  # purity ~94
    df = _day(date(2026, 6, 20), [low_purity, good])
    da = analyze.analyze_day(df, CFG)
    assert da.best_window.startswith("12:00")
    assert da.composite > 0
    assert da.dawn_wind_kind is WindKind.OFFSHORE  # wdir 337 对 157 为离岸
    assert da.board  # 非空板型
    assert "封顶" in da.recommendation


def test_analyze_day_no_daytime_points():
    df = DailyForecast(date=date(2026, 6, 20), points=[_pt(2)],
                       sunrise=datetime(2026, 6, 20, 4),
                       sunset=datetime(2026, 6, 20, 20))
    # 仅 2 点夜间 → 无白天数据
    df.points = [_pt(2)]
    da = analyze.analyze_day(df, CFG)
    assert da.composite == 0.0 and "无白天" in da.recommendation


def test_build_context_offline_ranking_and_lifecycle():
    d1 = _day(date(2026, 6, 20), [_pt(9, hs=0.5, swell=0.3, tp=4.5)])   # 弱
    d2 = _day(date(2026, 6, 21),
              [_pt(9, hs=1.0, swell=0.9, tp=6.8, d=date(2026, 6, 21))])  # 强
    ctx = analyze.build_context(
        36.092, 120.468, 2, "青岛山东头",
        forecasts=[d1, d2], calibrated_at=datetime(2026, 6, 20, 10, 0))
    assert len(ctx.days) == 2
    assert ctx.ranking[0] == 1            # 第二天综合分更高，排第一
    assert len(ctx.lifecycle) == 2
    assert ctx.lifecycle[1]["week"] == "周日"
    assert ctx.spot_facing_deg == 157


def test_build_context_runs_validate():
    # 正常两日不重叠 → 无 ERROR，warnings 为 list
    d1 = _day(date(2026, 6, 20), [_pt(9)])
    d2 = _day(date(2026, 6, 21), [_pt(9, d=date(2026, 6, 21))])
    ctx = analyze.build_context(36.092, 120.468, 2, "青岛山东头",
                                forecasts=[d1, d2],
                                calibrated_at=datetime(2026, 6, 20, 10, 0))
    assert isinstance(ctx.warnings, list)
