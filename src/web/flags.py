"""P1.3 功能开关（会员锁）+ 会员门原语（Fable5 §1.4 §2.2）。

一期：`member_lock_enabled=false` → 深度接口全公开（诚实分层：不再靠前端 demo 静默登录伪门禁）。
二期：置 true → 中间件按会员拦截（微信扫码登录后 membership=member）。
开关走 env `SF_MEMBER_LOCK`，二期上线**只改配置不改代码**。
"""
from __future__ import annotations

import os

from fastapi import HTTPException, Request

from . import db


def member_lock_enabled() -> bool:
    return os.getenv("SF_MEMBER_LOCK", "").strip().lower() in ("1", "true", "yes", "on")


def get_flags() -> dict:
    return {"member_lock_enabled": member_lock_enabled()}


def _session_user(request: Request) -> dict | None:
    """尽力解析登录用户；无/失效返回 None（不抛异常）。"""
    from . import deps
    token = request.cookies.get(deps.COOKIE_NAME)
    if not token:
        return None
    store = db.get_store()
    email = store.get_session_email(token)
    if not email:
        return None
    user = store.get_user(email)
    if not user:
        return None
    return {"userId": user["userId"], "email": user["email"],
            "level": user["level"], "membership": user.get("membership", "free")}


def member_gate(request: Request) -> dict | None:
    """会员门原语（就位·默认关）。

    - 开关关（一期）：放行任何人，返回登录用户 dict 或 None（公开）。
    - 开关开（二期）：要求登录且 membership=member，否则 402（会员专享）。
    绝不把可见性耦合到刷新/成本开关（冷点炸弹红线）——这里只读会员身份。
    """
    user = _session_user(request)
    if not member_lock_enabled():
        return user  # 一期全公开
    if not user:
        raise HTTPException(status_code=401, detail="会员专享内容，请登录")
    if user.get("membership") != "member":
        raise HTTPException(status_code=402, detail="会员专享内容，请开通会员")
    return user
