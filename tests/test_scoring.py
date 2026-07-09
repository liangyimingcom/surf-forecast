"""scoring.py 单测 —— 阈值加载/分段评分/离岸放宽/综合分/短板/排序（Task 2.3, A6/A7）。"""

from datetime import date

import pytest

from surf_forecast import scoring
from surf_forecast.models import DailyAnalysis, DailyForecast, ParamScore

CFG = scoring.load_thresholds("config/thresholds.yaml")


def test_load_thresholds_ok():
    assert set(("weights", "wind")).issubset(CFG)
    assert CFG["wind"]["spot_facing_deg"] == 157
    assert abs(sum(CFG["weights"].values()) - 1.0) < 1e-6


def test_load_thresholds_bad_weights(tmp_path):
    bad = tmp_path / "t.yaml"
    bad.write_text(
        "weights: {wave_height: 0.5, period: 0.2, wind: 0.2, purity: 0.2, tide: 0.2}\n"
        "wave_height: {bands: []}\nperiod: {bands: []}\n"
        "wind: {spot_facing_deg: 157, onshore_bands: []}\n"
        "purity: {bands: []}\ntide: {ideal_range: [0.3,1.0]}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="合计"):
        scoring.load_thresholds(str(bad))


def test_score_wave_height_bands():
    assert scoring.score_wave_height(0.8, CFG).score == 6   # 适中
    assert scoring.score_wave_height(1.5, CFG).score == 9   # 优秀
    assert scoring.score_wave_height(0.2, CFG).score == 1   # 不可冲


def test_score_period_prefers_tp():
    s = scoring.score_period(5.0, CFG, peak_s=6.5)
    assert s.score == 8 and "Tp" in s.note            # 用 Tp=6.5 → 顺滑推送
    s2 = scoring.score_period(5.0, CFG, peak_s=None)
    assert "Tm" in s2.note                            # 无 Tp 退回 Tm


def test_score_wind_offshore_relaxes_one_band():
    # 10kn 向岸 → 较强(混乱) score3；离岸放宽一档 → score6
    onshore = scoring.score_wind(10.0, 157, CFG)      # 风来向≈浪点朝向 → 向岸
    offshore = scoring.score_wind(10.0, 337, CFG)     # NNW → 离岸
    assert onshore.score == 3
    assert offshore.score == 6
    assert "离岸放宽一档" in offshore.note


def test_score_purity_bands():
    assert scoring.score_purity(90, CFG).score == 10  # 丝绸
    assert scoring.score_purity(75, CFG).score == 7   # 良好
    assert scoring.score_purity(40, CFG).score == 2   # 差


def test_score_tide_bands():
    assert scoring.score_tide(0.6, CFG).score == 9    # 理想
    assert scoring.score_tide(1.3, CFG).score == 4    # 高潮 mushy
    assert scoring.score_tide(0.2, CFG).score == 4    # 极低拍底


def test_composite_and_weakest():
    scores = {
        "wave_height": ParamScore(name="wave_height", score=8, grade=""),
        "period": ParamScore(name="period", score=8, grade=""),
        "wind": ParamScore(name="wind", score=10, grade=""),
        "purity": ParamScore(name="purity", score=5, grade=""),
        "tide": ParamScore(name="tide", score=9, grade=""),
    }
    comp = scoring.composite_score(scores, CFG["weights"])
    # 0.3*8+0.25*8+0.2*10+0.15*5+0.1*9 = 2.4+2.0+2.0+0.75+0.9 = 8.05
    assert comp == pytest.approx(8.05, abs=0.01)
    assert scoring.weakest(scores) == "purity"


def _da(composite, purity_score):
    scores = {
        "purity": ParamScore(name="purity", score=purity_score, grade=""),
        "wind": ParamScore(name="wind", score=5, grade=""),
    }
    return DailyAnalysis(
        forecast=DailyForecast(date=date(2026, 6, 20)),
        scores=scores,
        composite=composite,
    )


def test_rank_days_quality_tiebreak():
    # 两日综合分并列 7.6，纯度高者优先（需求 3.6）
    days = [_da(7.6, 49), _da(7.6, 80)]
    assert scoring.rank_days(days) == [1, 0]
    # 综合分不并列时按分数降序
    days2 = [_da(6.0, 90), _da(8.0, 50)]
    assert scoring.rank_days(days2) == [1, 0]
