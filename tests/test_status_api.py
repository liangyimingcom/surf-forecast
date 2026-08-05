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


@pytest.fixture(autouse=True)
def _clear_agg_cache():
    """/api/status 走 app._agg_cache（SF_AGG_TTL 默认 300s）——进程内单例会把上一个
    测试的响应带给下一个测试（同 fixture 数据时看不出来，换数据就串）。每例前后清空。"""
    A._agg_cache.clear()
    yield
    A._agg_cache.clear()


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


# ============================================================
# R1.2：失败原因贯通到 /api/status
# manifest 里 failed 本就是 {slug: 原因}，旧版只暴露 slug 列表 → 站长看不出
# 是上游格点无数据、validate 不过、还是取数异常，无法判断该找上游还是找代码。
# ============================================================
def test_status_exposes_failed_reasons(client, wired):
    body = client.get("/api/status").json()
    r = body["refresh"]
    # 向后兼容：failed 仍是 slug 列表（前端 join('、') 与既有契约不破）
    assert r["failed"] == ["m"]
    # 新增：带原因的明细
    assert r["failed_detail"] == {"m": "skipped"}


def test_status_failed_detail_empty_when_no_failure(client, monkeypatch):
    """无失败点时 failed_detail 为空对象（不是 None，前端可直接 Object.keys）。"""
    manifest = {"date": TODAY, "kind": "main", "run_at": FRESH,
                "expected": ["a"], "succeeded": ["a"], "failed": {},
                "history": []}
    monkeypatch.setattr(A.db, "get_store", lambda: _Store())
    monkeypatch.setattr(A.deps, "_cache_reader",
                        lambda: _Reader({"a": _rep(7.0), "manifest.json": manifest}))
    r = client.get("/api/status").json()["refresh"]
    assert r["failed"] == [] and r["failed_detail"] == {}
