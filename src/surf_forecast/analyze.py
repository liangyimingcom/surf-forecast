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


def _score_point(p, thresholds, facing: float | None = None) -> dict[str, ParamScore]:
    return {
        "wave_height": scoring.score_wave_height(p.wave_height_m, thresholds),
        "period": scoring.score_period(p.wave_period_mean_s, thresholds,
                                       peak_s=p.wave_period_peak_s),
        "wind": scoring.score_wind(p.wind_speed_kn, p.wind_direction_deg, thresholds,
                                   facing=facing),
        "purity": scoring.score_purity(p.swell_purity, thresholds),
        "tide": scoring.score_tide(p.sea_level_m, thresholds),
    }


def _board(hs: float, period_s: float) -> str:
    if hs < 0.5 or period_s < 5.0:
        return "9'+ 长板 / 泡沫板"
    if hs < 0.8:
        return "鱼板 / 7'0 中长板"
    return "短板 / step-up"


def resolve_facing(thresholds: dict, facing_deg: float | None = None,
                   facing_calibrated: bool = False) -> float:
    """决定本次分析用哪个浪点朝向。**唯一**的取值口径，别处不要再各自判断。

    离岸/向岸是产品的一等参数（domain-knowledge 三），所以这个取值必须可解释：

    - `facing_calibrated=True` → 用传入的逐点 `facing_deg`（实测/权威校准过的值）。
    - 否则 → 用 `thresholds.wind.spot_facing_deg`（全站口径），**不用**注册表里的未校准值。

    为什么不无条件采用注册表的逐点值：那些值来自 `tools/import_shilaoren_spots.py`
    的 `guess_facing(city)`，按 city 英文名查表，而 **41/58 个点的 city 没匹配上**，
    全部落到 `return 135` 兜底 —— 横跨 8 个地区，连巴厘岛 Canggu（实际朝西南）
    和黄金海岸 Kirra（实际朝东）都是 135。换用它等于把一个任意的全国常量
    换成另一个任意的近全国常量，还会静默改动 58 个点的风向判定，不是精度提升。
    所以：**管路打通、开关留给校准**。校准一个点，那个点立刻生效，无需改代码。
    """
    if facing_calibrated and isinstance(facing_deg, (int, float)):
        return float(facing_deg)
    return float(thresholds["wind"]["spot_facing_deg"])


def analyze_day(daily_forecast: DailyForecast, thresholds: dict,
                facing: float | None = None) -> DailyAnalysis:
    """对单日白天时段评分，产出 DailyAnalysis（含短板、最佳窗口、板型、晨风）。

    facing 为 None 时取 thresholds 里的全站口径（保持既有行为）。
    """
    if facing is None:
        facing = float(thresholds["wind"]["spot_facing_deg"])
    pts = _daytime_points(daily_forecast)
    if not pts:
        return DailyAnalysis(
            forecast=daily_forecast, composite=0.0,
            recommendation="无白天可冲时段数据", weakest_param="",
        )

    weights = thresholds["weights"]
    scored = [(p, _score_point(p, thresholds, facing=facing)) for p in pts]
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
                  history_forecasts: list[DailyForecast] | None = None,
                  facing_deg: float | None = None,
                  facing_calibrated: bool = False) -> ReportContext:
    """完整编排，返回 ReportContext（写出前必过 validate，需求红线）。

    forecasts 可注入（测试/离线）；否则调用 fetch_forecast 取数。
    include_history=True 时附带昨日回看（past_days=1，GMT+8 today−1），供回看校验。
    """
    thresholds = scoring.load_thresholds(config_path)
    facing = resolve_facing(thresholds, facing_deg, facing_calibrated)

    if forecasts is None:
        forecasts = fetch.fetch_forecast(lat, lon, days, client=client)

    analyses = [analyze_day(df, thresholds, facing=facing) for df in forecasts]
    ranking = scoring.rank_days(analyses)
    lifecycle = build_lifecycle(analyses)

    cal = calibrated_at or datetime.now()
    ctx = ReportContext(
        spot=spot, lat=lat, lon=lon, spot_facing_deg=facing,
        facing_calibrated=bool(facing_calibrated and isinstance(facing_deg, (int, float))),
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
            # 昨日回看必须与预报同一个 facing，否则回看的风质判定与预报口径分叉
            ctx.history = analyze_day(yd, thresholds, facing=facing)

    # 红线：渲染前必过 validate（含历史/预报日期互斥）；ERROR 抛出，WARNING 进声明
    ctx.warnings = validate.validate_report(ctx)
    return ctx
