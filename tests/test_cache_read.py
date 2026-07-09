"""读写解耦「读」侧单测 —— 缓存命中返回/未命中回退/坐标匹配（D6, R5.6）。"""

from web import deps, refresh


def test_find_spot_matches_registered():
    sp = refresh.find_spot(36.092, 120.468)
    assert sp is not None and sp["slug"] == "shandongtou"
    assert refresh.find_spot(0.0, 0.0) is None


def test_get_report_serves_cache_hit(monkeypatch):
    cached = {"spot": "青岛山东头", "days": [{"wdeg": [337], "score": 8.0}], "cached": True}

    class FakeReader:
        def get(self, key):
            assert key == "shandongtou/latest.json"
            return cached

    monkeypatch.setattr(deps, "_cache_reader", lambda: FakeReader())
    # 命中上架浪点坐标 → 直接返回缓存，不触引擎
    out = deps.get_report(36.092, 120.468, 3, "青岛山东头")
    assert out["cached"] is True


def test_get_report_falls_back_on_miss(monkeypatch):
    class EmptyReader:
        def get(self, key):
            return None

    monkeypatch.setattr(deps, "_cache_reader", lambda: EmptyReader())
    monkeypatch.setattr(deps.analyze, "build_context", lambda *a, **k: "CTX")
    monkeypatch.setattr(deps.render, "render_json", lambda ctx: {"fallback": True})
    out = deps.get_report(36.092, 120.468, 3, "青岛山东头")
    assert out["fallback"] is True


def test_get_report_custom_coord_always_live(monkeypatch):
    # 自定义坐标（非上架）即使有 reader 也直接实算
    monkeypatch.setattr(deps, "_cache_reader", lambda: object())
    monkeypatch.setattr(deps.analyze, "build_context", lambda *a, **k: "CTX")
    monkeypatch.setattr(deps.render, "render_json", lambda ctx: {"live": True})
    out = deps.get_report(10.0, 20.0, 3, "某无名点")
    assert out["live"] is True
