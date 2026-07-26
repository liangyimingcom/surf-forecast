# -*- coding: utf-8 -*-
"""L1 llm_guard 单测：限流/预算/校验 边界双侧钉死 + mutation。"""
from datetime import datetime, timedelta
from web import llm_guard as g


class _Clock:
    def __init__(self, t=1000.0): self.t = t
    def __call__(self): return self.t


# ---- RateLimiter：window 内 max 次边界双侧 ----
def test_ratelimit_allows_up_to_max():
    clk = _Clock(); r = g.RateLimiter(3, 60, now_fn=clk)
    assert [r.allow("ip") for _ in range(3)] == [True, True, True]  # 第3次仍允许
    assert r.allow("ip") is False                                   # 第4次拒(边界另一侧)

def test_ratelimit_window_slides():
    clk = _Clock(); r = g.RateLimiter(2, 60, now_fn=clk)
    r.allow("ip"); r.allow("ip"); assert r.allow("ip") is False
    clk.t += 60                                                     # 窗口滑过
    assert r.allow("ip") is True

def test_ratelimit_per_ip_isolated():
    clk = _Clock(); r = g.RateLimiter(1, 60, now_fn=clk)
    assert r.allow("a") is True and r.allow("b") is True and r.allow("a") is False


# ---- DailyBudget：max 次边界 + 跨天重置 ----
def test_budget_spends_up_to_max():
    d = [datetime(2026, 7, 26, 10)]
    b = g.DailyBudget(2, now_fn=lambda: d[0])
    assert b.try_spend() is True and b.try_spend() is True         # 第2次仍可
    assert b.try_spend() is False                                  # 第3次超预算
    assert b.spent == 2

def test_budget_resets_next_day():
    d = [datetime(2026, 7, 26, 23)]
    b = g.DailyBudget(1, now_fn=lambda: d[0])
    assert b.try_spend() is True and b.try_spend() is False
    d[0] = datetime(2026, 7, 27, 0)                                # 跨 GMT+8 日界
    assert b.try_spend() is True

def test_budget_zero_denies_all():
    b = g.DailyBudget(0, now_fn=lambda: datetime(2026, 7, 26))
    assert b.try_spend() is False


# ---- option_cache_key 稳定/区分 ----
def test_cache_key_stable_and_distinct():
    assert g.option_cache_key("live", 2, ["bug"]) == g.option_cache_key("live", 2, ["bug"])
    assert g.option_cache_key("live", 2, ["bug"]) != g.option_cache_key("live", 3, ["bug"])
    assert g.option_cache_key("live", 2, ["bug"]) != g.option_cache_key("report", 2, ["bug"])


# ---- validate_clarify：options / requirement / 畸形 ----
def test_validate_options_ok():
    assert g.validate_clarify({"options": ["直播卡顿", "评分不准"]}) == []

def test_validate_options_boundary():
    assert g.validate_clarify({"options": []}) != []               # 0 个拒
    assert g.validate_clarify({"options": ["x"] * 9}) != []         # 9 个拒(>8)
    assert g.validate_clarify({"options": ["x"] * 8}) == []         # 8 个可(边界)

def test_validate_option_too_long():
    assert g.validate_clarify({"options": ["y" * 61]}) != []        # 61 字拒
    assert g.validate_clarify({"options": ["y" * 60]}) == []        # 60 字可

def test_validate_requirement_ok():
    assert g.validate_clarify({"requirement": {"kind": "bug", "page": "live", "text": "崩溃"}}) == []

def test_validate_requirement_bad_kind():
    assert g.validate_clarify({"requirement": {"kind": "hack", "text": "x"}}) != []

def test_validate_requirement_empty_text():
    assert g.validate_clarify({"requirement": {"kind": "bug", "text": "  "}}) != []

def test_validate_neither():
    assert g.validate_clarify({"foo": 1}) != []

def test_validate_non_dict():
    assert g.validate_clarify("x") != []
