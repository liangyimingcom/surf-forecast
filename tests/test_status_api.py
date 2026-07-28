"""R2 §2 接口测试：/api/status 公开组装 + catalog 的 is_test 过滤与 X-Test-Access。"""
import datetime as dt

import pytest
from fastapi.testclient import TestClient

import web.app as A

GMT8 = dt.timezone(dt.timedelta(hours=8))
TODAY = dt.datetime.now(GMT8).strftime("%Y-%m-%d")
FRESH = f"{TODAY} 02:00 GMT+8"

REG = [
    {"slug": "a", "spot": "甲滩", "region_cn": "广东", "lat": 22.0, "lon": 114.0,
     "op_status": "open"},
    {"slug": "m", "spot": "乙滩", "region_cn": "广东", "lat": 22.1, "lon": 114.1,
     "op_status": "maintenance"},
    {"slug": "t", "spot": "E2E点", "region_cn": "其他", "lat": 36.1, "lon": 120.5,
     "is_test": True},
]


def _rep(score):
    return {"spot": "X", "calibratedAt": FRESH, "ranking": [0],
            "days": [{"date": TODAY, "week": "周二", "score": score, "best": True,
                      "window": "早7-9点", "board": "鱼板", "novice": "适合",
                      "dawnWind": "离岸风", "hs": [1.0], "tp": [8], "tp2": [9]}]}


class _Reader:
    def __init__(self, data):
        self.data = data

    def get(self, key):
        if key == "manifest.json":
            return self.data.get("manifest.json")
        return self.data.get(key.split("/")[0])


class _Store:
    def list_listed_registry(self):
        return REG


@pytest.fixture
def client():
    return TestClient(A.app)


@pytest.fixture
def wired(monkeypatch):
    manifest = {"date": TODAY, "kind": "main", "run_at": FRESH,
                "expected": ["a", "m"], "succeeded": ["a"], "failed": {"m": "skipped"},
                "history": [{"run_id": f"{TODAY}-main", "run_at": FRESH, "kind": "main",
                             "expected_n": 2, "ok_n": 1, "duration_s": 60.0}]}
    monkeypatch.setattr(A.db, "get_store", lambda: _Store())
    monkeypatch.setattr(A.deps, "_cache_reader",
                        lambda: _Reader({"a": _rep(7.0), "manifest.json": manifest}))


def test_status_public_shape(client, wired):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["refresh"]["is_today"] is True
    assert body["refresh"]["succeeded"] == 1 and body["refresh"]["expected"] == 2
    gd = next(x for x in body["regions"] if x["region"] == "广东")
    assert gd["available"] is True and gd["pool"] == 1   # 维护点不进可推荐池
    assert all(x["region"] != "其他" or x["spots"] == 0 for x in body["regions"]) or \
        not any(x["region"] == "其他" for x in body["regions"])  # 测试点不产生区域
    assert body["history"][0]["ok_n"] == 1


def test_catalog_hides_test_spots_by_default(client, wired):
    slugs = [s["slug"] for s in client.get("/api/catalog").json()["catalog"]]
    assert "t" not in slugs and "a" in slugs and "m" in slugs  # 维护点在目录（带徽标）


def test_catalog_test_access_key(client, wired, monkeypatch):
    monkeypatch.setenv("SF_TEST_ACCESS_KEY", "k123")
    slugs = [s["slug"] for s in client.get(
        "/api/catalog", headers={"X-Test-Access": "k123"}).json()["catalog"]]
    assert "t" in slugs
    # 错密钥不可见
    slugs2 = [s["slug"] for s in client.get(
        "/api/catalog", headers={"X-Test-Access": "wrong"}).json()["catalog"]]
    assert "t" not in slugs2


def test_catalog_no_key_configured_never_shows_test(client, wired, monkeypatch):
    monkeypatch.delenv("SF_TEST_ACCESS_KEY", raising=False)
    slugs = [s["slug"] for s in client.get(
        "/api/catalog", headers={"X-Test-Access": ""}).json()["catalog"]]
    assert "t" not in slugs
