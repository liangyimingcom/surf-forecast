"""R2 目录治理单测：状态解析 / 测试点判定 / 三道过滤 / 同滩去重 / manifest 契约。"""
import datetime as dt

import web.governance as G
import web.recommend as R
import web.refresh as RF

GMT8 = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime(2026, 7, 28, 10, 0, tzinfo=GMT8)
FRESH = "2026-07-28 02:00 GMT+8"


# —— parse_op_status：全角/半角、city/name 两处、干净化 ——

def test_parse_status_fullwidth_city():
    n, c, op = G.parse_op_status("汕尾88", "（维护中）")
    assert (n, c, op) == ("汕尾88", "", "maintenance")


def test_parse_status_halfwidth_city():
    n, c, op = G.parse_op_status("东涌", "(待开放)")
    assert (n, c, op) == ("东涌", "", "pending")


def test_parse_status_in_name():
    n, c, op = G.parse_op_status("SURFPARK （待开放）", "其他")
    assert (n, c, op) == ("SURFPARK", "其他", "pending")


def test_parse_status_clean_row_untouched():
    n, c, op = G.parse_op_status("石老人", "QingDao")
    assert (n, c, op) == ("石老人", "QingDao", "open")


def test_is_test_name():
    assert G.is_test_name("E2E石老人")
    assert G.is_test_name("测试点")
    assert not G.is_test_name("石老人")


def test_annotate_row_idempotent():
    row = {"slug": "sl45", "spot": "汕尾88", "city": "（维护中）"}
    G.annotate_row(row)
    once = dict(row)
    G.annotate_row(row)
    assert row == once
    assert row["op_status"] == "maintenance" and row["spot"] == "汕尾88"


def test_annotate_row_beach_group():
    row = {"slug": "sl2", "spot": "狮子岛全景", "city": "HuiZhou"}
    G.annotate_row(row)
    assert row["beach_group"] == "shizidao"


# —— 三道过滤 ——

def _rep(score):
    return {
        "spot": "X", "calibratedAt": FRESH, "ranking": [0],
        "days": [{"date": FRESH[:10], "week": "周二", "score": score, "best": True,
                  "window": "早7-9点", "board": "鱼板", "novice": "适合",
                  "dawnWind": "离岸风", "hs": [1.0], "tp": [8], "tp2": [9]}],
    }


class _Reader:
    def __init__(self, data):
        self.data = data

    def get(self, key):
        return self.data.get(key.split("/")[0])


def test_recommend_excludes_test_and_non_open():
    reg = [
        {"slug": "a", "spot": "甲", "region_cn": "广东", "op_status": "open"},
        {"slug": "t", "spot": "E2E点", "region_cn": "广东", "is_test": True},
        {"slug": "m", "spot": "乙", "region_cn": "广东", "op_status": "maintenance"},
    ]
    reader = _Reader({"a": _rep(7.0), "t": _rep(9.9), "m": _rep(9.5)})
    out = R.build_recommendation("广东", reg, reader, now=NOW)
    assert out["best"]["spot_slug"] == "a"          # 测试点/维护点分再高也不推荐
    assert out["total_count"] == 1                   # coverage 分母 = 可推荐池
    assert out["degraded"] is False


def test_recommend_missing_op_status_treated_open():
    reg = [{"slug": "a", "spot": "甲", "region_cn": "广东"}]  # 未迁移老行
    out = R.build_recommendation("广东", reg, _Reader({"a": _rep(7.0)}), now=NOW)
    assert out["best"] is not None


def test_recommend_dedups_beach_group():
    reg = [
        {"slug": "s1", "spot": "狮子岛全景", "region_cn": "广东", "beach_group": "shizidao"},
        {"slug": "s2", "spot": "狮子岛-右", "region_cn": "广东", "beach_group": "shizidao"},
        {"slug": "o", "spot": "他滩", "region_cn": "广东"},
    ]
    reader = _Reader({"s1": _rep(8.8), "s2": _rep(8.8), "o": _rep(7.0)})
    out = R.build_recommendation("广东", reg, reader, now=NOW)
    slugs = [out["best"]["spot_slug"]] + [a["spot_slug"] for a in out["alternatives"]]
    assert "s1" in slugs and "s2" not in slugs       # 同滩只出最高分一条
    assert "o" in slugs
    assert out["fresh_count"] == 3                    # 新鲜计数在去重前（数据健康口径）


# —— manifest 契约（R2 决策9/10）——

def test_manifest_gates_freshness():
    reg = [{"slug": "a", "spot": "甲", "region_cn": "广东"},
           {"slug": "b", "spot": "乙", "region_cn": "广东"}]
    reader = _Reader({"a": _rep(7.0), "b": _rep(9.0)})   # b 缓存新鲜但不在 succeeded
    manifest = {"date": "2026-07-28", "succeeded": ["a"], "expected": ["a", "b"]}
    out = R.build_recommendation("广东", reg, reader, now=NOW, manifest=manifest)
    assert out["best"]["spot_slug"] == "a"                # 中间态(b)对外不可见
    assert out["fresh_count"] == 1 and out["degraded"] is True


def test_manifest_stale_date_falls_back_to_calibrated_at():
    reg = [{"slug": "a", "spot": "甲", "region_cn": "广东"}]
    manifest = {"date": "2026-07-27", "succeeded": []}    # 昨日 manifest 不裁今日
    out = R.build_recommendation("广东", reg, _Reader({"a": _rep(7.0)}), now=NOW,
                                 manifest=manifest)
    assert out["best"] is not None


def _clock():
    return NOW


def test_build_manifest_main_records_failures():
    m = RF.build_manifest(None, "main", ["a", "b", "c"],
                          {"a": "ok", "b": "skipped: error(DataSourceError)", "c": "ok"},
                          duration_s=12.3, clock=_clock)
    assert m["date"] == "2026-07-28" and m["kind"] == "main"
    assert m["succeeded"] == ["a", "c"]
    assert "b" in m["failed"]
    assert m["history"][-1]["ok_n"] == 2


def test_build_manifest_retry_merges_same_day():
    prev = RF.build_manifest(None, "main", ["a", "b"], {"a": "ok", "b": "skipped: error(X)"},
                             duration_s=10, clock=_clock)
    m = RF.build_manifest(prev, "retry", ["b"], {"b": "ok"}, duration_s=5, clock=_clock)
    assert m["succeeded"] == ["a", "b"]              # 补齐而非替换
    assert m["failed"] == {}
    assert len(m["history"]) == 2


def test_missing_from_manifest():
    m = {"date": "2026-07-28", "expected": ["a", "b", "c"], "succeeded": ["a"]}
    assert RF.missing_from_manifest(m, "2026-07-28") == ["b", "c"]
    assert RF.missing_from_manifest(m, "2026-07-29") is None   # 非今日 → 断链退化全量
    assert RF.missing_from_manifest(None, "2026-07-28") is None


def test_build_manifest_all_failed_still_records():
    m = RF.build_manifest(None, "main", ["a"], {"a": "skipped: error(X)"},
                          duration_s=1, clock=_clock)
    assert m["succeeded"] == [] and "a" in m["failed"]   # 全失败也留痕（/status 不停摆）
