"""编排层 —— 见 design.md 第 8 节、requirements 3.x/4.5、Task 5.x.

fetch → DailyForecast[] → 逐日评分 → 短板/最佳窗口/板型 → DailyAnalysis[]
      → 排名 → 生命周期数据 → ReportContext。
仅白天(sunrise~sunset)时段纳入评分（需求 3.3）。计算/叙事分离：本层只产结构化数据。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from . import fetch, physics, scoring, validate
from .models import DailyAnalysis, DailyForecast, ParamScore, ReportContext, WindKind

_WEAKEST_CN = {
    "wave_height": "浪高", "period": "周期", "wind": "风况",
    "purity": "涌浪纯度", "tide": "潮汐",
}


def _daytime_points(df: DailyForecast) -> list:
    """筛选白天时段（sunrise~sunset）；无日出日落信息则返回全部（需求 3.3）。"""
    if df.sunrise and df.sunset:
        return [p for p in df.points if df.sunrise <= p.time <= df.sunset]
    return list(df.points)


def _score_point(p, thresholds) -> dict[str, ParamScore]:
    return {
        "wave_height": scoring.score_wave_height(p.wave_height_m, thresholds),
        "period": scoring.score_period(p.wave_period_mean_s, thresholds,
                                       peak_s=p.wave_period_peak_s),
        "wind": scoring.score_wind(p.wind_speed_kn, p.wind_direction_deg, thresholds),
        "purity": scoring.score_purity(p.swell_purity, thresholds),
        "tide": scoring.score_tide(p.sea_level_m, thresholds),
    }


def _board(hs: float, period_s: float) -> str:
    if hs < 0.5 or period_s < 5.0:
        return "9'+ 长板 / 泡沫板"
    if hs < 0.8:
        return "鱼板 / 7'0 中长板"
    return "短板 / step-up"


def analyze_day(daily_forecast: DailyForecast, thresholds: dict) -> DailyAnalysis:
    """对单日白天时段评分，产出 DailyAnalysis（含短板、最佳窗口、板型、晨风）。"""
    facing = float(thresholds["wind"]["spot_facing_deg"])
    pts = _daytime_points(daily_forecast)
    if not pts:
        return DailyAnalysis(
            forecast=daily_forecast, composite=0.0,
            recommendation="无白天可冲时段数据", weakest_param="",
        )

    weights = thresholds["weights"]
    scored = [(p, _score_point(p, thresholds)) for p in pts]
    # 每时段综合分，取最高者为当日代表窗口
    best_p, best_scores = max(
        scored, key=lambda ps: scoring.composite_score(ps[1], weights))
    composite = scoring.composite_score(best_scores, weights)
    weak = scoring.weakest(best_scores)

    window = f"{best_p.time:%H:%M}-{(best_p.time + timedelta(hours=3)):%H:%M}"
    board = _board(best_p.wave_height_m, best_p.wave_period_peak_s
                   or best_p.wave_period_mean_s)
    dawn_kind = WindKind(physics.wind_kind(pts[0].wind_direction_deg, facing))

    weak_cn = _WEAKEST_CN.get(weak, weak)
    rec = (f"综合 {composite}/10，最佳窗口 {window}，建议 {board}；"
           f"上限受『{weak_cn}』封顶")

    notes: list[str] = []
    if daily_forecast.is_midrange:
        notes.append("中期预报，浪高可信度 ±30%")

    return DailyAnalysis(
        forecast=daily_forecast,
        scores=best_scores,
        composite=composite,
        weakest_param=weak,
        best_window=window,
        board=board,
        recommendation=rec,
        dawn_wind_kind=dawn_kind,
        confidence_notes=notes,
    )


def build_lifecycle(daily_analyses: list[DailyAnalysis]) -> list[dict]:
    """从各日浪高/周期/综合分序列构造涌浪事件生命周期数据（需求 5.3）。"""
    lc: list[dict] = []
    for da in daily_analyses:
        pts = da.forecast.points
        hs = max((p.wave_height_m for p in pts), default=0.0)
        tp = max((p.wave_period_peak_s or p.wave_period_mean_s for p in pts), default=0.0)
        lc.append({
            "date": da.forecast.date.isoformat(),
            "week": da.forecast.weekday,
            "score": da.composite,
            "hs": round(hs, 2),
            "period": round(tp, 1),
        })
    return lc


def build_context(lat: float, lon: float, days: int, spot: str,
                  config_path: str = "config/thresholds.yaml",
                  *, forecasts: list[DailyForecast] | None = None,
                  client=None, calibrated_at: datetime | None = None,
                  include_history: bool = False,
                  history_forecasts: list[DailyForecast] | None = None) -> ReportContext:
    """完整编排，返回 ReportContext（写出前必过 validate，需求红线）。

    forecasts 可注入（测试/离线）；否则调用 fetch_forecast 取数。
    include_history=True 时附带昨日回看（past_days=1，GMT+8 today−1），供回看校验。
    """
    thresholds = scoring.load_thresholds(config_path)
    facing = float(thresholds["wind"]["spot_facing_deg"])

    if forecasts is None:
        forecasts = fetch.fetch_forecast(lat, lon, days, client=client)

    analyses = [analyze_day(df, thresholds) for df in forecasts]
    ranking = scoring.rank_days(analyses)
    lifecycle = build_lifecycle(analyses)

    cal = calibrated_at or datetime.now()
    ctx = ReportContext(
        spot=spot, lat=lat, lon=lon, spot_facing_deg=facing,
        calibrated_at=cal,
        days=analyses, ranking=ranking, lifecycle=lifecycle,
    )

    # 昨日回看（GMT+8 today−1）：与预报同管线，仅 past_days 不同（ADR-7）
    if include_history:
        yday = cal.date() - timedelta(days=1)
        past = history_forecasts
        if past is None:
            past = fetch.fetch_forecast(lat, lon, 1, past_days=1, client=client)
        yd = next((d for d in past if d.date == yday), None)
        if yd is not None:
            ctx.history = analyze_day(yd, thresholds)

    # 红线：渲染前必过 validate（含历史/预报日期互斥）；ERROR 抛出，WARNING 进声明
    ctx.warnings = validate.validate_report(ctx)
    return ctx
