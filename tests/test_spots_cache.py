"""custom-spots R3 测试 —— 按坐标解析 slug + 注册表缓存命中 + select 记忆。"""

from __future__ import annotations

from web import db, deps, spots


class FakeReader:
    def __init__(self, store):
        self.store = store

    def get(self, key):
        return self.store.get(key)


def test_resolve_slug_registry_first(monkeypatch):
    db.reset_store()
    store = db.get_store()
    spots.create_spot(store, {"email": "a@sf.com", "level": "paid"}, "石老人", 36.15, 120.65)
    slug = store.find_registry_by_coord(36.15, 120.65)["slug"]
    assert deps._resolve_slug(36.15, 120.65) == slug
    # 未注册坐标 → 回退 DEFAULT_SPOTS（山东头）或 None
    assert deps._resolve_slug(36.092, 120.468) == "shandongtou"  # DEFAULT_SPOTS 兜底


def test_get_report_cache_hit_for_custom_spot(monkeypatch):
    db.reset_store()
    store = db.get_store()
    s = spots.create_spot(store, {"email": "a@sf.com", "level": "paid"}, "自定义点", 35.5, 121.5)
    slug = s["slug"]
    # 预置缓存
    cache = {f"{slug}/latest.json": {"spot": "自定义点", "days": [{"date": "2026-06-26", "wdeg": [10]}]}}
    monkeypatch.setattr(deps, "_cache_reader", lambda: FakeReader(cache))
    rep = deps.get_report(35.5, 121.5, 3, "自定义点")
    assert rep["spot"] == "自定义点" and rep["days"][0]["wdeg"] == [10]  # 命中缓存，未打引擎


def test_get_report_miss_falls_back(monkeypatch):
    db.reset_store()
    # 无缓存 reader → 回退引擎（用 stub 避免真实 HTTP）
    monkeypatch.setattr(deps, "_cache_reader", lambda: None)
    called = {}

    def fake_build(lat, lon, days, spot, **kw):
        called["hit"] = True
        return "CTX"

    monkeypatch.setattr(deps.analyze, "build_context", fake_build)
    monkeypatch.setattr(deps.render, "render_json", lambda ctx: {"spot": "x", "fallback": True})
    rep = deps.get_report(10.0, 10.0, 3, "x")
    assert rep["fallback"] is True and called.get("hit")


def test_select_persists_last_viewed():
    db.reset_store()
    store = db.get_store()
    s = spots.create_spot(store, {"email": "a@sf.com", "level": "paid"}, "P", 34.8, 122.3)
    spots.select_spot(store, {"email": "a@sf.com", "level": "paid"}, s["slug"])
    assert store.get_last_selected("a@sf.com") == s["slug"]
    # registry last_viewed 已更新
    assert store.get_registry(s["slug"])["last_viewed_at_gmt8"] is not None
