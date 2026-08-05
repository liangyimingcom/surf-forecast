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


# ============================================================
# R2 数据健康探测器 —— 坏数据必须能在 /status 被看见
# （本项目无推送告警，/status 是唯一故障发现渠道；只能靠人肉翻库的坏数据等于发现不了）
# ============================================================
def test_coord_invalid_rows_picks_marked_and_sorts():
    rows = [
        {"slug": "b", "spot": "B点", "coord_invalid": "lat 超范围: 110.36"},
        {"slug": "a", "spot": "A点", "coord_invalid": "lon 超范围: 200.0"},
        {"slug": "ok", "spot": "正常点"},
    ]
    out = G.coord_invalid_rows(rows)
    assert [x["slug"] for x in out] == ["a", "b"]          # slug 升序
    assert out[0]["spot"] == "A点"
    assert "lon 超范围" in out[0]["why"]


def test_coord_invalid_rows_empty_is_normal():
    """生产当前应为空——它是未来复发的探测器，不是当下故障清单。"""
    assert G.coord_invalid_rows(
        [{"slug": "a", "lat": 18.6, "lon": 110.2}]) == []


def test_coord_duplicate_groups_only_returns_collisions():
    rows = [
        {"slug": "s2", "spot": "二", "lat": 22.6001, "lon": 114.8425},
        {"slug": "s58", "spot": "五八", "lat": 22.6001, "lon": 114.8425},
        {"slug": "solo", "spot": "独", "lat": 36.0920, "lon": 120.4680},
    ]
    out = G.coord_duplicate_groups(rows)
    assert len(out) == 1
    assert out[0]["slugs"] == ["s2", "s58"]                # 组内 slug 升序
    assert out[0]["spots"] == ["二", "五八"]
    assert out[0]["coord"] == "22.6001,114.8425"


def test_coord_duplicate_groups_precision_is_4dp():
    """精度必须与 dedup_key / find_registry_by_coord 的比较精度一致（4dp）——
    正是这个精度上的重复才会造成坐标→slug 解析歧义。"""
    rows = [
        {"slug": "a", "lat": 18.65200001, "lon": 110.27900001},
        {"slug": "b", "lat": 18.65200009, "lon": 110.27900009},   # 4dp 相同 → 算重复
        {"slug": "c", "lat": 18.6521, "lon": 110.2790},           # 4dp 不同 → 不算
    ]
    out = G.coord_duplicate_groups(rows)
    assert len(out) == 1 and out[0]["slugs"] == ["a", "b"]


def test_coord_duplicate_groups_tolerates_bad_rows():
    """缺坐标/坏类型的行跳过即可，不得让探测器自己炸掉（它是故障发现渠道）。"""
    rows = [
        {"slug": "no_coord"},
        {"slug": "bad", "lat": "x", "lon": "y"},
        {"slug": "none", "lat": None, "lon": 1.0},
    ]
    assert G.coord_duplicate_groups(rows) == []


def test_duplicate_severity_expected_vs_suspect():
    """分级是这个探测器可用的关键：同滩不同机位=预期，跨滩/跨区=真异常。
    不分级则 3 组里 2 组是误报，告警会被无视（狼来了）。"""
    rows = [
        # 同一片海滩的两个机位 → expected
        {"slug": "a1", "lat": 1.0, "lon": 2.0, "beach_group": "xichong", "region_cn": "广东"},
        {"slug": "a2", "lat": 1.0, "lon": 2.0, "beach_group": "xichong", "region_cn": "广东"},
        # 跨区域同坐标（Kirra 在澳洲却与广东点同坐标）→ suspect
        {"slug": "b1", "lat": 3.0, "lon": 4.0, "beach_group": "honghaiwan", "region_cn": "广东"},
        {"slug": "b2", "lat": 3.0, "lon": 4.0, "beach_group": None, "region_cn": "国外"},
    ]
    by_coord = {g["coord"]: g for g in G.coord_duplicate_groups(rows)}
    assert by_coord["1.0,2.0"]["severity"] == "expected"
    assert by_coord["3.0,4.0"]["severity"] == "suspect"
    assert by_coord["3.0,4.0"]["regions"] == ["国外", "广东"]


def test_real_snapshot_duplicate_groups_and_severity():
    """对真实快照回归：3 组重复 = 2 组同滩机位(expected) + 1 组真异常(suspect)。
    唯一 suspect 是 sl54 虹海湾山海里 / sl84 Kirra —— Kirra 在澳洲，坐标却在广东，
    疑与 sl54 数据串行。上游哪天修了或又多一组，这条会提醒复核。"""
    import json
    import pathlib
    from web import seed as _seed
    snap = pathlib.Path(__file__).resolve().parents[1] / "reference" / "data" / "shilaoren_spots.json"
    rows = _seed.build_registry_rows(json.loads(snap.read_text(encoding="utf-8")))
    groups = G.coord_duplicate_groups(G.visible_rows(rows))
    assert sorted(tuple(g["slugs"]) for g in groups) == \
        [("sl2", "sl58"), ("sl49", "sl93"), ("sl54", "sl84")]
    suspect = [g for g in groups if g["severity"] == "suspect"]
    assert [tuple(g["slugs"]) for g in suspect] == [("sl54", "sl84")], suspect

