"""P1.3 单测：会员锁开关 + 会员门原语双态 + 微信占位 501 + User 可空字段。"""
from types import SimpleNamespace as NS

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import web.app as A
import web.auth as auth
import web.flags as F


@pytest.fixture
def client():
    return TestClient(A.app)


def _req(cookie=None):
    return NS(cookies=({F_COOKIE: cookie} if cookie else {}))


F_COOKIE = "sf_session"


class _Store:
    def __init__(self, member=False):
        self._m = member

    def get_session_email(self, token):
        return "u@x.com" if token else None

    def get_user(self, email):
        return {"userId": "u1", "email": email, "level": "free",
                "membership": "member" if self._m else "free"}


# —— 开关 ——
def test_lock_default_off(monkeypatch):
    monkeypatch.delenv("SF_MEMBER_LOCK", raising=False)
    assert F.member_lock_enabled() is False
    assert F.get_flags() == {"member_lock_enabled": False}


def test_lock_on_when_env_set(monkeypatch):
    monkeypatch.setenv("SF_MEMBER_LOCK", "true")
    assert F.member_lock_enabled() is True


# —— 会员门原语双态 ——
def test_gate_off_passthrough_anon(monkeypatch):
    monkeypatch.delenv("SF_MEMBER_LOCK", raising=False)
    assert F.member_gate(_req()) is None            # 一期匿名放行


def test_gate_on_anon_401(monkeypatch):
    monkeypatch.setenv("SF_MEMBER_LOCK", "1")
    with pytest.raises(HTTPException) as e:
        F.member_gate(_req())
    assert e.value.status_code == 401


def test_gate_on_free_user_402(monkeypatch):
    monkeypatch.setenv("SF_MEMBER_LOCK", "1")
    monkeypatch.setattr(F.db, "get_store", lambda: _Store(member=False))
    with pytest.raises(HTTPException) as e:
        F.member_gate(_req("tok"))
    assert e.value.status_code == 402               # 登录但非会员


def test_gate_on_member_ok(monkeypatch):
    monkeypatch.setenv("SF_MEMBER_LOCK", "1")
    monkeypatch.setattr(F.db, "get_store", lambda: _Store(member=True))
    u = F.member_gate(_req("tok"))
    assert u and u["membership"] == "member"


# —— 端点 ——
def test_flags_endpoint_public(client, monkeypatch):
    monkeypatch.delenv("SF_MEMBER_LOCK", raising=False)
    r = client.get("/api/flags")
    assert r.status_code == 200 and r.json()["member_lock_enabled"] is False


def test_wechat_placeholder_501(client):
    assert client.post("/api/auth/wechat/qr").status_code == 501
    assert client.get("/api/auth/wechat/status").status_code == 501


# —— User 可空字段（二期微信预埋）——
def test_register_user_has_wechat_membership_fields():
    class _S:
        def __init__(self): self.saved = None
        def get_user(self, e): return None
        def put_user(self, u): self.saved = u
    s = _S()
    auth.register(s, "a@b.com", "pw12345")
    assert s.saved["wechat_openid"] is None and s.saved["membership"] == "free"
