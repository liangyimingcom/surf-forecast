"""custom-spots R1 测试 —— spots_model 纯函数 + InMemoryStore 浪点/注册表访问。"""

from __future__ import annotations

import pytest

from web import db
from web import spots_model as sm


# —— slug / 去重 / 区域推断 ——
def test_slugify_ascii():
    assert sm.slugify("Shandongtou Point") == "shandongtou-point"
    assert sm.slugify("石老人") == ""  # 中文剥离后为空 → 调用方退化 geo


def test_geo_slug_stable_and_negative():
    assert sm.geo_slug(36.092, 120.468) == "geo-360920-1204680"
    assert sm.geo_slug(-33.9, 151.2).startswith("geo-n")


def test_make_slug_dedup_fallback():
    # 中文名 → 退化 geo
    s1 = sm.make_slug("石老人", 36.1, 120.6)
    assert s1.startswith("geo-")
    # ASCII 名优先；冲突则退化 geo
    assert sm.make_slug("Point", 36.1, 120.6, existing=set()) == "point"
    s2 = sm.make_slug("Point", 36.1, 120.6, existing={"point"})
    assert s2.startswith("geo-")


def test_dedup_key_rounds():
    assert sm.dedup_key(36.09201, 120.46799, 157) == sm.dedup_key(36.092, 120.468, 157)
    assert sm.dedup_key(36.092, 120.468, 157) != sm.dedup_key(36.092, 120.468, 180)


def test_infer_region_and_facing():
    assert sm.infer_region(36.092, 120.468) == "huanghai"
    assert sm.infer_region(-33.9, 151.2) == "uncalibrated"
    assert sm.infer_facing(36.092, 120.468) == 157.0     # 黄海缺省
    assert sm.infer_facing(-33.9, 151.2) == 180.0        # 未标定缺省
    assert sm.infer_facing(36.092, 120.468, override=200) == 200.0  # 用户覆盖


def test_validate_name_escapes_xss():
    assert sm.validate_name("  山东头  ") == "山东头"
    assert sm.validate_name("<script>") == "&lt;script&gt;"
    with pytest.raises(ValueError):
        sm.validate_name("")
    with pytest.raises(ValueError):
        sm.validate_name("x" * 33)


def test_validate_coord_range():
    sm.validate_coord(36.092, 120.468)
    with pytest.raises(ValueError):
        sm.validate_coord(95, 120)
    with pytest.raises(ValueError):
        sm.validate_coord(36, 200)


# —— InMemoryStore: saved_spots CRUD + 隔离 ——
def test_store_spot_crud_isolation():
    db.reset_store()
    st = db.get_store()
    st.put_spot("a@x.com", {"slug": "s1", "name": "P1", "status": "active"})
    st.put_spot("b@x.com", {"slug": "s2", "name": "P2", "status": "active"})
    assert len(st.list_spots("a@x.com")) == 1          # 用户隔离
    assert st.get_spot("a@x.com", "s1")["name"] == "P1"
    assert st.soft_delete_spot("a@x.com", "s1") is True
    assert st.list_spots("a@x.com") == []              # 软删后默认不列
    assert len(st.list_spots("a@x.com", include_inactive=True)) == 1


# —— InMemoryStore: spot_registry 去重 + ref_count + active ——
def test_store_registry_dedup_and_refcount():
    db.reset_store()
    st = db.get_store()
    dk = sm.dedup_key(36.092, 120.468, 157)
    st.upsert_registry({"slug": "shandongtou", "dedup_key": dk, "ref_count": 1,
                        "status": "active", "refresh_enabled": True})
    # 去重命中
    assert st.find_registry_by_dedup(dk)["slug"] == "shandongtou"
    # 第二用户引用 → ref_count++
    st.incr_ref("shandongtou", 1)
    assert st.get_registry("shandongtou")["ref_count"] == 2
    assert len(st.list_active_registry()) == 1
    # 引用归零 → inactive，退出 active 列表
    st.incr_ref("shandongtou", -2)
    assert st.get_registry("shandongtou")["status"] == "inactive"
    assert st.list_active_registry() == []


def test_store_refresh_enabled_and_last_selected():
    db.reset_store()
    st = db.get_store()
    st.upsert_registry({"slug": "p", "dedup_key": "k", "ref_count": 1,
                        "status": "active", "refresh_enabled": True})
    st.set_refresh_enabled("p", False)          # 冷点回收
    assert st.list_active_registry() == []
    st.set_last_selected("a@x.com", "p")        # 记住上次选中
    assert st.get_last_selected("a@x.com") == "p"
