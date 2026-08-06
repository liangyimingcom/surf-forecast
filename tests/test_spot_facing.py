"""逐点浪点朝向：管路打通 + 「只在已校准时采用」的开关（2026-08-06）。

背景（为什么是开关而不是无条件采用）：
`/api/report` 的 `spotFacingDeg` 曾对**全国每个浪点**都返回 157°（青岛山东头 SSE），
源头是 `config/thresholds.yaml` 的全站常量。注册表里另有逐点 `facing`，但它来自
`tools/import_shilaoren_spots.py:guess_facing(city)` —— 按 city 英文名查表，
而 **41/58 个点的 city 没匹配上**，全部落 `return 135` 兜底，横跨 8 个地区
（巴厘岛 Canggu 实际朝西南、黄金海岸 Kirra 实际朝东，都被标 135）。
所以无条件采用 = 把一个任意全国常量换成另一个任意近全国常量，还静默改 58 点判定。
结论：**管路打通、取值门槛交给 `facing_calibrated`**。
"""
import pytest

from surf_forecast import analyze, physics, scoring

CFG = scoring.load_thresholds("config/thresholds.yaml")
GLOBAL_FACING = float(CFG["wind"]["spot_facing_deg"])


def test_uncalibrated_per_spot_value_is_ignored():
    """未校准的注册表值必须被忽略 —— 否则 58 个点的风向判定会静默改变。"""
    assert analyze.resolve_facing(CFG, facing_deg=135.0, facing_calibrated=False) == GLOBAL_FACING
    # 连巴厘岛那种明显不对的值也不许悄悄生效
    assert analyze.resolve_facing(CFG, facing_deg=135.0) == GLOBAL_FACING


def test_calibrated_per_spot_value_wins():
    """校准过的值必须生效，且无需改代码 —— 这就是打通管路的意义。"""
    assert analyze.resolve_facing(CFG, facing_deg=225.0, facing_calibrated=True) == 225.0


def test_calibrated_flag_without_value_falls_back():
    """只有标记没有值 → 退回全站口径，不炸也不猜。"""
    assert analyze.resolve_facing(CFG, facing_deg=None, facing_calibrated=True) == GLOBAL_FACING


@pytest.mark.parametrize("facing,wind_from,expect", [
    # 浪点朝南(180°)：北风(0°)从陆地吹向海 = 离岸
    (180.0, 0.0, "off"),
    (180.0, 180.0, "on"),      # 南风正对着浪来的方向 = 向岸
    # 同一个风向，换朝向后判定必须跟着变（这条是「逐点」真正生效的证据）
    (0.0, 0.0, "on"),
    (0.0, 180.0, "off"),
])
def test_facing_change_flips_wind_kind(facing, wind_from, expect):
    assert physics.wind_kind(wind_from, facing) == expect


def test_score_wind_honours_facing_override():
    """score_wind 必须用传入的 facing，而不是永远读全站常量。

    钉住这条 = 防回退：谁把 `facing=facing` 那个参数丢了，这里立刻炸。
    """
    speed, wind_from = 6.0, 0.0        # 北风 6kn
    onshore = scoring.score_wind(speed, wind_from, CFG, facing=0.0)     # 朝北 → 向岸
    offshore = scoring.score_wind(speed, wind_from, CFG, facing=180.0)  # 朝南 → 离岸
    assert "向岸" in onshore.note and "离岸" in offshore.note
    # 离岸放宽一档 → 同样风速分数必须更高（不是并列）
    assert offshore.score > onshore.score


def test_default_facing_unchanged_so_production_scores_do_not_move():
    """不传参时行为与改动前完全一致 —— 本次改动对生产是零行为变化。"""
    speed, wind_from = 6.0, 90.0
    assert (scoring.score_wind(speed, wind_from, CFG).score
            == scoring.score_wind(speed, wind_from, CFG, facing=GLOBAL_FACING).score)
