"""形态C整合单测 —— 浪点导入 seed / /api/catalog / /api/cams / /api/catalog/scores 契约 + 401。"""
import pytest
from fastapi.testclient import TestClient

from web import app as app_module
from web import db, seed


@pytest.fixture(autouse=True)
def _reset():
    db.reset_store()
    yield
    db.reset_store()


@pytest.fixture
def client():
    return TestClient(app_module.app)


SNAP = {"spots": [
    {"slug": "sl74", "name": "石老人", "city": "QingDao", "region_cn": "山东",
     "lat": 36.0958, "lon": 120.4786, "facing": 157, "facing_calibrated": False,
     "live_src": "https://isurfvideo.c-pan.cn/live/slr.m3u8", "post_url": "/p/a.jpg"},
    {"slug": "sl50", "name": "大东海", "city": "HaiNan", "region_cn": "海南",
     "lat": 18.2207, "lon": 109.5278, "facing": 110, "facing_calibrated": False,
     "live_src": None, "post_url": None},   # 无直播 → 不进 cams
]}


def _auth(client):
    client.post("/api/auth/register", json={"email": "c@t.com", "password": "secret123"})
    client.post("/api/auth/login", json={"email": "c@t.com", "password": "secret123"})


def _seed():
    seed.seed_store(db.get_store(), seed.build_registry_rows(SNAP))


# —— seed 纯函数 ——
def test_build_registry_rows_shape():
    rows = seed.build_registry_rows(SNAP)
    assert len(rows) == 2
    r = {x["slug"]: x for x in rows}["sl74"]
    assert r["spot"] == "石老人" and r["spot_facing_deg"] == 157.0
    assert r["region_cn"] == "山东" and r["source"] == "shilaoren"
    assert r["live_src"].endswith(".m3u8") and r["status"] == "active"


def test_build_skips_missing_coord():
    snap = {"spots": [{"slug": "x", "name": "无坐标", "lat": None, "lon": None}]}
    assert seed.build_registry_rows(snap) == []


# —— 401 保护 ——
def test_catalog_requires_auth(client):
    assert client.get("/api/catalog").status_code == 401


def test_cams_requires_auth(client):
    assert client.get("/api/cams").status_code == 401


def test_catalog_scores_requires_auth(client):
    assert client.get("/api/catalog/scores").status_code == 401


# —— 契约 ——
def test_catalog_lists_seeded_spots(client):
    _seed(); _auth(client)
    j = client.get("/api/catalog").json()
    cat = {c["slug"]: c for c in j["catalog"]}
    assert set(cat) == {"sl74", "sl50"}
    assert cat["sl74"]["region"] == "山东" and cat["sl74"]["has_live"] is True
    assert cat["sl50"]["has_live"] is False
    assert cat["sl74"]["facing_calibrated"] is False


def test_cams_only_with_live_src(client):
    _seed(); _auth(client)
    cams = client.get("/api/cams").json()["cams"]
    slugs = {c["slug"] for c in cams}
    assert "sl74" in slugs and "sl50" not in slugs   # sl50 无 live_src
    assert cams[0]["live_src"].endswith(".m3u8")


def test_catalog_scores_no_cache(client):
    _seed(); _auth(client)
    j = client.get("/api/catalog/scores").json()
    assert j["cached"] is False and j["scores"] == {}
