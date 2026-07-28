"""每日刷新入口 —— 由 EventBridge Scheduler 触发的 ECS RunTask 执行（D5 + R2 决策9/10）。

容器命令覆盖：
  python -m web.refresh_cli          # 主跑（02:00/14:00）：注册表全量
  python -m web.refresh_cli retry    # 补跑哨兵（06:00）：manifest 缺失点；主跑没跑(断链)→退化全量

R2 一致性契约：逐点写 {slug}/latest.json + 结束原子写 manifest.json（try/finally——
哪怕全失败也落记录，否则 /status 会无声停在昨天）。recommend/状态页/补跑三处统一读 manifest。
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time

from . import db
from .refresh import (
    S3CacheReader,
    S3CacheWriter,
    active_registry_spots,
    build_manifest,
    load_manifest,
    missing_from_manifest,
    now_gmt8,
    recycle_cold_spots,
    refresh_spots,
    scheduled_refresh,
)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = argv if argv is not None else sys.argv[1:]
    kind = "retry" if (args and args[0] == "retry") else "main"

    bucket = os.getenv("SF_CACHE_BUCKET")
    if not bucket:
        print("缺少 SF_CACHE_BUCKET 环境变量", file=sys.stderr)
        return 2
    store = db.get_store()
    writer = S3CacheWriter(bucket)
    reader = S3CacheReader(bucket)
    prev = load_manifest(reader)
    today = now_gmt8().date().isoformat()

    summary: dict[str, str] = {}
    expected: list[str] = []
    t0 = time.monotonic()
    try:
        if kind == "main":
            recycled = recycle_cold_spots(store)          # 先回收冷点（省调用）
            print("recycled cold:", json.dumps(recycled, ensure_ascii=False))
            expected = [c["slug"] for c in active_registry_spots(store)]
            summary = scheduled_refresh(store, writer)
        else:
            missing = missing_from_manifest(prev, today)
            if missing is None:
                # 断链哨兵：主跑没留下今日 manifest → 全量兜底（R2 决策10）
                print("retry: 今日无 manifest（主跑未跑/断链），退化全量")
                cfgs = active_registry_spots(store)
            elif not missing:
                print("retry: 今日已全覆盖，无缺失点")
                cfgs = []
            else:
                by_slug = {c["slug"]: c for c in active_registry_spots(store)}
                cfgs = [by_slug[s] for s in missing if s in by_slug]
                print("retry: 补跑缺失点", json.dumps(missing, ensure_ascii=False))
            expected = [c["slug"] for c in cfgs]
            if cfgs:
                summary = refresh_spots(cfgs, writer)
    finally:
        # 契约：无论成败必落 manifest（全失败也要留痕，/status 不无声停摆）
        manifest = build_manifest(prev, kind, expected, summary,
                                  duration_s=time.monotonic() - t0)
        try:
            writer.put("manifest.json", manifest)
            print("manifest:", json.dumps(
                {k: manifest[k] for k in ("run_id", "kind", "date")}
                | {"expected_n": len(manifest["expected"]),
                   "ok_n": len(manifest["succeeded"])}, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            print(f"manifest 写入失败: {e}", file=sys.stderr)

    print("refresh summary:", json.dumps(summary, ensure_ascii=False))
    if kind == "retry" and not expected:
        return 0  # 无缺失点的补跑是成功
    # 全部跳过视为失败（便于告警）；至少一个 ok 则成功
    return 0 if any(v == "ok" for v in summary.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
