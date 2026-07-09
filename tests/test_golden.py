"""test_golden —— 端到端：排名确定性、离岸判定、历史口径一致、CLI JSON 含 wdeg（A1/A6/A9）。"""

import json
from datetime import date, datetime

from surf_forecast import analyze, cli, render, scoring
from surf_forecast.models import DailyForecast, ForecastPoint, TideExtreme

CFG = scoring.load_thresholds("config/thresholds.yaml")


def _pt(h, d, hs, tp, wdir, swell):
    return ForecastPoint(
        time=datetime(d.year, d.month, d.day, h), wave_height_m=hs, wave_direction_deg=160,
        wave_period_mean_s=tp - 1, wave_period_peak_s=tp, swell_height_m=swell,
        wind_speed_kn=8, wind_direction_deg=wdir, wind_gust_kn=11, sea_level_m=0.6,
    )


def _day(d, hs, tp, wdir, swell):
    return DailyForecast(
        date=d, points=[_pt(h, d, hs, tp, wdir, swell) for h in (6, 9, 12)],
        tide_extremes=[TideExtreme(time=datetime(d.year, d.month, d.day, 9),
                                   level_m=0.9, kind="high")],
        sunrise=datetime(d.year, d.month, d.day, 4),
        sunset=datetime(d.year, d.month, d.day, 20),
    )


def test_golden_ranking_and_offshore():
    # 三日：王者日(高浪高纯度长周期+离岸) 应排第一；向岸日垫底
    king = _day(date(2026, 6, 24), hs=1.1, tp=7.0, wdir=337, swell=1.0)   # 离岸
    mid = _day(date(2026, 6, 23), hs=0.8, tp=6.0, wdir=247, swell=0.6)    # 侧岸
    poor = _day(date(2026, 6, 22), hs=0.5, tp=4.5, wdir=157, swell=0.3)   # 向岸
    ctx = analyze.build_context(
        36.092, 120.468, 3, "青岛山东头",
        forecasts=[poor, mid, king], calibrated_at=datetime(2026, 6, 22, 10, 0))
    # 王者日(index 2)排第一
    assert ctx.ranking[0] == 2
    assert ctx.ranking[-1] == 0
    # 离岸判定：王者日晨风离岸，向岸日晨风向岸
    assert ctx.days[2].dawn_wind_kind.value == "off"
    assert ctx.days[0].dawn_wind_kind.value == "on"


def test_golden_history_parity_and_disjoint():
    # 历史(昨日 6-19)与预报(6-20起)口径一致、日期不重叠（A9）
    hist = _day(date(2026, 6, 19), hs=0.9, tp=6.5, wdir=337, swell=0.8)
    fc = [_day(date(2026, 6, 20), hs=0.8, tp=6.0, wdir=337, swell=0.6)]
    ctx = analyze.build_context(36.092, 120.468, 1, "青岛山东头",
                                forecasts=fc, calibrated_at=datetime(2026, 6, 20, 10, 0))
    ctx.history = analyze.analyze_day(hist, CFG)
    rep = render.render_json(ctx)
    # history 与 forecast day 字段一致（口径一致），且 history 多 predict
    fkeys = set(rep["days"][0])
    hkeys = set(rep["history"])
    assert fkeys.issubset(hkeys)              # 同口径字段
    assert "predict" in rep["history"]
    assert "wdeg" in rep["history"]
    # 日期不重叠
    assert rep["history"]["date"] not in [d["date"] for d in rep["days"]]


def test_golden_cli_json_has_wdeg(tmp_path, monkeypatch):
    # CLI --format json 端到端，monkeypatch fetch 避免触网
    fc = [_day(date(2026, 6, 20), hs=0.8, tp=6.5, wdir=337, swell=0.6)]

    def fake_fetch(lat, lon, days, **kw):
        return fc
    monkeypatch.setattr(analyze.fetch, "fetch_forecast", fake_fetch)

    out = tmp_path / "report.json"
    rc = cli.main(["--lat", "36.092", "--lon", "120.468", "--days", "1",
                   "--spot", "青岛山东头", "--out", str(out), "--format", "json"])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["spot"] == "青岛山东头"
    assert "wdeg" in data["days"][0] and data["days"][0]["wdeg"][0] == 337
    assert "GMT+8" in data["calibratedAt"]
