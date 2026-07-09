"""波浪物理公式 —— 纯函数，无副作用，全部可单测.

对应 design.md 第 4 节、domain-knowledge.md 第三节。
样例校验值：wavelength(3)=14.04, wavelength(5)=39, wavelength(7)=76.44。
"""

from __future__ import annotations

import math

GRAVITY = 9.81  # m/s^2

_COMPASS_16 = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def wavelength(period_s: float) -> float:
    """深水波长 L = 1.56 * T^2 (m)。

    3s→14m(泳池浪), 5s→42m(真浪), 7s→79m(滑翔毯) —— 推力天壤之别。
    """
    return 1.56 * period_s**2


def group_velocity(period_s: float) -> float:
    """深水群速 Cg = g*T / (4*pi) (m/s)。频散判据：长周期波更快。"""
    return GRAVITY * period_s / (4 * math.pi)


def energy_index(height_m: float, period_s: float) -> float:
    """相对波浪能量指数 E ∝ H^2 * T。

    例：1.18^2*5.05 ≈ 7.0 vs 0.3^2*3 ≈ 0.27 —— 能量差 ~25 倍。
    """
    return height_m**2 * period_s


def nearshore_height(offshore_hs_m: float, factor: float = 0.75) -> float:
    """外海 Hs 经黄海浅水衰减后的近岸浪高（保守 0.7-0.8）。"""
    return offshore_hs_m * factor


def face_height(hs_m: float, factor: float = 1.4) -> float:
    """浪面高度 ≈ Hs * 1.3-1.5。注意勿与近岸衰减重复放大。"""
    return hs_m * factor


def swell_purity(swell_h_m: float, total_h_m: float) -> float:
    """涌浪纯度 (%) = 涌浪高 / 总浪高 * 100。total 为 0 时返回 0。"""
    if total_h_m <= 0:
        return 0.0
    return min(100.0, swell_h_m / total_h_m * 100.0)


def direction_16(deg: float) -> str:
    """方位角(度) → 16 方位罗盘字符串。"""
    return _COMPASS_16[int((deg + 11.25) // 22.5) % 16]


def is_onshore(wind_from_deg: float, spot_facing_deg: float, tol: float = 90.0) -> bool:
    """判断风是否向岸。

    spot_facing_deg 为浪点面朝的方向（浪从该方向来）。
    向岸风 = 风吹向陆地，即风的去向与浪点朝向相反，
    亦即风的来向与浪点朝向相近（夹角 < tol）。
    """
    diff = abs((wind_from_deg - spot_facing_deg + 180) % 360 - 180)
    return diff < tol


def wind_kind(wind_from_deg: float, spot_facing_deg: float) -> str:
    """把风按浪点朝向分类为 offshore/cross/onshore（domain-knowledge 第三节）。

    spot_facing_deg：浪点面朝方向（浪从该方向来，山东头≈157° SSE）。
    diff = |((wind_from_deg - facing + 180) mod 360) - 180|
      diff < 60   → "on"    向岸：风顺浪推、把浪面吹乱（差）
      diff > 120  → "off"   离岸：风逆浪、梳直浪面（最佳）
      else        → "cross" 侧岸（尚可）
    返回纯字符串，不依赖枚举，保持 physics 层零依赖；models 层再映射为 WindKind。
    """
    diff = abs((wind_from_deg - spot_facing_deg + 180) % 360 - 180)
    if diff < 60:
        return "on"
    if diff > 120:
        return "off"
    return "cross"


def is_dispersion_rising(periods: list[float], min_points: int = 3) -> bool:
    """频散信号：周期序列是否呈持续上升（涌浪主体在路上）。

    用最小二乘斜率 > 0 且首尾差为正作为判据。
    """
    n = len(periods)
    if n < min_points:
        return False
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(periods) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, periods))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den if den else 0.0
    return slope > 0 and periods[-1] > periods[0]
