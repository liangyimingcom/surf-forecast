"""事实自检关 —— 见 design.md 第 6 节、requirements 2.x、Task 4.x.

这是 v1 血泪教训的自动化执行点（domain-knowledge.md 第七节）。
任何 ERROR 抛 ReportValidationError 阻断报告输出；WARNING 进入可信度声明。
"""

from __future__ import annotations

from datetime import date

from . import physics

# 月相锚点：已知新月（朔），用于推算潮型
KNOWN_NEW_MOON = date(2026, 1, 18)
SYNODIC_MONTH = 29.5306  # 朔望月天数

_WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class ReportValidationError(Exception):
    """阻断级校验失败（事实红线）。"""

    def __init__(self, message: str, field: str = ""):
        super().__init__(message)
        self.field = field


def moon_age(d: date) -> float:
    """返回月龄（天，0=新月，~14.77=满月）。"""
    return (d - KNOWN_NEW_MOON).days % SYNODIC_MONTH


def is_spring_tide(d: date, tol: float = 2.0) -> bool:
    """新月或满月 ±tol 天内为大潮（需求 2.2）。"""
    age = moon_age(d)
    return age < tol or abs(age - SYNODIC_MONTH) < tol or abs(age - SYNODIC_MONTH / 2) < tol


def expected_weekday(d: date) -> str:
    """由 GMT+8 日期派生的中文星期（单一真源）。"""
    return _WEEKDAY_CN[d.weekday()]


def verify_weekday(d: date, claimed_weekday: str) -> None:
    """星期必须由日期计算（需求 2.1）。不一致抛 ReportValidationError。"""
    exp = expected_weekday(d)
    if claimed_weekday and claimed_weekday != exp:
        raise ReportValidationError(
            f"星期不符：{d} 应为 {exp}，却标注 {claimed_weekday}", "weekday")


def tide_range(daily_forecast) -> float:
    """当日潮差（最高潮位 - 最低潮位），无极值时用 points 海面高度兜底。"""
    levels = [e.level_m for e in daily_forecast.tide_extremes]
    if not levels:
        levels = [p.sea_level_m for p in daily_forecast.points]
    if not levels:
        return 0.0
    return max(levels) - min(levels)


def verify_tide_vs_moon(daily_forecast) -> list[str]:
    """潮型与月相自洽、潮差量级符合海域，否则返回 Warning 列表（需求 2.2）。

    黄海：大潮潮差 3-4m，小潮约 2m。大潮日潮差却很小（<1.5m）或反之 → 警告。
    """
    warnings: list[str] = []
    d = daily_forecast.date
    rng = tide_range(daily_forecast)
    spring = is_spring_tide(d)
    if spring and 0 < rng < 1.5:
        warnings.append(f"{d} 月相为大潮但潮差仅 {rng:.2f}m，与黄海大潮 3-4m 量级不符")
    if (not spring) and rng > 4.0:
        warnings.append(f"{d} 月相为小潮但潮差达 {rng:.2f}m，量级偏大")
    return warnings


def verify_period_citation(cited_s: float, point, kind: str, tol: float = 0.05) -> None:
    """报告引用的周期值必须等于实际 Tm 或 Tp，kind 标注口径（需求 2.3）。"""
    if kind == "Tm":
        actual = point.wave_period_mean_s
    elif kind == "Tp":
        actual = point.wave_period_peak_s
    else:
        raise ReportValidationError(f"周期口径必须为 Tm 或 Tp，得到 {kind!r}", "period_caliber")
    if actual is None:
        raise ReportValidationError(f"引用 {kind} 但该时段无此口径数据", "period_citation")
    if abs(cited_s - actual) > tol:
        raise ReportValidationError(
            f"周期引用不符：声称 {kind}={cited_s}，实际 {actual}", "period_citation")


def flag_gust_anomaly(point, ratio_threshold: float = 5.0) -> bool:
    """阵风/持续风比 > 阈值标记疑似异常（需求 2.5）。"""
    return point.gust_ratio > ratio_threshold


def tag_midrange_confidence(daily_forecast, day_index: int, threshold: int = 5) -> str | None:
    """D+5+ 标注可信度降级 ±30%（需求 2.6）。设置 is_midrange 并返回提示文案。"""
    if day_index >= threshold:
        daily_forecast.is_midrange = True
        return f"{daily_forecast.date} 为 D+{day_index} 中期预报，浪高可信度 ±30%"
    return None


def verify_narrative_support(claim_type: str, daily_forecast) -> bool:
    """叙事-数据依赖检查（需求 2.4）：声称的物理现象须有当日数据支撑。

    支持的现象：
      - "dispersion"：周期序列须持续上升（频散，涌浪主体在路上）。
      - "forerunner"：先行波 = 浪很小(Hs<0.5)但周期长(>=6s)。
    严禁用正确物理套不存在数据（v1 把先行波安在周期最低谷那天）。未知现象默认放行。
    """
    pts = daily_forecast.points
    if not pts:
        return False
    if claim_type == "dispersion":
        periods = [p.wave_period_mean_s for p in pts]
        return physics.is_dispersion_rising(periods)
    if claim_type == "forerunner":
        max_period = max((p.wave_period_peak_s or p.wave_period_mean_s) for p in pts)
        mean_hs = sum(p.wave_height_m for p in pts) / len(pts)
        return max_period >= 6.0 and mean_hs < 0.5
    return True


def verify_history_forecast_disjoint(history_date: date, forecast_dates: list[date]) -> None:
    """历史区与预报区日期必须互斥（需求 2.6 红线）。重叠抛 ReportValidationError。"""
    if history_date in forecast_dates:
        raise ReportValidationError(
            f"历史日期 {history_date} 与预报区重叠（预报区: {forecast_dates}）",
            "history_forecast_overlap")


def validate_report(context) -> list[str]:
    """跑全套校验。返回 Warning 列表；遇 ERROR 抛 ReportValidationError 阻断渲染。"""
    warnings: list[str] = []
    forecast_dates = [da.forecast.date for da in context.days]

    # 1) 每日星期 GMT+8 自洽（ERROR）
    for da in context.days:
        verify_weekday(da.forecast.date, da.forecast.weekday)

    # 2) 历史区与预报区互斥（ERROR）
    if context.history is not None:
        verify_history_forecast_disjoint(context.history.forecast.date, forecast_dates)

    # 3) 潮型↔月相、阵风异常、中期降级（WARNING）
    for i, da in enumerate(context.days):
        warnings.extend(verify_tide_vs_moon(da.forecast))
        for p in da.forecast.points:
            if flag_gust_anomaly(p):
                warnings.append(
                    f"{p.time:%Y-%m-%d %H:%M} 阵风比 {p.gust_ratio:.1f} 异常偏高，疑似数据问题")
        note = tag_midrange_confidence(da.forecast, i)
        if note:
            warnings.append(note)
    return warnings
