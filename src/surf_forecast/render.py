"""报告渲染 —— 见 design.md 第 7/8 节、requirements 4.x/5.x、Task 6.x.

两路输出：
  render_json(context)  → DATA CONTRACT（形状=前端 DAYS/HISTORY/REPORT，**必含 wdeg**）
  render_report(context) → Markdown（CLI，套 templates/report.md.j2）
关键红线：JSON 必须输出 wdeg（风向度，前端离岸编码消费）；周期 Tm/Tp 双口径分列 tp/tp2。
"""

from __future__ import annotations

from datetime import datetime

from .models import DailyAnalysis, ReportContext

_PARAMS = ("wave_height", "period", "wind", "purity", "tide")
_PARAM_CN = {"wave_height": "浪高", "period": "周期", "wind": "风况",
             "purity": "纯度", "tide": "潮汐"}
# 物理小课堂：按当日短板参数给一条解释（前端 lesson=[标题,正文]）
_LESSON = {
    "purity": ["涌浪纯度为什么决定浪面", "纯度=涌浪/总浪。高=丝滑干净；低=风浪占比大、浪面起毛 choppy。今天短板在纯度，浪面会带纹理。"],
    "period": ["周期决定推力", "波长 L=1.56×T²，周期越长推力越强。6s 是黄海临界线，低于则浪面发颠、起乘晚。"],
    "wind": ["离岸风为什么是好风", "风从陆地吹向海，逆浪梳直浪面、托住浪壁更陡更晚破——冲浪最爱。>15kn 会吹得起乘困难。"],
    "wave_height": ["浪高怎么换算", "近岸浪高≈外海 Hs×0.7-0.8，浪面≈Hs×1.3-1.5。门槛之下只能长板滑水。"],
    "tide": ["潮汐如何配合", "中潮位最理想；高潮淹浪型 mushy、极低潮拍底 close-out，要与浪高峰值错峰看。"],
}
_DEFAULT_LESSON = ["冲浪日的上限由最差参数决定", "加权综合分定排序，但体验上限被当日最弱的那一项封顶——先看短板，再看总分。"]


def _daytime(df):
    if df.sunrise and df.sunset:
        pts = [p for p in df.points if df.sunrise <= p.time <= df.sunset]
        if pts:
            return pts
    return list(df.points)


def _tag(score: float) -> str:
    if score >= 8:
        return "🔥 必冲"
    if score >= 6.5:
        return "👍 推荐"
    if score >= 5:
        return "🆗 一般"
    return "😴 不建议"


def _level(hs: float) -> str:
    if hs < 0.5:
        return "初学友好"
    if hs <= 1.0:
        return "进阶"
    return "高级"


def _tide_text(df) -> str:
    if not df.tide_extremes:
        return "潮汐数据不足"
    parts = [
        f"{'高潮' if e.kind == 'high' else '低潮'} {e.time:%H:%M}({e.level_m:.2f}m)"
        for e in df.tide_extremes
    ]
    return "，".join(parts)


def _window_pair(window_str: str):
    """'HH:MM-HH:MM' → [起小时, 止小时] 数字对（前端图表最佳窗口高亮 sx(w[0])/sx(w[1]) 依赖）。"""
    try:
        a, b = window_str.split("-")
        ah, am = a.split(":")
        bh, bm = b.split(":")
        return [int(ah) + int(am) / 60, int(bh) + int(bm) / 60]
    except Exception:  # noqa: BLE001
        return None


def _day_to_dict(da: DailyAnalysis, today: bool) -> dict:
    df = da.forecast
    pts = _daytime(df)
    rep_hs = max((p.wave_height_m for p in pts), default=0.0)
    # dims：前端用中文键标签（DATA CONTRACT 对齐 浪报MVP.html）
    dims = {_PARAM_CN[n]: round(da.scores[n].score, 1) for n in _PARAMS if n in da.scores}
    # pa：前端期望 [标签, "x/10", 文案] 三元组
    pa = [[_PARAM_CN[n], f"{int(round(da.scores[n].score))}/10",
           f"{da.scores[n].grade}：{da.scores[n].note}"]
          for n in _PARAMS if n in da.scores]
    lesson = _LESSON.get(da.weakest_param, _DEFAULT_LESSON)
    plan = ["🏄 行动建议", da.recommendation or "按窗口择时下水。"]
    safety = (["安全提醒", "浪高 >1m 即便小潮也查脚绳、看 5 分钟流向、结伴下水。"]
              if rep_hs > 1.0 else [])
    return {
        "id": df.date.isoformat(),
        "date": df.date.isoformat(),
        "week": df.weekday,
        "today": today,
        "best": False,
        "score": da.composite,
        "stars": int(round(da.composite / 2)),
        "tag": _tag(da.composite),
        "phase": "",
        "dawnWind": da.dawn_wind_kind.value if da.dawn_wind_kind else "",
        "window": da.best_window,
        "windows": ([_window_pair(da.best_window)]
                    if da.best_window and _window_pair(da.best_window) else []),
        "board": da.board,
        "level": _level(rep_hs),
        "novice": da.recommendation,
        "weakest": da.weakest_param,
        # —— 图表时间序列（白天时段）；times 为数字小时（前端图表 sx 缩放依赖）——
        "times": [round(p.time.hour + p.time.minute / 60, 2) for p in pts],
        "hs": [round(p.wave_height_m, 2) for p in pts],
        "swell": [round(p.swell_height_m, 2) for p in pts],
        "tp": [round(p.wave_period_mean_s, 1) for p in pts],          # Tm 实线
        "tp2": [round(p.wave_period_peak_s, 1) if p.wave_period_peak_s else None
                for p in pts],                                        # Tp 虚线
        "wind": [round(p.wind_speed_kn, 1) for p in pts],
        "gust": [round(p.wind_gust_kn, 1) for p in pts],
        "wdeg": [round(p.wind_direction_deg) for p in pts],           # ★ 风向编码必需
        # tideEvents 为 [小时, 潮位] 数字对（前端图表 e[0]=小时 e[1]=潮位）
        "tideEvents": [[round(e.time.hour + e.time.minute / 60, 2), round(e.level_m, 2)]
                       for e in df.tide_extremes],
        "tideText": _tide_text(df),
        "dims": dims,
        "pa": pa,
        "lesson": lesson,
        "plan": plan,
        "safety": safety,
        "confidenceNotes": da.confidence_notes,
        "midrange": df.is_midrange,
        "midterm": df.is_midrange,
    }


