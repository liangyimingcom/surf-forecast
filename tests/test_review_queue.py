# -*- coding: utf-8 -*-
"""A3 review_queue triage 单测——确定性,双侧钉死边界。"""
import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_spec = importlib.util.spec_from_file_location(
    "review_queue", os.path.join(_ROOT, "tools", "review_queue.py"))
rq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rq)


# ---- is_spam：MIN_TEXT_LEN 双侧钉死 ----
def test_spam_empty():
    assert rq.is_spam({"text": ""})[0] is True

def test_spam_too_short_boundary():
    # 7 字 < 8 → 垃圾；8 字 → 非垃圾（边界两侧）
    assert rq.is_spam({"text": "a" * (rq.MIN_TEXT_LEN - 1)})[0] is True
    assert rq.is_spam({"text": "a" * rq.MIN_TEXT_LEN})[0] is False

def test_spam_illegal_kind():
    assert rq.is_spam({"text": "这是一条足够长的正常需求", "kind": "hack"})[0] is True

def test_spam_valid_ok():
    assert rq.is_spam({"text": "这是一条足够长的正常需求", "kind": "bug"})[0] is False


# ---- normalize_text ----
def test_normalize_collapses_ws():
    assert rq.normalize_text("  A   B\tC ") == "a b c"


# ---- find_duplicates：首个保留,后续标 dup ----
def test_find_duplicates():
    rows = [{"id": "1", "text": "加个页脚"}, {"id": "2", "text": "加个页脚"}, {"id": "3", "text": "别的"}]
    dup = rq.find_duplicates(rows)
    assert dup == {"2": "1"}
    assert "1" not in dup and "3" not in dup

def test_find_duplicates_empty_text_ignored():
    assert rq.find_duplicates([{"id": "1", "text": ""}, {"id": "2", "text": ""}]) == {}


# ---- priority_of ----
def test_priority_order():
    assert rq.priority_of({"kind": "bug"}) < rq.priority_of({"kind": "improve"})
    assert rq.priority_of({"kind": "improve"}) < rq.priority_of({"kind": "new_feature"})
    assert rq.priority_of({"kind": "new_feature"}) < rq.priority_of({"kind": "remove"})
    assert rq.priority_of({"kind": "unknown"}) == 5


# ---- triage：排序把 bug 顶前、垃圾/重复沉底 ----
def test_triage_sort_and_flags():
    rows = [
        {"id": "spam", "text": "x", "kind": "bug"},                    # 垃圾(过短)
        {"id": "first", "text": "同样的需求文本内容", "kind": "improve"}, # 首个=规范
        {"id": "dup", "text": "同样的需求文本内容", "kind": "improve"},   # 后出现=重复
        {"id": "bug1", "text": "详情页图表点击崩溃需修复", "kind": "bug"}, # 真 bug,最高优先
    ]
    out = rq.triage(rows)
    # 第一条应是真 bug(非垃圾非重复,优先级最高)
    assert out[0]["id"] == "bug1"
    # 垃圾条 spam=True 且排在最后区
    ids = [x["id"] for x in out]
    assert out[ids.index("spam")]["spam"] is True
    # dup 有 dup_of 指向 first
    d = out[ids.index("dup")]
    assert d["dup_of"] == "first"
