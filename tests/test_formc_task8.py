"""形态C · Task 8 —— 契约测试扩充（在既有 test_formc.py 基础上加深覆盖）。

覆盖 DoD 摘要 1/2/3/4 的后端契约，全部离线（内存 store + 真实快照文件，不触网）：
  A. spot_registry 58+ 导入（真实 reference/data/shilaoren_spots.json）
  B. /api/cams 直播目录（数量=有 live_src 子集 / 免责 / 只读 405 / Decimal 兼容）
  C. 引擎预报契约（wdeg 必含 + 双周期 tp/tp2 + times/hs/wind/gust 数字 + 离岸风编码）
  D. 地区筛选后端契约（/api/catalog 携带 region + has_live，供前端 8 区筛选）

红线守护：float→Decimal（DynamoDB 写库前）；受保护接口 401；slug 不可变（^sl\\d+$）；
只读接口无写入面（405）。
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from surf_forecast import analyze, render
from surf_forecast.models import DailyForecast, ForecastPoint, TideExtreme
from web import app as app_module
from web import db, seed

# 真实快照：58 浪点（全含坐标），42 含 live_src；官方 8 区分布固定。
SNAPSHOT = "reference/data/shilaoren_spots.json"
REGIONS_8 = {"广东", "海南", "福建", "广西", "浙江", "山东", "其他", "国外"}
EXPECT_REGION_COUNTS = {"广东": 22, "海南": 15, "山东": 3, "福建": 5,
                        "广西": 3, "浙江": 2, "其他": 1, "国外": 7}
EXPECT_TOTAL = 58
EXPECT_LIVE = 42


@pytest.fixture(autouse=True)
def _reset():
    db.reset_store()
    yield
    db.reset_store()


@pytest.fixture
def client():
    return TestClient(app_module.app)


def _auth(client):
    client.post("/api/auth/register", json={"email": "t8@t.com", "password": "secret123"})
    client.post("/api/auth/login", json={"email": "t8@t.com", "password": "secret123"})


def _seed_real():
    """把真实 58 浪点快照灌入内存注册表；返回写入条数。"""
    return seed.seed_from_file(db.get_store(), SNAPSHOT)


# ============================================================
# A. spot_registry 58+（真实快照导入）
# ============================================================
def test_registry_seeds_58_plus():
    n = _seed_real()
    assert n >= EXPECT_TOTAL
    active = db.get_store().list_active_registry()
    assert len(active) >= EXPECT_TOTAL          # DoD#1：58+ 浪点入注册表


def test_registry_every_row_has_coord_and_immutable_slug():
    _seed_real()
    import math
    slug_re = re.compile(r"^sl\d+$")            # 稳定不可变(基于 cId)
    for r in db.get_store().list_active_registry():
        assert slug_re.match(r["slug"]), f"slug 非法/可变: {r['slug']}"
        lat, lon = float(r["lat"]), float(r["lon"])
        assert math.isfinite(lat) and math.isfinite(lon)   # 坐标为有限数字


def test_registry_regions_cover_official_8():
    _seed_real()
    got = {r.get("region_cn") for r in db.get_store().list_active_registry()}
    assert got == REGIONS_8                     # DoD#4：8 官方区域齐全（供筛选）


def test_registry_region_distribution_matches_snapshot():
    _seed_real()
    counts: dict[str, int] = {}
    for r in db.get_store().list_active_registry():
        counts[r["region_cn"]] = counts.get(r["region_cn"], 0) + 1
    assert counts == EXPECT_REGION_COUNTS


def test_registry_live_src_subset_is_42():
    _seed_real()
    live = [r for r in db.get_store().list_active_registry() if r.get("live_src")]
    assert len(live) == EXPECT_LIVE


def test_seed_row_float_to_decimal_redline():
    """红线：写 DynamoDB 前 float→Decimal（moto 单测不暴露，这里钉死转换）。"""
    rows = seed.build_registry_rows({"spots": [{
        "slug": "sl99", "name": "红线点", "lat": 36.0958, "lon": 120.4786,
        "facing": 157.0, "region_cn": "山东", "live_src": "https://x/y.m3u8"}]})
    conv = db._to_decimal(rows[0])
    assert isinstance(conv["lat"], Decimal) and conv["lat"] == Decimal("36.0958")
    assert isinstance(conv["lon"], Decimal) and conv["lon"] == Decimal("120.4786")
    assert isinstance(conv["spot_facing_deg"], Decimal)
    # 非浮点字段保持原样（不被误转）
    assert conv["slug"] == "sl99" and isinstance(conv["slug"], str)


# ============================================================
# B. /api/cams 直播目录（数量 / 免责 / 只读 / Decimal 兼容）
# ============================================================
def test_cams_count_equals_live_subset(client):
    _seed_real(); _auth(client)
    j = client.get("/api/cams").json()
    assert j["count"] == EXPECT_LIVE            # 目录只含 42 个有直播的浪点
    assert len(j["cams"]) == EXPECT_LIVE
    assert all(c.get("live_src") for c in j["cams"])   # 无一为空 live_src


def test_cams_disclaimer_present_and_meaningful(client):
    _seed_real(); _auth(client)
    disc = client.get("/api/cams").json()["disclaimer"]
    assert isinstance(disc, str) and len(disc) >= 20
    assert "研究" in disc                        # 合规：仅研究用途
    assert "hls" in disc.lower() or "直连" in disc  # 视频前端直连、不经后端


def test_cams_read_only_no_write_surface(client):
    """只读红线：POST/PUT/DELETE/PATCH → 405（方法级路由拒绝，无写入面）。"""
    for method in ("POST", "PUT", "DELETE", "PATCH"):
        resp = client.request(method, "/api/cams")
        assert resp.status_code == 405, f"{method} /api/cams 应 405，实得 {resp.status_code}"


def test_cams_decimal_lat_lon_serialized_as_float(client):
    """Decimal(DynamoDB) 兼容：注册表存 Decimal 坐标，接口下发 JSON float。"""
    db.get_store().upsert_registry({
        "slug": "sl77", "spot": "Decimal 点", "city": "QD", "region_cn": "山东",
        "lat": Decimal("36.0958"), "lon": Decimal("120.4786"),
        "spot_facing_deg": Decimal("157"), "facing_calibrated": False,
        "live_src": "https://isurfvideo.c-pan.cn/live/x.m3u8", "post_url": None,
        "status": "active", "refresh_enabled": True, "days": 6,
    })
    _auth(client)
    cams = client.get("/api/cams").json()["cams"]
    row = {c["slug"]: c for c in cams}["sl77"]
    assert isinstance(row["lat"], float) and row["lat"] == 36.0958
    assert isinstance(row["lon"], float) and row["lon"] == 120.4786


def test_cams_still_requires_auth(client):
    _seed_real()
    assert client.get("/api/cams").status_code == 401   # 受保护红线（未登录 401）


# ============================================================
# C. 引擎预报契约（wdeg / 双周期 / 数字字段 / 离岸风编码）—— 离线自算
# ============================================================
def _pt(h, d, hs=0.8, tp=6.5, wdir=337):
    return ForecastPoint(
        time=datetime(d.year, d.month, d.day, h), wave_height_m=hs, wave_direction_deg=160,
        wave_period_mean_s=5.0, wave_period_peak_s=tp, swell_height_m=0.6,
        wind_speed_kn=8, wind_direction_deg=wdir, wind_gust_kn=11, sea_level_m=0.6,
    )


def _day(d, wdir=337):
    return DailyForecast(
        date=d, points=[_pt(h, d, wdir=wdir) for h in (6, 9, 12)],
        tide_extremes=[TideExtreme(time=datetime(d.year, d.month, d.day, 9),
                                   level_m=0.9, kind="high")],
        sunrise=datetime(d.year, d.month, d.day, 4),
        sunset=datetime(d.year, d.month, d.day, 20),
    )


def _ctx(wdir=337):
    # 山东头朝向 SSE(157)；wdir 参数用于离岸/向岸编码断言
    return analyze.build_context(
        36.092, 120.468, 2, "青岛山东头",
        forecasts=[_day(date(2026, 6, 20), wdir), _day(date(2026, 6, 21), wdir)],
        calibrated_at=datetime(2026, 6, 20, 10, 0))


def test_engine_contract_wdeg_and_dual_period_all_days():
    """DoD#2：所有预报日必含 wdeg + 双周期 tp/tp2，且图表字段均为数字。"""
    rep = render.render_json(_ctx())
    assert len(rep["days"]) == 2
    for day in rep["days"]:
        # wdeg 必含、长度对齐、元素为数字
        assert "wdeg" in day and len(day["wdeg"]) == len(day["times"]) == 3
        assert all(isinstance(w, (int, float)) for w in day["wdeg"])
        # 双周期：tp(Tm) 与 tp2(Tp) 均在场，tp 全数字，tp2 为数字或 None
        assert "tp" in day and "tp2" in day
        assert all(isinstance(x, (int, float)) for x in day["tp"])
        assert all((x is None) or isinstance(x, (int, float)) for x in day["tp2"])
        # times/hs/wind/gust 数字数组（前端图表 sx 缩放依赖）
        for field in ("times", "hs", "wind", "gust"):
            assert day[field] and all(isinstance(v, (int, float)) for v in day[field])
        # tideEvents 为 [小时,潮位] 数字对
        assert day["tideEvents"] and all(
            isinstance(e, list) and len(e) == 2
            and all(isinstance(v, (int, float)) for v in e) for e in day["tideEvents"])


