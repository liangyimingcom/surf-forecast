"""R2 一次性迁移：为存量 spot_registry 行补齐治理三字段（Fable5迭代建议-R2 §1.1）。

- op_status: 从 name/city 的「（维护中）」「(待开放)」后缀解析，展示名/city 还原干净
- beach_group: governance.BEACH_GROUPS 人工标注表
- is_test: E2E/测试 名称前缀

幂等可重跑。用法：
  AWS_PROFILE=oversea1 AWS_REGION=ap-northeast-1 \
  PYTHONPATH=src python3 tools/migrate_governance.py --table surf-forecast-dev-spot_registry [--dry-run]
"""
from __future__ import annotations

import argparse
import sys

sys.path.insert(0, "src")

from web import governance  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import boto3
    t = boto3.resource("dynamodb").Table(args.table)

    items, resp = [], t.scan()
    items.extend(resp.get("Items", []))
    while resp.get("LastEvaluatedKey"):
        resp = t.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp.get("Items", []))

    changed = 0
    for row in items:
        before = (row.get("spot"), row.get("city"), row.get("op_status"),
                  row.get("beach_group"), row.get("is_test"))
        governance.annotate_row(row)
        after = (row.get("spot"), row.get("city"), row.get("op_status"),
                 row.get("beach_group"), row.get("is_test"))
        if before == after:
            continue
        changed += 1
        print(f"{row['slug']}: {before} -> {after}")
        if not args.dry_run:
            t.put_item(Item=row)

    print(f"\n{'DRY-RUN ' if args.dry_run else ''}migrated {changed}/{len(items)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
