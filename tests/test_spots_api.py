"""custom-spots R2 测试 —— /api/spots CRUD + 401 + 配额 + 去重 + XSS。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from web import db
from web.app import app


def _client_logged_in(level="free"):
    db.reset_store()
    c = TestClient(app)
    c.post("/api/auth/register", json={"email": "u@sf.com", "password": "pass123", "level": level})
    c.post("/api/auth/login", json={"email": "u@sf.com", "password": "pass123"})
    return c


def test_spots_require_auth():
    db.reset_store()
    c = TestClient(app)
    assert c.get("/api/spots").status_code == 401
    assert c.post("/api/spots", json={"name": "x", "lat": 36, "lon": 120}).status_code == 401
    assert c.delete("/api/spots/foo").status_code == 401


def test_spot_create_list_select_delete():
    c = _client_logged_in()
    r = c.post("/api/spots", json={"name": "山东头", "lat": 36.092, "lon": 120.468})
    assert r.status_code == 200
    slug = r.json()["slug"]
    assert r.json()["threshold_note"].startswith("已标定")  # 黄海
    # 列表含 1 个
    lst = c.get("/api/spots").json()["spots"]
    assert len(lst) == 1 and lst[0]["slug"] == slug
    # 选中 → selected 标志
    assert c.post(f"/api/spots/{slug}/select").status_code == 200
    assert c.get("/api/spots").json()["spots"][0]["selected"] is True
    # 软删 → 列表空
    assert c.delete(f"/api/spots/{slug}").status_code == 200
    assert c.get("/api/spots").json()["spots"] == []


def test_spot_quota_free_limit():
    c = _client_logged_in(level="free")
    for i in range(3):
        assert c.post("/api/spots", json={"name": f"P{i}", "lat": 36 + i * 0.1, "lon": 120}).status_code == 200
    # 第 4 个超 free 配额
    r = c.post("/api/spots", json={"name": "P4", "lat": 37, "lon": 121})
    assert r.status_code == 409 and "上限" in r.json()["detail"]


def test_spot_name_unique_and_xss_escaped():
    c = _client_logged_in()
    c.post("/api/spots", json={"name": "Dup", "lat": 36.0, "lon": 120.0})
    # 重名 409
    assert c.post("/api/spots", json={"name": "Dup", "lat": 35.0, "lon": 121.0}).status_code == 409
    # XSS 名称被转义存储
    r = c.post("/api/spots", json={"name": "<b>x</b>", "lat": 34.5, "lon": 122.0})
    assert r.status_code == 200 and "&lt;b&gt;" in r.json()["name"]


def test_spot_invalid_coord_400():
    c = _client_logged_in()
    assert c.post("/api/spots", json={"name": "Bad", "lat": 95, "lon": 120}).status_code == 400


def test_spot_rename_keeps_slug():
    c = _client_logged_in()
    slug = c.post("/api/spots", json={"name": "Old", "lat": 36.0, "lon": 120.0}).json()["slug"]
    r = c.patch(f"/api/spots/{slug}", json={"name": "New"})
    assert r.status_code == 200 and r.json()["slug"] == slug and r.json()["name"] == "New"


def test_spot_dedup_shares_slug_across_users():
    db.reset_store()
    store = db.get_store()
    from web import spots
    u1 = {"email": "a@sf.com", "level": "paid"}
    u2 = {"email": "b@sf.com", "level": "paid"}
    s1 = spots.create_spot(store, u1, "A点", 36.092, 120.468)
    s2 = spots.create_spot(store, u2, "B点", 36.0920, 120.4680)  # 同坐标
    assert s1["slug"] == s2["slug"]                       # 共享 slug
    assert store.get_registry(s1["slug"])["ref_count"] == 2  # ref 计数


def test_uncalibrated_note():
    db.reset_store()
    store = db.get_store()
    from web import spots
    s = spots.create_spot(store, {"email": "c@sf.com", "level": "paid"}, "悉尼", -33.9, 151.2)
    assert "未标定" in s["threshold_note"]
