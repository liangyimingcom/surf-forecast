"""render.py 单测 —— DATA CONTRACT(含 wdeg/双周期/tideEvents)、markdown、生命周期 ASCII（Task 6.x）。"""

from datetime import date, datetime

from surf_forecast import analyze, render, scoring
from surf_forecast.models import DailyForecast, ForecastPoint, TideExtreme

CFG = scoring.load_thresholds("config/thresholds.yaml")


def _pt(h, d, hs=0.8, tp=6.5, wdir=337):
    return ForecastPoint(
        time=datetime(d.year, d.month, d.day, h), wave_height_m=hs, wave_direction_deg=160,
        wave_period_mean_s=5.0, wave_period_peak_s=tp, swell_height_m=0.6,
        wind_speed_kn=8, wind_direction_deg=wdir, wind_gust_kn=11, sea_level_m=0.6,
    )


def _day(d, hours=(6, 9, 12)):
    return DailyForecast(
        date=d, points=[_pt(h, d) for h in hours],
        tide_extremes=[TideExtreme(time=datetime(d.year, d.month, d.day, 9),
                                   level_m=0.9, kind="high")],
        sunrise=datetime(d.year, d.month, d.day, 4),
        sunset=datetime(d.year, d.month, d.day, 20),
    )


def _ctx():
    return analyze.build_context(
        36.092, 120.468, 2, "青岛山东头",
        forecasts=[_day(date(2026, 6, 20)), _day(date(2026, 6, 21))],
        calibrated_at=datetime(2026, 6, 20, 10, 0))


def test_render_json_has_wdeg_redline():
    rep = render.render_json(_ctx())
    day0 = rep["days"][0]
    # ★ 红线：wdeg 必须存在且与时段数一致
    assert "wdeg" in day0
    assert len(day0["wdeg"]) == len(day0["times"]) == 3
    assert day0["wdeg"][0] == 337


def test_render_json_dual_period_caliber():
    day0 = render.render_json(_ctx())["days"][0]
    assert day0["tp"][0] == 5.0     # Tm 实线
    assert day0["tp2"][0] == 6.5    # Tp 虚线


def test_render_json_chart_numeric_contract():
    # 前端图表 sx 缩放依赖：times 为数字小时；tideEvents 为 [小时,潮位] 数字对
    day0 = render.render_json(_ctx())["days"][0]
    assert all(isinstance(t, (int, float)) for t in day0["times"])
    assert day0["times"][0] == 6.0
    assert day0["tideEvents"] and all(
        isinstance(e, list) and len(e) == 2 and isinstance(e[0], (int, float))
        for e in day0["tideEvents"])
    # windows 为 [起,止] 数字对（前端图表最佳窗口高亮依赖）
    if day0["windows"]:
        assert len(day0["windows"][0]) == 2
        assert all(isinstance(x, (int, float)) for x in day0["windows"][0])


def test_render_json_contract_keys():
    rep = render.render_json(_ctx())
    assert rep["spot"] == "青岛山东头"
    assert rep["coord"] == [36.092, 120.468]
    assert "GMT+8" in rep["calibratedAt"]
    assert rep["spotFacingDeg"] == 157
    day0 = rep["days"][0]
    for key in ("id", "date", "week", "today", "score", "stars", "tag",
                "dawnWind", "window", "board", "level", "dims", "tideEvents", "wdeg"):
        assert key in day0, f"缺字段 {key}"
    assert day0["today"] is True            # 6-20 是 calibrated 当天
    assert day0["dawnWind"] == "off"        # wdir 337 → 离岸
    assert set(day0["dims"]) == {"浪高", "周期", "风况", "纯度", "潮汐"}
    assert len(day0["pa"][0]) == 3          # [标签, x/10, 文案] 三元组
    assert len(day0["lesson"]) == 2 and len(day0["plan"]) == 2  # [标题,正文]


def test_render_json_today_flag():
    rep = render.render_json(_ctx())
    assert rep["days"][0]["today"] is True
    assert rep["days"][1]["today"] is False


def test_render_json_best_and_story():
    rep = render.render_json(_ctx())
    # 前端 Hero 依赖：恰有一天 best=true（排名第一）
    bests = [d for d in rep["days"] if d.get("best")]
    assert len(bests) == 1
    assert rep["days"][rep["ranking"][0]]["best"] is True
    # 数据驱动剧情存在且含「本周最佳」
    assert "story" in rep and "本周最佳" in rep["story"]


def test_render_lifecycle_ascii():
    ctx = _ctx()
    rep = render.render_json(ctx)
    art = render.render_lifecycle_ascii(rep["lifecycle"])
    assert "周六" in art and "/10" in art


def test_render_markdown():
    md = render.render_report(_ctx())
    assert "青岛山东头" in md
    assert "速查排名" in md
    assert "GMT+8" in md


def test_score_precision_is_one_decimal():
    """分数精度单一来源：`/api/report` 的 days[].score 必须已是 1 位小数。

    根因回归：此前 render 输出 `da.composite` 原值（如 8.65），而 `/api/recommend`
    自己 round(...,1) → 8.7，同一天同一浪点两个端点给出不同数字（首页 8.7 vs 详情 8.65）。
    在输出层统一取整后，recommend 那次 round 变成幂等，两端必然一致。
    """
    rep = render.render_json(_ctx())
    for d in rep["days"]:
        s = d["score"]
        assert isinstance(s, float), f"score 应为 float，实得 {type(s)}"
        assert round(s, 1) == s, f"score 未取到 1 位小数：{s!r}"


def test_recommend_score_matches_report_score():
    """跨端点一致性：recommend 对同一份 report 取到的分数 == report 自己给的分数。"""
    import web.recommend as R

    rep = render.render_json(_ctx())
    best_day = next((d for d in rep["days"] if d.get("best")), rep["days"][0])
    # recommend 内部就是 round(float(bd["score"]), 1)；render 已取整 → 必须幂等
    assert round(float(best_day["score"]), 1) == best_day["score"]
    assert R._headline(best_day)  # 顺带确认 headline 对真实引擎输出不炸


def test_engine_output_through_recommend_has_no_raw_enum():
    """端到端（引擎真实输出 → recommend）：用户可见文案里不得出现内部枚举/术语。

    比手搓 fixture 更硬 —— fixture 会被写得比现实漂亮（本轮在 E2E 与单测两层都踩过），
    而引擎的 `dawnWind` 一定是 `WindKind.value`（off/cross/on）。
    """
    import web.recommend as R

    rep = render.render_json(_ctx())
    for d in rep["days"]:
        visible = " ".join(R._key_factors(d)) + " " + R._headline(d)
        assert d.get("dawnWind") in ("off", "cross", "on", "", None), \
            f"引擎的 dawnWind 应是枚举值，实得 {d.get('dawnWind')!r}"
        for raw in ("off", "cross", "on", "Tp"):
            assert raw not in visible, f"{raw!r} 泄漏到用户可见文案: {visible!r}"
        assert "到，" not in visible  # 窗口措辞必须是「下水」