def _predict_from(da: DailyAnalysis) -> dict:
    """昨日『系统当时预报判断』摘要（供回看对照，feedback spec）。"""
    df = da.forecast
    pts = _daytime(df)
    hs = max((p.wave_height_m for p in pts), default=0.0)
    tp = max((p.wave_period_peak_s or p.wave_period_mean_s for p in pts), default=0.0)
    wind = max((p.wind_speed_kn for p in pts), default=0.0)
    return {
        "height": f"{hs:.1f}m",
        "period": f"{tp:.1f}s",
        "wind": f"{wind:.0f}kn",
        "best": da.best_window,
        "board": da.board,
        "verdict": da.recommendation,
    }


def render_json(context: ReportContext) -> dict:
    """输出 DATA CONTRACT JSON（REPORT），形状对齐前端 DAYS/HISTORY（需求 5.1）。"""
    today = context.calibrated_at.date()
    days = [_day_to_dict(da, today=(da.forecast.date == today)) for da in context.days]

    # 标记最佳日（前端 Hero `DAYS.find(d=>d.best)` 依赖；缺失会致前端渲染中断）
    if days and context.ranking:
        days[context.ranking[0]]["best"] = True
    elif days:
        days[0]["best"] = True

    # 数据驱动的「一句话剧情」（替代前端硬编码静态叙事）
    story = ""
    if days:
        b = days[context.ranking[0] if context.ranking else 0]
        t = next((x for x in days if x["today"]), days[0])
        weak_cn = _PARAM_CN.get(t.get("weakest", ""), t.get("weakest", ""))
        story = (f"<b>一句话剧情：</b>本周最佳 <b>{b['week']} {b['date']} {b['score']}/10"
                 f"（{b['tag']}）</b>；今日 {t['week']} {t['date']} {t['score']}/10（{t['tag']}）。"
                 f"短板参数：<b>{weak_cn}</b>——冲浪日的上限由最差参数决定。")

    history = None
    if context.history is not None:
        history = _day_to_dict(context.history, today=False)
        history["predict"] = _predict_from(context.history)

    return {
        "spot": context.spot,
        "coord": [context.lat, context.lon],
        "spotFacingDeg": context.spot_facing_deg,
        "calibratedAt": context.calibrated_at.strftime("%Y-%m-%d %H:%M GMT+8"),
        "ranking": context.ranking,
        "days": days,
        "story": story,
        "history": history,
        "lifecycle": context.lifecycle,
        "confidenceNotes": context.warnings,
    }


def render_lifecycle_ascii(lifecycle) -> str:
    """程序化生成 ASCII 生命周期图（需求 5.3）。"""
    lines = []
    for item in lifecycle:
        score = item.get("score", 0.0)
        bar = "█" * int(round(score))
        lines.append(f"{item.get('week', '')} {item.get('date', '')} "
                     f"|{bar:<10}| {score}/10  Hs{item.get('hs', 0)}m T{item.get('period', 0)}s")
    return "\n".join(lines)


def render_report(context: ReportContext, style: str = "professional",
                  template_dir: str = "templates",
                  config_path: str = "config/thresholds.yaml") -> str:
    """渲染完整报告 Markdown 字符串（套 templates/report.md.j2，需求 5.x）。"""
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    from . import scoring
    weights = scoring.load_thresholds(config_path)["weights"]

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True, lstrip_blocks=True,
    )
    tmpl = env.get_template("report.md.j2")

    dates = [da.forecast.date for da in context.days]
    date_range = (f"{min(dates)} ~ {max(dates)}" if dates else "")
    notes = list(context.warnings)
    for da in context.days:
        notes.extend(da.confidence_notes)

    tmpl_ctx = type("C", (), {})()
    tmpl_ctx.spot = context.spot
    tmpl_ctx.coord = [context.lat, context.lon]
    tmpl_ctx.date_range = date_range
    tmpl_ctx.confidence_notes = [f"校准 {context.calibrated_at:%Y-%m-%d} 北京时间 GMT+8"] + notes
    tmpl_ctx.ranking = context.ranking
    tmpl_ctx.days = context.days
    tmpl_ctx.lifecycle_ascii = render_lifecycle_ascii(context.lifecycle)

    return tmpl.render(ctx=tmpl_ctx, w=weights)
