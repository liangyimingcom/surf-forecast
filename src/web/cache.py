# -*- coding: utf-8 -*-
"""
cache.py — 进程内 TTL + LRU 缓存（web R4.1/4.2）。

用途：给 get_report/get_history 的**实算路径**加一层短命内存缓存，减少 TTL 窗口内的重复
Open-Meteo 取数与引擎计算（S3 latest.json 缓存仍是权威的每日预算层，本层在其之上/之前只做去抖）。

红线（冷点炸弹）：本缓存是**纯性能层**，键=查询参数(slug/坐标+days+spot)，
**绝不影响"可见性"**（目录/直播的上架判定另走 list_listed_registry，与本缓存无关）。

ttl_s<=0 → 缓存停用（get 恒 None）。now_fn 可注入（测试用确定性时钟）。
"""
from __future__ import annotations

import time
from collections import OrderedDict


class TTLCache:
    def __init__(self, ttl_s: float, max_items: int = 128, now_fn=time.monotonic):
        self.ttl_s = ttl_s
        self.max_items = max(1, max_items)
        self._now = now_fn
        self._d: "OrderedDict[str, tuple[float, object]]" = OrderedDict()

    def get(self, key: str):
        if self.ttl_s <= 0:
            return None
        item = self._d.get(key)
        if item is None:
            return None
        ts, val = item
        # 边界：age >= ttl 视为过期（ttl 秒内命中，满 ttl 起失效）
        if self._now() - ts >= self.ttl_s:
            self._d.pop(key, None)
            return None
        self._d.move_to_end(key)          # LRU：命中刷新近用
        return val

    def set(self, key: str, value) -> None:
        if self.ttl_s <= 0:
            return
        self._d[key] = (self._now(), value)
        self._d.move_to_end(key)
        while len(self._d) > self.max_items:
            self._d.popitem(last=False)   # 淘汰最久未用

    def clear(self) -> None:
        self._d.clear()

    def __len__(self) -> int:
        return len(self._d)