def test_engine_dual_period_two_calibers_distinct():
    day0 = render.render_json(_ctx())["days"][0]
    assert day0["tp"][0] == 5.0     # Tm 实线（平均周期）
    assert day0["tp2"][0] == 6.5    # Tp 虚线（峰值周期）
    assert day0["tp"][0] != day0["tp2"][0]   # 双口径确实分列


def test_engine_offshore_wind_encoded_off():
    # 风 337(NNW) 对朝向 157(SSE) 的浪点 = 离岸（157+180）
    rep = render.render_json(_ctx(wdir=337))
    assert rep["days"][0]["dawnWind"] == "off"


def test_engine_onshore_wind_encoded_on():
    # 风 157(SSE) 正对朝向 157 的浪点 = 向岸（离岸风加成不应触发）
    rep = render.render_json(_ctx(wdir=157))
    assert rep["days"][0]["dawnWind"] == "on"


# ============================================================
# D. 地区筛选后端契约（/api/catalog 携带 region + has_live）
# ============================================================
def test_catalog_lists_58_plus_with_region(client):
    _seed_real(); _auth(client)
    cat = client.get("/api/catalog").json()["catalog"]
    assert len(cat) >= EXPECT_TOTAL
    regions = {c["region"] for c in cat}
    assert regions == REGIONS_8                 # 8 区可筛选


def test_catalog_region_counts_match_snapshot(client):
    _seed_real(); _auth(client)
    cat = client.get("/api/catalog").json()["catalog"]
    counts: dict[str, int] = {}
    for c in cat:
        counts[c["region"]] = counts.get(c["region"], 0) + 1
    assert counts == EXPECT_REGION_COUNTS


def test_catalog_has_live_flag_matches_cams(client):
    _seed_real(); _auth(client)
    cat = client.get("/api/catalog").json()["catalog"]
    cams = client.get("/api/cams").json()["cams"]
    live_in_catalog = sum(1 for c in cat if c["has_live"])
    assert live_in_catalog == len(cams) == EXPECT_LIVE
    # 目录 has_live 的 slug 集合 == cams 的 slug 集合
    assert {c["slug"] for c in cat if c["has_live"]} == {c["slug"] for c in cams}


def test_catalog_facing_uncalibrated_flag(client):
    """朝向为默认估算待校准：facing_calibrated 全 False（合规标注）。"""
    _seed_real(); _auth(client)
    cat = client.get("/api/catalog").json()["catalog"]
    assert all(c["facing_calibrated"] is False for c in cat)
