# -*- coding: utf-8 -*-
"""W3 cache.py TTL 单测：边界双侧钉死 + LRU + 停用 + get_report memo 集成。"""
from web import cache, deps


class _Clock:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t


# ---- TTL 边界（双侧钉死 + mutation：改 >= 为 > 或 ttl±1 须变红）----
def test_ttl_hit_before_expiry():
    clk = _Clock(); c = cache.TTLCache(10, now_fn=clk)
    c.set("k", "v"); clk.t += 9.999
    assert c.get("k") == "v"            # age<ttl 命中

def test_ttl_expires_at_ttl_boundary():
    clk = _Clock(); c = cache.TTLCache(10, now_fn=clk)
    c.set("k", "v"); clk.t += 10.0
    assert c.get("k") is None           # age==ttl 即过期(边界另一侧)

def test_ttl_expires_after():
    clk = _Clock(); c = cache.TTLCache(10, now_fn=clk)
    c.set("k", "v"); clk.t += 10.001
    assert c.get("k") is None


# ---- 停用 ----
def test_disabled_ttl_zero():
    c = cache.TTLCache(0)
    c.set("k", "v"); assert c.get("k") is None and len(c) == 0

def test_disabled_ttl_negative():
    c = cache.TTLCache(-5)
    c.set("k", "v"); assert c.get("k") is None


# ---- LRU 淘汰（容量边界双侧）----
def test_lru_evicts_oldest_over_capacity():
    c = cache.TTLCache(100, max_items=2)
    c.set("a", 1); c.set("b", 2); c.set("c", 3)   # 超 2 → 淘汰最久未用 a
    assert c.get("a") is None and c.get("b") == 2 and c.get("c") == 3
    assert len(c) == 2

def test_lru_hit_refreshes_recency():
    c = cache.TTLCache(100, max_items=2)
    c.set("a", 1); c.set("b", 2)
    assert c.get("a") == 1                          # 刷新 a 近用
    c.set("c", 3)                                   # 淘汰最久未用 b(非 a)
    assert c.get("a") == 1 and c.get("b") is None and c.get("c") == 3


# ---- get_report memo 集成：TTL 窗口内不重算 ----
def test_get_report_memo_avoids_recompute(monkeypatch):
    clk = _Clock()
    monkeypatch.setattr(deps, "_report_cache", cache.TTLCache(60, now_fn=clk))
    monkeypatch.setattr(deps, "_cache_reader", lambda: None)      # 无 S3 → 走实算
    monkeypatch.setattr(deps, "_resolve_slug", lambda lat, lon: "sl-test")
    calls = {"n": 0}

    class _Ctx: pass
    def _bctx(*a, **k):
        calls["n"] += 1; return _Ctx()
    monkeypatch.setattr(deps.analyze, "build_context", _bctx)
    monkeypatch.setattr(deps.render, "render_json", lambda ctx: {"spot": "x", "days": [1]})

    r1 = deps.get_report(36.0, 120.0, 3, "x")
    r2 = deps.get_report(36.0, 120.0, 3, "x")        # TTL 内 → memo 命中
    assert r1 == r2 == {"spot": "x", "days": [1]}
    assert calls["n"] == 1                            # 只算一次
    clk.t += 61                                       # 过期
    deps.get_report(36.0, 120.0, 3, "x")
    assert calls["n"] == 2                            # 过期后重算

def test_get_report_memo_disabled_by_default(monkeypatch):
    # 默认 _report_cache ttl=0(停用) → 每次都算(不改既有行为)
    monkeypatch.setattr(deps, "_report_cache", cache.TTLCache(0))
    monkeypatch.setattr(deps, "_cache_reader", lambda: None)
    monkeypatch.setattr(deps, "_resolve_slug", lambda lat, lon: "sl-test")
    calls = {"n": 0}
    def _bctx(*a, **k):
        calls["n"] += 1; return object()
    monkeypatch.setattr(deps.analyze, "build_context", _bctx)
    monkeypatch.setattr(deps.render, "render_json", lambda ctx: {"days": [1]})
    deps.get_report(36.0, 120.0, 3, "x"); deps.get_report(36.0, 120.0, 3, "x")
    assert calls["n"] == 2                            # 停用→每次算
