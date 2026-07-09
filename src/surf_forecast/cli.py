"""命令行入口 —— 见 design.md 第 8/9 节、Task 7.1.

用法：
    python -m surf_forecast.cli --lat 36.092 --lon 120.468 \
        --days 7 --spot "青岛山东头" --out report.md [--style professional]
        [--config config/thresholds.yaml] [--past-days 1] [--format md|json]
"""

from __future__ import annotations

import argparse
import json
import sys

from . import analyze, render
from .validate import ReportValidationError


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="surf_forecast", description="冲浪浪报深度分析器")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--spot", type=str, default="未命名浪点")
    p.add_argument("--out", type=str, default="report.md")
    p.add_argument("--style", choices=["professional", "casual"], default="professional")
    p.add_argument("--config", type=str, default="config/thresholds.yaml")
    p.add_argument("--past-days", type=int, default=0,
                   help="历史回算天数（昨日回看用 1）")
    p.add_argument("--format", choices=["md", "json"], default="md",
                   help="输出格式：md(默认) 或 json(DATA CONTRACT，含 wdeg)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        ctx = analyze.build_context(
            args.lat, args.lon, args.days, args.spot, config_path=args.config)
    except ReportValidationError as e:
        # 红线：校验失败阻断输出，不写出半成品
        print(f"❌ 校验阻断（{e.field}）：{e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"❌ 取数/分析失败：{e}", file=sys.stderr)
        return 1

    if args.format == "json":
        out = json.dumps(render.render_json(ctx), ensure_ascii=False, indent=2)
    else:
        out = render.render_report(ctx, style=args.style, config_path=args.config)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"✅ 已写出 {args.out}（{args.format}，{len(ctx.days)} 日，校准 {ctx.calibrated_at:%Y-%m-%d %H:%M} GMT+8）")
    if ctx.warnings:
        print(f"⚠️ 可信度声明 {len(ctx.warnings)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
