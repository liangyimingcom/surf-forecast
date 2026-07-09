"""custom-spots R4 测试 —— 注册表驱动刷新 + 即时预算 + 频率上限 + 冷点回收。"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from web import db, refresh, spots

GMT8 = ZoneInfo("Asia/Shanghai")


def _fake_report(cfg, *, calibrated_at=None):
    return {"spot": cfg["spot"], "days": [{"date": "2026-06-26", "wdeg": [1]}],
            "history": {"date": "2026-06-25"}}


def test_active_registry_merges_default_and_dedups():
    db.reset_store()
    store = db.get_store()
    spots.create_spot(store, {"email": "a@sf.com", "level": "paid"}, "新点", 35.5, 121.5)
    cfgs = refresh.active_registry_spots(store)
    slugs = {c["slug"] for c in cfgs}
    assert "shandongtou" in slugs          # DEFAULT_SPOTS 兜底
    assert any(c["lat"] == 35.5 for c in cfgs)  # 用户浪点纳入


def test_scheduled_refresh_writes_cache_and_last_refresh():
    db.reset_store()
    store = db.get_store()
    s = spots.create_spot(store, {"email": "a@sf.com", "level": "paid"}, "P", 35.5, 121.5)
    writer = refresh.InMemoryCacheWriter()
    summary = refresh.scheduled_refresh(store, writer, report_fn=_fake_report)
    assert summary[s["slug"]] == "ok"
    assert writer.get(f"{s['slug']}/latest.json")["spot"] == "P"   # 写缓存
    assert store.get_registry(s["slug"])["last_refresh_at_gmt8"] is not None  # 回写


def test_budget_one_makes_new_spot_readable():
    db.reset_store()
    store = db.get_store()
    s = spots.create_spot(store, {"email": "a@sf.com", "level": "paid"}, "Q", 34.0, 122.0)
    row = store.get_registry(s["slug"])
    writer = refresh.InMemoryCacheWriter()
    refresh.budget_one(writer, row, report_fn=_fake_report)
    assert writer.get(f"{s['slug']}/latest.json") is not None   # 即时预算后立即可读


def test_refresh_budget_cap():
    db.reset_store()
    store = db.get_store()
    for i in range(5):
        store.upsert_registry({"slug": f"s{i}", "spot": f"S{i}", "lat": 35 + i, "lon": 120,
                               "days": 6, "dedup_key": f"k{i}", "ref_count": 1,
                               "status": "active", "refresh_enabled": True,
                               "last_viewed_at_gmt8": f"2026-06-2{i}T00:00:00"})
    cfgs = refresh.active_registry_spots(store, budget=2)
    assert len(cfgs) == 2          # 截断到预算上限
    # 按 last_viewed 降序：s4 最新在前
    assert cfgs[0]["slug"] == "s4"


def test_recycle_cold_spots():
    db.reset_store()
    store = db.get_store()
    old = (datetime.now(GMT8) - timedelta(days=20)).isoformat(timespec="seconds")
    store.upsert_registry({"slug": "cold", "spot": "C", "lat": 35, "lon": 120, "days": 6,
                           "dedup_key": "kc", "ref_count": 1, "status": "active",
                           "refresh_enabled": True, "last_viewed_at_gmt8": old})
    recycled = refresh.recycle_cold_spots(store, cold_days=14)
    assert "cold" in recycled
    assert store.list_active_registry() == []   # 冷点退出 active 刷新集
