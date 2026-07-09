"""test_config —— 阈值驱动结果(A8)、配置校验、CLI parser（Task 7.3）。"""

import copy

import pytest

from surf_forecast import cli, scoring

CFG = scoring.load_thresholds("config/thresholds.yaml")


def test_threshold_change_changes_score_not_code():
    """A8：改 yaml(阈值) 改结果，代码不变。"""
    base = scoring.score_wave_height(0.8, CFG).score
    tweaked = copy.deepcopy(CFG)
    # 把 0.8 所在档(max 0.8)的分值从 6 改成 3
    for band in tweaked["wave_height"]["bands"]:
        if band["max"] == 0.80:
            band["score"] = 3
    changed = scoring.score_wave_height(0.8, tweaked).score
    assert base == 6 and changed == 3   # 同代码、不同阈值 → 不同结果


def test_missing_top_key_raises(tmp_path):
    bad = tmp_path / "t.yaml"
    bad.write_text("weights: {wave_height: 1.0}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        scoring.load_thresholds(str(bad))


def test_missing_spot_facing_raises(tmp_path):
    bad = tmp_path / "t.yaml"
    bad.write_text(
        "weights: {wave_height: 0.3, period: 0.25, wind: 0.2, purity: 0.15, tide: 0.1}\n"
        "wave_height: {bands: []}\nperiod: {bands: []}\n"
        "wind: {onshore_bands: []}\npurity: {bands: []}\ntide: {ideal_range: [0.3,1.0]}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="spot_facing_deg"):
        scoring.load_thresholds(str(bad))


def test_cli_parser_defaults_and_past_days():
    args = cli.build_parser().parse_args(
        ["--lat", "36.092", "--lon", "120.468", "--past-days", "1", "--format", "json"])
    assert args.lat == 36.092 and args.past_days == 1 and args.format == "json"
    assert args.days == 7  # 默认
