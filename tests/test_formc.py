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


# —— 解耦回归：冷点回收(refresh_enabled=False)不得让目录/直播消失 ——
def test_cold_spot_still_listed_but_not_refreshed(client):
    """根因回归：list_listed_registry(目录/直播) 与 list_active_registry(刷新/回收) 解耦。
    冷点回收把 refresh_enabled=False 后，浪点仍须在 /api/catalog + /api/cams 可见，
    但退出刷新集(list_active_registry)。防「部署两周后目录/直播静默归零」复发。"""
    _seed(); _auth(client)
    store = db.get_store()
    store.set_refresh_enabled("sl74", False)   # 模拟冷点回收
    # 刷新集：sl74 已退出
    active = {r["slug"] for r in store.list_active_registry()}
    assert "sl74" not in active
    # 公开可见集：sl74 仍在
    listed = {r["slug"] for r in store.list_listed_registry()}
    assert "sl74" in listed
    # API：目录 + 直播仍含 sl74
    cat = {c["slug"] for c in client.get("/api/catalog").json()["catalog"]}
    cams = {c["slug"] for c in client.get("/api/cams").json()["cams"]}
    assert "sl74" in cat and "sl74" in cams


# —— http 明文源须被隐藏（HTTPS 生产 mixed-content 拦截，数据诚实）——
def test_http_live_src_excluded(client):
    from web import seed as _seed_mod
    snap = {"spots": [
        {"slug": "hp1", "name": "明文源", "city": "X", "region_cn": "其他",
         "lat": 22.5, "lon": 114.5, "facing": 135, "facing_calibrated": False,
         "live_src": "http://isurflive.c-pan.cn/live/x.m3u8", "post_url": None},
    ]}
    _seed_mod.seed_store(db.get_store(), _seed_mod.build_registry_rows(snap))
    _auth(client)
    cams = {c["slug"] for c in client.get("/api/cams").json()["cams"]}
    cat = {c["slug"]: c for c in client.get("/api/catalog").json()["catalog"]}
    assert "hp1" not in cams                 # http 源不进直播
    assert cat["hp1"]["has_live"] is False   # 目录 has_live 也不认 http


# —— B1 需求库/反馈落库 + status 状态机 ——
def test_feedback_submit_and_store(client):
    r = client.post("/api/feedback", json={"kind": "improve", "page": "catalog", "text": "按距离排序"})
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "new" and j["id"] and j["claim_code"]
    store = db.get_store()
    news = store.list_feedback("new")
    assert any(x["id"] == j["id"] and x["text"] == "按距离排序" for x in news)
    # 状态机：采纳 → 退出 new 集
    store.set_feedback_status(j["id"], "accepted")
    assert all(x["id"] != j["id"] for x in store.list_feedback("new"))
    assert any(x["id"] == j["id"] for x in store.list_feedback("accepted"))


def test_feedback_empty_text_422(client):
    assert client.post("/api/feedback", json={"text": ""}).status_code == 422


def test_feedback_text_length_capped(client):
    # 长度上限由 Pydantic max_length=2000 强制：超限直接 422（反滥用/RP-mc1）
    assert client.post("/api/feedback", json={"text": "x" * 5000}).status_code == 422
    assert client.post("/api/feedback", json={"text": "x" * 2000}).status_code == 200


# —— B4 更新日志 + 认领码查进展 ——
def test_changelog_public(client):
    j = client.get("/api/changelog").json()
    assert "releases" in j and isinstance(j["releases"], list)


def test_track_claim_flow(client):
    claim = client.post("/api/feedback", json={"text": "track流程"}).json()["claim_code"]
    r = client.get("/api/feedback/track", params={"claim": claim})
    assert r.status_code == 200 and r.json()["status"] == "new"
    # 认领码只回状态/时间/类别，不含文本(防泄漏他人内容)
    assert "text" not in r.json()


def test_track_bad_claim_404(client):
    assert client.get("/api/feedback/track", params={"claim": "nope"}).status_code == 404
