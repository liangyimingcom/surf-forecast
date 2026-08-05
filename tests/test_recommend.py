"""P1.1 区域推荐单测：只排当日新鲜点 + 诚实降级（边界双侧钉死）+ 公开端点。"""
import datetime as dt

import pytest
from fastapi.testclient import TestClient

import web.app as A
import web.recommend as R

GMT8 = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime(2026, 7, 27, 10, 0, tzinfo=GMT8)
FRESH = "2026-07-27 02:00 GMT+8"
STALE = "2026-07-25 02:00 GMT+8"  # 两天前


def _rep(cal, score, *, window="早7-9点", board="鱼板", dawn="离岸风", hs=1.2, tp=9.0):
    return {
        "spot": "X", "calibratedAt": cal, "ranking": [0],
        "days": [{
            "date": cal[:10], "week": "周一", "score": score, "best": True,
            "window": window, "board": board, "novice": "适合下水",
            "dawnWind": dawn, "hs": [hs, hs - 0.1], "tp": [tp - 1], "tp2": [tp],
        }],
    }


class _Reader:
    def __init__(self, data):  # data: slug -> report | Exception
        self.data = data

    def get(self, key):
        slug = key.split("/")[0]
        v = self.data.get(slug)
        if isinstance(v, Exception):
            raise v
        return v


REG = [
    {"slug": "a", "spot": "甲滩", "region_cn": "广东"},
    {"slug": "b", "spot": "乙滩", "region_cn": "广东"},
    {"slug": "c", "spot": "丙滩", "region_cn": "广东"},
    {"slug": "z", "spot": "外省", "region_cn": "海南"},
]


def test_ranks_fresh_by_score_desc_with_alternatives():
    reader = _Reader({"a": _rep(FRESH, 6.0), "b": _rep(FRESH, 8.2), "c": _rep(FRESH, 7.1)})
    out = R.build_recommendation("广东", REG, reader, now=NOW)
    assert out["best"]["spot_slug"] == "b" and out["best"]["score"] == 8.2
    assert [a["spot_slug"] for a in out["alternatives"]] == ["c", "a"]  # 次高两条
    assert out["degraded"] is False  # fresh==total（3/3 边界）


def test_alternatives_capped_at_two():
    reg = REG[:3] + [{"slug": "d", "spot": "丁", "region_cn": "广东"}]
    reader = _Reader({k: _rep(FRESH, s) for k, s in [("a", 5), ("b", 8), ("c", 7), ("d", 6)]})
    out = R.build_recommendation("广东", reg, reader, now=NOW)
    assert len(out["alternatives"]) == 2


def test_stale_spot_excluded_and_degraded():
    reader = _Reader({"a": _rep(FRESH, 6.0), "b": _rep(STALE, 9.9), "c": _rep(STALE, 9.8)})
    out = R.build_recommendation("广东", REG, reader, now=NOW)
    assert out["best"]["spot_slug"] == "a"          # 陈旧的高分被排除
    assert out["fresh_count"] == 1 and out["total_count"] == 3
    assert out["degraded"] is True                   # fresh < total


def test_zero_fresh_degraded_best_none():
    reader = _Reader({"a": _rep(STALE, 8), "b": _rep(STALE, 9)})
    out = R.build_recommendation("广东", REG, reader, now=NOW)
    assert out["best"] is None and out["alternatives"] == []
    assert out["degraded"] is True and out["fresh_count"] == 0


def test_reader_none_degraded():
    out = R.build_recommendation("广东", REG, None, now=NOW)
    assert out["best"] is None and out["degraded"] is True


def test_bad_cache_does_not_crash():
    reader = _Reader({"a": RuntimeError("half-write"), "b": _rep(FRESH, 7.0)})
    out = R.build_recommendation("广东", REG, reader, now=NOW)
    assert out["best"]["spot_slug"] == "b"           # 坏缓存被隔离，不拖垮


def test_headline_and_key_factors():
    reader = _Reader({"b": _rep(FRESH, 8.0, window="早7-9点", board="鱼板", dawn="离岸风", hs=1.2, tp=9.0)})
    out = R.build_recommendation("广东", REG, reader, now=NOW)
    assert out["best"]["headline"] == "早7-9点到，带鱼板"
    assert out["best"]["key_factors"] == ["1.2m浪", "离岸风", "Tp9s"]


def test_empty_region_uses_all():
    reader = _Reader({"a": _rep(FRESH, 6), "z": _rep(FRESH, 9)})
    out = R.build_recommendation("", REG, reader, now=NOW)
    assert out["best"]["spot_slug"] == "z" and out["total_count"] == 4


def test_list_regions_counts_sorted():
    regs = R.list_regions(REG)
    assert regs[0] == {"region": "广东", "count": 3}
    assert {"region": "海南", "count": 1} in regs


# —— Recommendation 输出契约锚点（供 Vue 首屏依赖，键集/类型/GMT+8 固定）——
def test_recommendation_contract_shape():
    reader = _Reader({"a": _rep(FRESH, 8.0), "b": _rep(FRESH, 6.0)})
    out = R.build_recommendation("广东", REG, reader, now=NOW)
    assert set(out) == {"region", "generated_at", "fresh_count", "total_count",
                        "degraded", "best", "alternatives"}
    assert out["generated_at"].endswith("GMT+8")          # 时区显式(数据诚实)
    assert isinstance(out["fresh_count"], int) and isinstance(out["degraded"], bool)
    assert set(out["best"]) == {"spot_slug", "spot_name", "day", "week", "score",
                                "headline", "key_factors"}
    assert isinstance(out["best"]["key_factors"], list) and len(out["best"]["key_factors"]) <= 3
    for alt in out["alternatives"]:
        assert set(alt) == {"spot_slug", "spot_name", "day", "week", "score"}


# —— 公开端点（无鉴权）——
@pytest.fixture
def client():
    return TestClient(A.app)


class _Store:
    def list_listed_registry(self):
        return REG


def test_endpoints_public_no_auth(client, monkeypatch):
    # 端点走真实时钟 → 新鲜时间戳必须动态生成（钉死日期=时间炸弹，07-28 曾爆）
    fresh_today = dt.datetime.now(GMT8).strftime("%Y-%m-%d 02:00 GMT+8")
    monkeypatch.setattr(A.db, "get_store", lambda: _Store())
    monkeypatch.setattr(A.deps, "_cache_reader", lambda: _Reader({"a": _rep(fresh_today, 7.0)}))
    r1 = client.get("/api/regions")
    assert r1.status_code == 200 and any(x["region"] == "广东" for x in r1.json()["regions"])
    r2 = client.get("/api/recommend?region=广东")
    assert r2.status_code == 200                      # 公开，无 401
    assert r2.json()["best"]["spot_slug"] == "a"
