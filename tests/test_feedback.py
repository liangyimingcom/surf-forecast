"""feedback 单测 —— 四档反馈/持久化(GMT+8)/偏差校准(不改原分)/接口鉴权（F4/F5/F6）。"""

import pytest
from fastapi.testclient import TestClient

from web import app as app_module
from web import db, feedback


@pytest.fixture(autouse=True)
def _reset():
    db.reset_store()
    yield
    db.reset_store()


@pytest.fixture
def client():
    return TestClient(app_module.app)


def _auth(client):
    client.post("/api/auth/register", json={"email": "v@b.com", "password": "secret123"})
    client.post("/api/auth/login", json={"email": "v@b.com", "password": "secret123"})


# —— 服务层 ——
def test_record_vote_feedback_text():
    store = db.get_store()
    r = feedback.record_vote(store, "v@b.com", "山东头", "2026-06-20", "optimistic")
    assert "下调半档" in r["feedback"]
    assert store.votes_for("v@b.com", "山东头")[0]["created_at_gmt8"].endswith("GMT+8")


def test_record_vote_invalid_kind():
    with pytest.raises(feedback.FeedbackError):
        feedback.record_vote(db.get_store(), "v@b.com", "山东头", "2026-06-20", "bogus")


def test_bias_insufficient_then_dominant():
    store = db.get_store()
    # 仅 2 条 → 不足
    for _ in range(2):
        feedback.record_vote(store, "v@b.com", "山东头", "2026-06-20", "optimistic")
    assert feedback.compute_bias(store, "v@b.com", "山东头")["bias"] == "insufficient"
    # 再补到 3 条偏乐观 → 偏乐观建议
    feedback.record_vote(store, "v@b.com", "山东头", "2026-06-21", "optimistic")
    b = feedback.compute_bias(store, "v@b.com", "山东头")
    assert b["bias"] == "偏乐观" and "下调半档" in b["suggestion"]
    assert "不修改原始评分" in b["note"]   # F6 不篡改原分


def test_bias_excludes_noidea():
    store = db.get_store()
    for _ in range(3):
        feedback.record_vote(store, "v@b.com", "点", "2026-06-20", "noidea")
    # 全是 noidea → 不计入偏差，样本不足
    assert feedback.compute_bias(store, "v@b.com", "点")["bias"] == "insufficient"


# —— 接口层 ——
def test_vote_requires_auth(client):
    r = client.post("/api/accuracy/vote", json={"spot": "山东头", "date": "2026-06-20", "kind": "accurate"})
    assert r.status_code == 401


def test_vote_and_bias_endpoints(client):
    _auth(client)
    for _ in range(3):
        assert client.post("/api/accuracy/vote",
                           json={"spot": "山东头", "date": "2026-06-20", "kind": "conservative"}).status_code == 200
    b = client.get("/api/accuracy/bias?spot=山东头").json()
    assert b["bias"] == "偏保守" and "上调半档" in b["suggestion"]
