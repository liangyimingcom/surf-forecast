#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
surf_triage.py — surf-forecast 每日 triage 仪式 cron（G3，人主导治理模型 v5）。

只读拉生产 feedback 待审队列 → 预过滤 → 推摘要给人。**绝不自动改 status**（accept/reject 由人在对话授权）。
cron 本体仅用 stdlib(subprocess/os)；boto3+AWS creds 在项目 venv 的 review_queue.py 子进程里跑，
避开 gateway python 无 boto3 的限制。

注册：script='~/.meshclaw/crons/surf_triage.py:daily_triage'，每天 09:30 Asia/Shanghai，timeout≥120。
"""
import os
import subprocess

PROJ = "/Users/yiming/Downloads/all_the_meshclaw/surf-forecast/surf-forecast-kiro-v2"
PY = PROJ + "/.venv/bin/python"
RQ = PROJ + "/tools/review_queue.py"


def _run(args, timeout=120):
    env = dict(os.environ)
    env.setdefault("AWS_PROFILE", "oversea1")
    env["AWS_DEFAULT_REGION"] = env["AWS_REGION"] = "ap-northeast-1"
    try:
        p = subprocess.run([PY, RQ, "--store", "dynamo", *args],
                           cwd=PROJ, capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, (p.stdout or ""), (p.stderr or "")
    except Exception as e:  # noqa
        return 1, "", "EXC: %r" % e


def daily_triage(ctx):
    """每日只读摘要。有可审条目才通知；空队列/纯垃圾静默；出错通知一次便于修。"""
    rc, out, err = _run(["list", "--status", "new"])          # 默认已滤垃圾/重复
    if rc != 0:
        ctx.notify("🌊 surf-forecast 每日 triage：拉取失败（可能 AWS 凭证过期）。\n%s"
                   % (err.strip()[-400:] or out.strip()[-400:]))
        return
    lines = [l for l in out.splitlines() if l.strip()]
    header = lines[0] if lines else ""
    # 首行形如 "待审(status=new)：N 条…"；N=0 则静默（不打扰）
    n = 0
    import re
    m = re.search(r"：(\d+)\s*条", header)
    if m:
        n = int(m.group(1))
    if n == 0:
        return  # 无可审条目，静默
    _, stats_out, _ = _run(["stats"])
    body = "🌊 surf-forecast 每日 triage · 待审用户建议 %d 条\n\n%s\n\n%s\n\n在对话里说「接受 <id>」/「驳回 <id>」我来执行（生产 status 写，你授权才动）。" % (
        n, "\n".join(lines[:15]), stats_out.strip())
    ctx.notify(body)
