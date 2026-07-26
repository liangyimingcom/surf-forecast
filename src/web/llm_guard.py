# -*- coding: utf-8 -*-
"""
llm_guard.py — 在线 LLM 澄清护栏（ADR-7，纯 stdlib，进程内，可单测）。

- RateLimiter：per-IP 滑动窗口限流。
- DailyBudget：全局每日调用预算硬闸（GMT+8 日界，跨天重置）。
- option_cache_key：同页同类选项缓存键（复用 cache.TTLCache 存值）。
- validate_clarify：校验 LLM 澄清输出（options 菜单 或 收敛的 requirement），拒畸形。

红线：纯性能/护栏，不碰可见性；超限/超预算 → 调用方降级预置模板（不报错、不白屏）。
时钟可注入，便于边界测试。
"""
from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta, timezone

GMT8 = timezone(timedelta(hours=8))
_KINDS = ("bug", "improve", "new_feature", "remove")


class RateLimiter:
    """per-IP 滑动窗口：window_s 内最多 max_calls 次。"""

    def __init__(self, max_calls: int, window_s: float, now_fn=time.monotonic):
        self.max = max(1, max_calls)
        self.win = window_s
        self._now = now_fn
        self._hits: dict[str, list] = {}

    def allow(self, ip: str) -> bool:
        now = self._now()
        q = self._hits.setdefault(ip or "?", [])
        while q and now - q[0] >= self.win:
            q.pop(0)
        if len(q) >= self.max:
            return False
        q.append(now)
        return True


class DailyBudget:
    """全局每日调用预算硬闸（GMT+8 日界）。超预算 → False（调用方降级模板）。"""

    def __init__(self, max_calls: int, now_fn=lambda: datetime.now(GMT8)):
        self.max = max(0, max_calls)
        self._now = now_fn
        self._day = None
        self._n = 0

    def try_spend(self) -> bool:
        d = self._now().date()
        if d != self._day:
            self._day, self._n = d, 0
        if self._n >= self.max:
            return False
        self._n += 1
        return True

    @property
    def spent(self) -> int:
        return self._n


def option_cache_key(page: str, step, chosen_path) -> str:
    raw = "%s|%s|%s" % (page or "", step, ">".join(chosen_path or []))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def validate_clarify(obj) -> list:
    """LLM 澄清输出校验：{options:[≤8 个 ≤60字]} 或 {requirement:{kind,page,text}}。返回错误列表(空=通过)。"""
    errs = []
    if not isinstance(obj, dict):
        return ["输出非对象"]
    if "options" in obj:
        o = obj["options"]
        if not (isinstance(o, list) and 1 <= len(o) <= 8
                and all(isinstance(x, str) and 0 < len(x) <= 60 for x in o)):
            errs.append("options 须为 1-8 个 1..60 字字符串")
    elif "requirement" in obj:
        r = obj.get("requirement")
        if not isinstance(r, dict):
            errs.append("requirement 非对象")
        else:
            if r.get("kind") not in _KINDS:
                errs.append("kind 非法(%r)" % r.get("kind"))
            if not (isinstance(r.get("text"), str) and r["text"].strip()):
                errs.append("text 空")
            if len(r.get("text", "")) > 2000:
                errs.append("text 超长(>2000)")
    else:
        errs.append("须含 options 或 requirement")
    return errs
