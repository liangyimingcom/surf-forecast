#!/usr/bin/env python3
"""P1.3 生产注册表灌入 — 把石老人 58 浪点快照写入 DynamoDB spot_registry。

用法(生产, 一次性):
  SF_STORE=dynamo SF_TABLE_PREFIX=surf-forecast-dev AWS_PROFILE=oversea1 \
    PYTHONPATH=src python tools/load_registry.py reference/data/shilaoren_spots.json

不带 SF_STORE 时写内存(仅演示计数)。写入走 _to_decimal(红线)。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from web import db, seed  # noqa: E402

path = sys.argv[1] if len(sys.argv) > 1 else "reference/data/shilaoren_spots.json"
store = db.get_store()
n = seed.seed_from_file(store, path)
target = "DynamoDB" if os.getenv("SF_STORE") == "dynamo" else "内存(演示)"
active = len(store.list_active_registry() or [])
print(f"[load_registry] 灌入 {n} 浪点 → {target}；当前 active+refresh_enabled 注册表行={active}")
