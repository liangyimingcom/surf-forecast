"""鉴权 —— argon2 加盐哈希 + 服务端 session token（web R1.1/1.2/1.6, design web §7）。

密码绝不明文存储；token 为服务端随机串，httponly cookie 携带（前端零信任）。
"""

from __future__ import annotations

import secrets
import time
import uuid

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()

VALID_LEVELS = ("free", "paid")


class AuthError(Exception):
    """鉴权失败（注册冲突/凭据错误）。"""


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return _ph.verify(stored_hash, password)
    except VerifyMismatchError:
        return False


def register(store, email: str, password: str, level: str = "free") -> dict:
    email = (email or "").strip().lower()
    if not email or not password:
        raise AuthError("邮箱与密码必填")
    if level not in VALID_LEVELS:
        level = "free"
    if store.get_user(email):
        raise AuthError("该邮箱已注册")
    user = {
        "userId": str(uuid.uuid4()),
        "email": email,
        "passwordHash": hash_password(password),  # 绝不存明文
        "level": level,
        "createdAt": int(time.time()),
    }
    store.put_user(user)
    return _public(user)


def login(store, email: str, password: str) -> str:
    email = (email or "").strip().lower()
    user = store.get_user(email)
    if not user or not verify_password(user["passwordHash"], password):
        raise AuthError("邮箱或密码错误")
    token = secrets.token_urlsafe(32)
    store.put_session(token, email)
    return token


def logout(store, token: str) -> None:
    if token:
        store.delete_session(token)


def _public(user: dict) -> dict:
    """对外暴露的用户字段（绝不含 passwordHash）。"""
    return {"userId": user["userId"], "email": user["email"], "level": user["level"]}
