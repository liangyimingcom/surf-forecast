"""web 后端单测 —— 鉴权流程/401保护/report含wdeg/配额钳制（web W1/W2/W3/W4/W9）。"""

import pytest
from fastapi.testclient import TestClient

from web import app as app_module
from web import db, deps


@pytest.fixture(autouse=True)
def _reset():
    db.reset_store()
    yield
    db.reset_store()


@pytest.fixture
def client():
    return TestClient(app_module.app)


@pytest.fixture
def fake_report(monkeypatch):
    """monkeypatch 引擎，避免触网；返回含 wdeg 的最小 REPORT。"""
    captured = {}

    def _fake(lat, lon, days, spot):
        captured["days"] = days
        return {"spot": spot, "coord": [lat, lon], "calibratedAt": "2026-06-20 10:00 GMT+8",
                "days": [{"date": "2026-06-20", "wdeg": [337, 312], "score": 6.4}],
                "ranking": [0], "history": None}
    monkeypatch.setattr(deps, "get_report", _fake)
    return captured


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_register_login_logout(client):
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    assert r.status_code == 200 and r.json()["level"] == "free"
    assert "passwordHash" not in r.json()           # 绝不泄露哈希
    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "secret123"})
    assert r.status_code == 200 and "sf_session" in r.cookies
    assert client.post("/api/auth/logout").status_code == 200


def test_register_duplicate_409(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    assert r.status_code == 409


def test_login_wrong_password_401(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "WRONG999"})
    assert r.status_code == 401


def test_report_requires_auth_401(client):
    # W1：未登录无法获取浪报数据
    r = client.get("/api/report?lat=36.092&lon=120.468&spot=山东头")
    assert r.status_code == 401


def test_report_returns_wdeg_when_authed(client, fake_report):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    client.post("/api/auth/login", json={"email": "a@b.com", "password": "secret123"})
    r = client.get("/api/report?lat=36.092&lon=120.468&spot=山东头&days=3")
    assert r.status_code == 200
    body = r.json()
    assert "wdeg" in body["days"][0]               # W4 红线：含 wdeg
    assert body["days"][0]["wdeg"][0] == 337


def test_free_tier_day_clamp(client, fake_report):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    client.post("/api/auth/login", json={"email": "a@b.com", "password": "secret123"})
    client.get("/api/report?lat=36.092&lon=120.468&days=7")  # free 请求 7 天
    assert fake_report["days"] == 3                 # W3：free 钳到 3 天


def test_bad_coord_400(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    client.post("/api/auth/login", json={"email": "a@b.com", "password": "secret123"})
    r = client.get("/api/report?lat=999&lon=120&days=3")
    assert r.status_code == 400


def test_report_502_on_datasource_failure(client, monkeypatch):
    """W2.1 故障降级：get_report 抛错(如 Open-Meteo 故障) → 502 + 可读 detail（非 500 裸崩、非白屏源）。"""
    client.post("/api/auth/register", json={"email": "d@b.com", "password": "secret123"})
    client.post("/api/auth/login", json={"email": "d@b.com", "password": "secret123"})

    def _boom(lat, lon, days, spot):
        from surf_forecast.fetch import DataSourceError
        raise DataSourceError("Open-Meteo 502", ["*"])
    monkeypatch.setattr(deps, "get_report", _boom)
    r = client.get("/api/report?lat=36.092&lon=120.468&spot=x&days=3")
    assert r.status_code == 502
    assert "浪报生成失败" in r.json()["detail"]


def test_history_502_on_failure(client, monkeypatch):
    client.post("/api/auth/register", json={"email": "d@b.com", "password": "secret123"})
    client.post("/api/auth/login", json={"email": "d@b.com", "password": "secret123"})

    def _boom(lat, lon, days, spot):
        raise RuntimeError("history upstream down")
    monkeypatch.setattr(deps, "get_history", _boom)
    r = client.get("/api/report/history?lat=36.092&lon=120.468&spot=x")
    assert r.status_code == 502
