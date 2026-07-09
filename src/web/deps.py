"""依赖与服务层 —— current_user(401) + 会员配额 + 接引擎出 REPORT。"""

from __future__ import annotations

import os

from fastapi import HTTPException, Request

from surf_forecast import analyze, render

from . import db

COOKIE_NAME = "sf_session"

# 会员等级 → 最大可查天数（web R1.4/1.5）
LEVEL_MAX_DAYS = {"free": 3, "paid": 7}


def current_user(request: Request) -> dict:
    """从 httponly cookie 解析当前用户；无效则 401（web R1.3，前端零信任）。"""
    token = request.cookies.get(COOKIE_NAME)
    store = db.get_store()
    email = store.get_session_email(token) if token else None
    if not email:
        raise HTTPException(status_code=401, detail="未登录或会话失效")
    user = store.get_user(email)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return {"userId": user["userId"], "email": user["email"], "level": user["level"]}


def clamp_days(level: str, days: int) -> int:
    """按会员等级钳制可查天数（超限走升级引导，这里直接钳制）。"""
    return max(1, min(days, LEVEL_MAX_DAYS.get(level, 3)))


def _cache_reader():
    """生产经 SF_CACHE_BUCKET 启用 S3 缓存读；未配置则 None（直连引擎）。"""
    bucket = os.getenv("SF_CACHE_BUCKET")
    if not bucket:
        return None
    from . import refresh
    return refresh.S3CacheReader(bucket)


def _cache_writer():
    """生产经 SF_CACHE_BUCKET 启用 S3 缓存写（即时预算用）；未配置则 None。"""
    bucket = os.getenv("SF_CACHE_BUCKET")
    if not bucket:
        return None
    from . import refresh
    return refresh.S3CacheWriter(bucket)


def instant_budget(registry_row: dict) -> None:
    """新建浪点即时预算钩子（C4）：有缓存桶则预算一次写缓存，使新点立即可读。无桶则 no-op（回退实算）。"""
    writer = _cache_writer()
    if writer is None:
        return
    from . import refresh
    refresh.budget_one(writer, registry_row)


def _resolve_slug(lat: float, lon: float) -> str | None:
    """按坐标解析缓存 slug：优先动态注册表(custom-spots)，回退 DEFAULT_SPOTS。"""
    reg = db.get_store().find_registry_by_coord(lat, lon)
    if reg:
        return reg["slug"]
    from . import refresh
    sp = refresh.find_spot(lat, lon)
    return sp["slug"] if sp else None


def get_report(lat: float, lon: float, days: int, spot: str) -> dict:
    """读写解耦的「读」：上架/已注册浪点优先命中每日预算缓存（<500ms）；未命中回退引擎实算。"""
    reader = _cache_reader()
    slug = _resolve_slug(lat, lon)
    if reader is not None and slug is not None:
        cached = reader.get(f"{slug}/latest.json")
        if cached:
            return cached
    # 回退：实时计算（自定义坐标 / 缓存未命中 / 缓存不可用）
    from . import refresh  # noqa: F401  保持原依赖路径
    ctx = analyze.build_context(lat, lon, days, spot)
    return render.render_json(ctx)


def get_history(lat: float, lon: float, days: int, spot: str) -> dict | None:
    """昨日回看 HISTORY（含 predict）。已注册浪点优先读缓存，未命中回退引擎 include_history。"""
    reader = _cache_reader()
    slug = _resolve_slug(lat, lon)
    if reader is not None and slug is not None:
        cached = reader.get(f"{slug}/latest.json")
        if cached and cached.get("history"):
            return cached["history"]
    ctx = analyze.build_context(lat, lon, days, spot, include_history=True)
    rep = render.render_json(ctx)
    return rep.get("history")
