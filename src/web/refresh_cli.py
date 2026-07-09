"""每日刷新入口 —— 由 EventBridge Scheduler 触发的 ECS RunTask 执行（D5）。

容器命令覆盖为 `python -m web.refresh_cli`；从 env 取 S3 缓存桶，跑 refresh_spots。
与在线请求读写解耦：本入口只「写」预算缓存。
"""

from __future__ import annotations

import json
import logging
import os
import sys

from . import db
from .refresh import S3CacheWriter, recycle_cold_spots, scheduled_refresh


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    bucket = os.getenv("SF_CACHE_BUCKET")
    if not bucket:
        print("缺少 SF_CACHE_BUCKET 环境变量", file=sys.stderr)
        return 2
    store = db.get_store()
    writer = S3CacheWriter(bucket)
    recycled = recycle_cold_spots(store)              # 先回收冷点（省调用）
    summary = scheduled_refresh(store, writer)        # 注册表驱动（含 DEFAULT_SPOTS 兜底）
    print("recycled cold:", json.dumps(recycled, ensure_ascii=False))
    print("refresh summary:", json.dumps(summary, ensure_ascii=False))
    # 全部跳过视为失败（便于告警）；至少一个 ok 则成功
    return 0 if any(v == "ok" for v in summary.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
