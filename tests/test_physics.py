"""physics.py 单测 —— 校验 domain-knowledge.md 的样例值（Task 2.3）。

这是脚手架中唯一可立即通过的测试，证明工程骨架可运行。
其余测试见 design.md 第 9 节，随对应模块实现而补全。
"""

import math

from surf_forecast import physics


def test_wavelength_examples():
    assert math.isclose(physics.wavelength(3), 14.04, rel_tol=1e-6)
    assert math.isclose(physics.wavelength(5), 39.0, rel_tol=1e-6)
    assert math.isclose(physics.wavelength(7), 76.44, rel_tol=1e-6)


def test_group_velocity_monotonic():
    # 长周期波群速更快 —— 频散的物理基础
    assert physics.group_velocity(7) > physics.group_velocity(3)


def test_energy_index_ratio():
    # 1.18m@5.05s 的能量约为 0.3m@3s 的 ~25 倍
    big = physics.energy_index(1.18, 5.05)
    small = physics.energy_index(0.3, 3.0)
    assert 20 < big / small < 30


def test_swell_purity_bounds():
    assert physics.swell_purity(0.4, 0.4) == 100.0
    assert physics.swell_purity(0.1, 0.4) == 25.0
    assert physics.swell_purity(0.0, 0.0) == 0.0


def test_direction_16():
    assert physics.direction_16(0) == "N"
    assert physics.direction_16(157) == "SSE"
    assert physics.direction_16(270) == "W"


def test_dispersion_rising():
    # 6/13 周期序列上升 → 频散信号成立
    assert physics.is_dispersion_rising([3.2, 3.4, 3.7, 4.05]) is True
    # 6/11 午后周期下降 → 不成立（v1 把先行波误安在此）
    assert physics.is_dispersion_rising([4.4, 4.0, 3.1, 2.75]) is False


def test_is_onshore():
    # 浪点朝 SSE(157)；SSE 来的风为向岸
    assert physics.is_onshore(157, 157) is True
    # W(270) 风对 SSE 浪点为离岸
    assert physics.is_onshore(270, 157) is False


def test_wind_kind_157():
    # 山东头朝向 SSE(157)
    assert physics.wind_kind(157, 157) == "on"    # 正向岸
    assert physics.wind_kind(337, 157) == "off"   # NNW，正离岸（157+180）
    assert physics.wind_kind(67, 157) == "cross"  # ENE，侧岸（diff≈90）
    assert physics.wind_kind(247, 157) == "cross" # WSW，侧岸（diff≈90）
