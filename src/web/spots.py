"""浪点 CRUD 服务层 —— custom-spots R2（design §4）。

会员自定义浪点的增/查/改/删 + 切换记忆。鉴权由 app.py 的 current_user 依赖保证（全 401）。
红线：slug 不可变作缓存键；同坐标全局去重共享 slug；名称转义防 XSS；配额 free=3/paid=20。
即时预算（新建立即可读）由 R4 通过 budget_hook 注入，避免本层耦合刷新逻辑。
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from . import spots_model as sm

GMT8 = ZoneInfo("Asia/Shanghai")

# 会员等级 → 浪点数上限（R2.2 / C2）
LEVEL_MAX_SPOTS = {"free": 3, "paid": 20}

VALID_VOTE = None  # 占位避免误用


class SpotError(Exception):
    """浪点操作错误（配额/重名/非法坐标/不存在）。"""


def _now() -> str:
    return datetime.now(GMT8).isoformat(timespec="seconds")


def create_spot(store, user: dict, name: str, lat: float, lon: float,
                facing: float | None = None, days: int = 6,
                budget_hook=None) -> dict:
    """创建浪点：校验→配额→重名→去重(registry)→写 saved_spots(+ref)。

    budget_hook(registry_row): 可选，新坐标首次入册时触发即时预算（R4 注入）。
    """
    email, level = user["email"], user.get("level", "free")
    # 1. 校验坐标 + 名称转义
    sm.validate_coord(lat, lon)
    clean_name = sm.validate_name(name)
    # 2. 配额
    existing = store.list_spots(email)
    if len(existing) >= LEVEL_MAX_SPOTS.get(level, 3):
        raise SpotError(f"浪点数已达上限({LEVEL_MAX_SPOTS.get(level, 3)})，升级 paid 可增至 20")
    # 3. 名称用户内唯一
    if any(s["name"] == clean_name for s in existing):
        raise SpotError(f"名称已存在：{clean_name}")
    # 4. 区域/朝向推断 + 去重键
    region = sm.infer_region(lat, lon)
    facing_deg = sm.infer_facing(lat, lon, override=facing)
    dk = sm.dedup_key(lat, lon, facing_deg)
    # 5. 去重：同坐标已入册 → 复用 slug + ref_count++；否则新建注册表行 + 即时预算
    reg = store.find_registry_by_dedup(dk)
    if reg is not None:
        slug = reg["slug"]
        store.incr_ref(slug, 1)
        # 若曾 inactive 则复活
        if reg.get("status") != "active":
            reg["status"] = "active"
            reg["refresh_enabled"] = True
            store.upsert_registry(reg)
    else:
        used = {r["slug"] for r in (store.list_active_registry() or [])}
        existing_reg = store.get_registry  # 探测全局占用（保守：用 dedup 已查，这里仅防名冲突）
        slug = sm.make_slug(clean_name, lat, lon, existing=used)
        row = {
            "slug": slug, "spot": clean_name, "lat": lat, "lon": lon,
            "spot_facing_deg": facing_deg, "region": region, "days": days,
            "dedup_key": dk, "ref_count": 1, "status": "active",
            "refresh_enabled": True, "source": "user",
            "created_at_gmt8": _now(), "last_refresh_at_gmt8": None,
            "last_viewed_at_gmt8": _now(),
        }
        store.upsert_registry(row)
        if budget_hook is not None:
            try:
                budget_hook(row)  # 即时预算（R4），失败不阻断创建
            except Exception:  # noqa: BLE001
                pass
    # 6. 写用户浪点
    spot = {
        "slug": slug, "name": clean_name, "lat": lat, "lon": lon,
        "spot_facing_deg": facing_deg, "region": region, "days": days,
        "status": "active", "created_at_gmt8": _now(), "last_viewed_at_gmt8": _now(),
    }
    store.put_spot(email, spot)
    return _public(spot, region)


def list_spots(store, user: dict) -> list[dict]:
    email = user["email"]
    last = store.get_last_selected(email)
    out = []
    for s in store.list_spots(email):
        d = _public(s, s.get("region", "uncalibrated"))
        d["selected"] = (s["slug"] == last)
        out.append(d)
    return out


def update_spot(store, user: dict, slug: str, name: str | None = None,
                facing: float | None = None) -> dict:
    """重命名/改朝向；**slug 不变**（缓存键稳定，R2.3）。"""
    email = user["email"]
    s = store.get_spot(email, slug)
    if not s or s.get("status") != "active":
        raise SpotError("浪点不存在")
    if name is not None:
        clean = sm.validate_name(name)
        if any(o["name"] == clean and o["slug"] != slug for o in store.list_spots(email)):
            raise SpotError(f"名称已存在：{clean}")
        s["name"] = clean
    if facing is not None:
        s["spot_facing_deg"] = float(facing)
    store.put_spot(email, s)
    return _public(s, s.get("region", "uncalibrated"))


def delete_spot(store, user: dict, slug: str) -> dict:
    """软删 saved_spots + registry ref_count--（R2.4 / C8）。"""
    email = user["email"]
    s = store.get_spot(email, slug)
    if not s:
        raise SpotError("浪点不存在")
    store.soft_delete_spot(email, slug)
    store.incr_ref(slug, -1)  # ref 归零自动转 inactive
    return {"ok": True, "slug": slug}


def select_spot(store, user: dict, slug: str) -> dict:
    """记"上次选中" + 更新 last_viewed（用于默认展示与冷点回收，R3.2/C3）。"""
    email = user["email"]
    s = store.get_spot(email, slug)
    if not s or s.get("status") != "active":
        raise SpotError("浪点不存在")
    store.set_last_selected(email, slug)
    s["last_viewed_at_gmt8"] = _now()
    store.put_spot(email, s)
    reg = store.get_registry(slug)
    if reg:
        reg["last_viewed_at_gmt8"] = _now()
        store.upsert_registry(reg)
    return {"ok": True, "slug": slug}


def _public(spot: dict, region: str) -> dict:
    """对外视图（标注未标定海域阈值来源，C6 数据诚实）。"""
    d = {k: spot.get(k) for k in
         ("slug", "name", "lat", "lon", "spot_facing_deg", "region", "days", "status")}
    d["threshold_note"] = "已标定(黄海)" if region == "huanghai" else "按黄海近似(未标定)"
    return d
