"""评分纯函数 —— 见 design.md 第 5 节、requirements 3.x、Task 1.2/2.2.

每个 score_x 返回 ParamScore（0-10）。阈值与权重来自 config/thresholds.yaml
（load_thresholds），不硬编码。
排序：composite 降序，并列时质量参数(纯度/风)优先于数量参数(浪高)（需求 3.6）。
核心信条：综合分排序，但 weakest() 必须暴露短板参数（需求 3.4）。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from . import physics
from .models import ParamScore, WindKind

_REQUIRED_TOP = ("weights", "wave_height", "period", "wind", "purity", "tide")
_WEIGHT_KEYS = ("wave_height", "period", "wind", "purity", "tide")


def load_thresholds(path: str = "config/thresholds.yaml") -> dict:
    """解析并校验阈值配置（Task 1.2）。weights 须合计 1.0。

    校验：顶层键齐全；weights 含五项且合计 ≈1.0（容差 1e-6）；wind 含 spot_facing_deg。
    缺失或不自洽抛 ValueError。
    """
    p = Path(path)
    if not p.exists():
        raise ValueError(f"阈值配置不存在: {path}")
    cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    missing = [k for k in _REQUIRED_TOP if k not in cfg]
    if missing:
        raise ValueError(f"阈值配置缺少顶层键: {missing}")

    weights = cfg["weights"]
    wmissing = [k for k in _WEIGHT_KEYS if k not in weights]
    if wmissing:
        raise ValueError(f"weights 缺少: {wmissing}")
    total = sum(float(weights[k]) for k in _WEIGHT_KEYS)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"weights 合计须为 1.0，实际 {total}")

    if "spot_facing_deg" not in cfg["wind"]:
        raise ValueError("wind 配置缺少 spot_facing_deg（离岸判定必需）")

    return cfg


def _band_by_max(value: float, bands: list[dict]) -> dict:
    """按上界 max 升序的分段：返回 value <= max 的第一段（兜底末段）。"""
    for band in bands:
        if value <= band["max"]:
            return band
    return bands[-1]


def _band_by_min(value: float, bands: list[dict]) -> dict:
    """按下界 min 降序的分段：返回 value >= min 的第一段（兜底末段）。"""
    for band in bands:
        if value >= band["min"]:
            return band
    return bands[-1]


def score_wave_height(value_m: float, thresholds: dict, context=None) -> ParamScore:
    """浪高分段评分（外海 Hs，需求 3.1）。"""
    band = _band_by_max(value_m, thresholds["wave_height"]["bands"])
    return ParamScore(
        name="wave_height",
        score=float(band["score"]),
        grade=band["grade"],
        note=f"Hs={value_m:.2f}m",
    )


def score_period(value_mean_s: float, thresholds: dict, peak_s: float | None = None,
                 context=None) -> ParamScore:
    """周期评分，6s 临界；prefer_peak_period 时优先用 Tp 并标注口径（需求 3.2/A4）。"""
    pcfg = thresholds["period"]
    use_peak = bool(pcfg.get("prefer_peak_period")) and peak_s is not None
    value = peak_s if use_peak else value_mean_s
    caliber = "Tp" if use_peak else "Tm"
    band = _band_by_max(value, pcfg["bands"])
    return ParamScore(
        name="period",
        score=float(band["score"]),
        grade=band["grade"],
        note=f"{caliber}={value:.1f}s（口径 {caliber}）",
    )


def score_wind(speed_kn: float, wind_dir_deg: float, thresholds: dict,
               context=None) -> ParamScore:
    """风况评分，离岸/向岸感知；离岸放宽一档（需求 3.5/A6）。"""
    wcfg = thresholds["wind"]
    facing = float(wcfg["spot_facing_deg"])
    bands = wcfg["onshore_bands"]
    kind = WindKind(physics.wind_kind(wind_dir_deg, facing))

    # 基准档（按向岸标准）
    idx = next((i for i, b in enumerate(bands) if speed_kn <= b["max"]), len(bands) - 1)
    # 离岸放宽：上移 offshore_bonus_band 档（更高分），clamp
    if kind is WindKind.OFFSHORE:
        bonus = int(wcfg.get("offshore_bonus_band", 1))
        idx = max(0, idx - bonus)
    band = bands[idx]
    label = {"off": "离岸", "cross": "侧岸", "on": "向岸"}[kind.value]
    return ParamScore(
        name="wind",
        score=float(band["score"]),
        grade=band["grade"],
        note=f"{speed_kn:.1f}kn {label}({physics.direction_16(wind_dir_deg)})"
             + ("·离岸放宽一档" if kind is WindKind.OFFSHORE else ""),
    )


def score_purity(purity_pct: float, thresholds: dict, context=None) -> ParamScore:
    """涌浪纯度评分（按 min 降序分段，需求 3.1）。"""
    band = _band_by_min(purity_pct, thresholds["purity"]["bands"])
    return ParamScore(
        name="purity",
        score=float(band["score"]),
        grade=band["grade"],
        note=f"纯度={purity_pct:.0f}%",
    )


def score_tide(level_m: float, thresholds: dict, context=None) -> ParamScore:
    """潮汐配合评分：理想中潮位最佳，过高 mushy、过低拍底（需求 3.1）。"""
    tcfg = thresholds["tide"]
    lo, hi = tcfg["ideal_range"]
    high_pen = tcfg["high_tide_penalty_above"]
    low_pen = tcfg["low_tide_penalty_below"]
    if lo <= level_m <= hi:
        score, grade = 9.0, "🟢 理想中潮位"
    elif level_m >= high_pen:
        score, grade = 4.0, "🟠 高潮 mushy"
    elif level_m <= low_pen:
        score, grade = 4.0, "🟠 极低潮拍底"
    else:
        score, grade = 7.0, "🟡 中等配合"
    return ParamScore(name="tide", score=score, grade=grade, note=f"潮位={level_m:.2f}m")


def composite_score(scores: dict[str, ParamScore], weights: dict) -> float:
    """加权平均 → 0-10（需求 3.2）。缺失分项按权重重新归一。"""
    num = 0.0
    wsum = 0.0
    for name, w in weights.items():
        ps = scores.get(name)
        if ps is None:
            continue
        num += ps.score * float(w)
        wsum += float(w)
    if wsum <= 0:
        return 0.0
    return round(num / wsum, 2)


def weakest(scores: dict[str, ParamScore]) -> str:
    """得分最低的分项名（需求 3.4，体现『上限由最差参数决定』）。"""
    if not scores:
        return ""
    return min(scores.values(), key=lambda ps: ps.score).name


# 质量参数优先级（并列时排序用，需求 3.6）：纯度/风 > 周期 > 浪高/潮汐
_QUALITY_ORDER = ("purity", "wind", "period", "wave_height", "tide")


def rank_days(daily_analyses: list) -> list[int]:
    """按 composite 降序排序，并列时质量参数(纯度/风)优先；返回 days 原始索引（需求 3.6）。"""
    def sort_key(item):
        idx, da = item
        quality = tuple(
            da.scores[q].score if (da.scores and q in da.scores) else 0.0
            for q in _QUALITY_ORDER
        )
        return (-da.composite, *(-q for q in quality))

    indexed = list(enumerate(daily_analyses))
    indexed.sort(key=sort_key)
    return [idx for idx, _ in indexed]
