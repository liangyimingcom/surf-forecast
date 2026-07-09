"""昨日回看校验 —— 自评持久化 + 偏差校准（forecast-accuracy-feedback F4/F5/F6）。

四档自评：accurate(准)/optimistic(偏乐观)/conservative(偏保守)/noidea(没下水)。
偏差校准只产出**提示**，绝不篡改原始评分（ADR-F2，数据诚实优先）。全程 GMT+8。
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

GMT8 = ZoneInfo("Asia/Shanghai")

VALID_KINDS = ("accurate", "optimistic", "conservative", "noidea")

_FEEDBACK_TEXT = {
    "accurate": "模型标定可信，可放心参考本周预报。",
    "optimistic": "常见原因：近岸浅水打折、风/纯度体感更敏感。建议本周预期下调半档。",
    "conservative": "实际更好（局地涌浪聚焦/离岸梳面超预期），可上调半档但保留安全 margin。",
    "noidea": "下次下水后回来评分，多积累以校准该浪点。",
}


class FeedbackError(Exception):
    pass


def record_vote(store, email: str, spot: str, date: str, kind: str) -> dict:
    """持久化一条自评（含 GMT+8 时间，F5）。返回即时反馈文案（F4）。"""
    if kind not in VALID_KINDS:
        raise FeedbackError(f"自评档位非法：{kind}")
    vote = {
        "email": email, "spot": spot, "date": date, "kind": kind,
        "created_at_gmt8": datetime.now(GMT8).strftime("%Y-%m-%d %H:%M GMT+8"),
    }
    store.add_vote(vote)
    return {"ok": True, "feedback": _FEEDBACK_TEXT[kind]}


def compute_bias(store, email: str, spot: str, min_votes: int = 3) -> dict:
    """统计近 N 条自评的系统性偏差倾向 + 校准建议（F6，不改原评分）。"""
    votes = store.votes_for(email, spot)
    # 偏差只看下过水的（排除 noidea）
    rated = [v for v in votes if v["kind"] != "noidea"]
    n = len(rated)
    counts = {k: sum(1 for v in rated if v["kind"] == k)
              for k in ("accurate", "optimistic", "conservative")}
    if n < min_votes:
        return {"bias": "insufficient", "samples": n, "min": min_votes,
                "suggestion": f"已积累 {n}/{min_votes} 条，继续评分以校准该浪点。"}

    dominant = max(counts, key=counts.get)
    if dominant == "optimistic":
        bias, suggestion = "偏乐观", "你常觉得此点偏乐观，建议预期下调半档看。"
    elif dominant == "conservative":
        bias, suggestion = "偏保守", "你常觉得此点比预报好，可上调半档但留安全 margin。"
    else:
        bias, suggestion = "标定可信", "历次体感与预报吻合，可放心参考。"
    return {"bias": bias, "samples": n, "counts": counts, "suggestion": suggestion,
            "note": "仅为体感校准提示，不修改原始评分。"}
