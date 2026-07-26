#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
review_queue.py — 对话审阅台（A，纯标准库 + 复用 web.db store）。

把生产 feedback 表拉成"待审列表"，供人工在 MeshClaw 对话里挑靠谱需求：
  list   拉待审(默认 status=new) + 垃圾/超短/重复预过滤 + 优先级 + 摘要
  stats  按 status 计数
  accept <id> [<id>...]  status→accepted(去TTL,进 pipeline 队列)   ← 人工授权=门
  reject <id> [<id>...]  status→rejected(留TTL,到期自动清)          ← 人工授权=门

存储：--store dynamo（生产,需 SF_TABLE_PREFIX + AWS creds）| memory（测试/dry-run）。
红线：accept/reject 是生产数据写,必须由人工在对话里逐条授权;本工具只忠实执行,不自动判定采纳。

triage 纯函数(is_spam/normalize_text/find_duplicates/priority_of/triage)确定性,可单测。
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT + "/src" not in sys.path:
    sys.path.insert(0, ROOT + "/src")

MIN_TEXT_LEN = 8          # 短于此判为垃圾(无效需求)
VALID_STATUS = {"new", "triaged", "accepted", "in_progress", "shipped", "rejected", "expired"}
# 优先级：bug 最高(修复优先) → improve → new_feature → remove(删除最谨慎/最低自动)
_PRIO = {"bug": 0, "improve": 1, "new_feature": 2, "improve_feature": 1, "remove": 3, "remove_feature": 3}


# ---------- triage 纯函数（确定性，可单测） ----------

def normalize_text(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def is_spam(row: dict):
    """返回 (是否垃圾, 原因)。仅结构性判定，不做语义。"""
    text = (row.get("text") or "").strip()
    if not text:
        return True, "空文本"
    if len(text) < MIN_TEXT_LEN:
        return True, "过短(<%d字)" % MIN_TEXT_LEN
    if row.get("kind") and row["kind"] not in ("bug", "improve", "new_feature", "remove",
                                               "improve_feature", "remove_feature"):
        return True, "非法 kind=%r" % row.get("kind")
    return False, ""


def find_duplicates(rows: list) -> dict:
    """按归一化 text 找重复；返回 {id: 首个同文本id}（首个不算重复）。"""
    seen, dup = {}, {}
    for r in rows:
        key = normalize_text(r.get("text", ""))
        if not key:
            continue
        if key in seen:
            dup[r.get("id")] = seen[key]
        else:
            seen[key] = r.get("id")
    return dup


def priority_of(row: dict) -> int:
    return _PRIO.get(row.get("kind", ""), 5)


def triage(rows: list) -> list:
    """给每条打 flags：spam/spam_reason/dup_of/priority；按 (非垃圾,非重复,优先级,时间) 排序。"""
    dup = find_duplicates(rows)
    out = []
    for r in rows:
        spam, reason = is_spam(r)
        out.append({
            "id": r.get("id"), "kind": r.get("kind"), "page": r.get("page"),
            "text": r.get("text", ""), "claim": r.get("claim_code"),
            "created": r.get("created_gmt8", ""), "status": r.get("status"),
            "spam": spam, "spam_reason": reason,
            "dup_of": dup.get(r.get("id")), "priority": priority_of(r),
        })
    out.sort(key=lambda x: (x["spam"], x["dup_of"] is not None, x["priority"], x["created"]))
    return out


# ---------- store 接入 ----------

def _store():
    import web.db as db
    return db.get_store()


def cmd_list(args):
    rows = _store().list_feedback(args.status)
    items = triage(rows)
    if not args.all:
        items = [x for x in items if not x["spam"] and x["dup_of"] is None]
    print("待审(status=%s)：%d 条%s" % (args.status, len(items), "（已滤垃圾/重复；--all 看全部）" if not args.all else ""))
    for x in items:
        flags = []
        if x["spam"]:
            flags.append("🗑%s" % x["spam_reason"])
        if x["dup_of"]:
            flags.append("♻dup→%s" % x["dup_of"])
        p = {0: "🔴bug", 1: "🟠改进", 2: "🟢新增", 3: "⚫删除"}.get(x["priority"], "·")
        print("  [%s] %s %s | %s | %s%s" % (
            x["id"], p, x["page"] or "-", (x["text"] or "")[:60],
            "认领%s " % x["claim"] if x["claim"] else "", " ".join(flags)))
    return 0


def cmd_stats(args):
    rows = _store().list_feedback(None)
    from collections import Counter
    c = Counter(r.get("status", "?") for r in rows)
    print("feedback 总计 %d：%s" % (len(rows), dict(c)))
    return 0


def _set_status(args, target):
    if target not in VALID_STATUS:
        print("非法 status: %s" % target); return 2
    st = _store()
    ok = 0
    for fid in args.ids:
        try:
            st.set_feedback_status(fid, target)
            print("  ✅ %s → %s" % (fid, target)); ok += 1
        except Exception as e:  # noqa
            print("  ❌ %s: %r" % (fid, e))
    print("完成 %d/%d → %s（生产数据写,人工授权执行）" % (ok, len(args.ids), target))
    return 0 if ok == len(args.ids) else 2


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("--status", default="new"); p.add_argument("--all", action="store_true")
    sub.add_parser("stats")
    pa = sub.add_parser("accept"); pa.add_argument("ids", nargs="+")
    pr = sub.add_parser("reject"); pr.add_argument("ids", nargs="+")
    ap.add_argument("--store", choices=["dynamo", "memory"], default="memory",
                    help="dynamo=生产(需SF_TABLE_PREFIX+creds); memory=测试")
    args = ap.parse_args()
    # store 选择：dynamo → 设 env 让 get_store 走 DynamoDBStore
    if args.store == "dynamo":
        os.environ["SF_STORE"] = "dynamo"
        os.environ.setdefault("SF_TABLE_PREFIX", "surf-forecast-dev")
        # botocore 读 AWS_DEFAULT_REGION（非 AWS_REGION）；本项目单区 ap-northeast-1，强制设两者
        os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"] = os.getenv("SF_AWS_REGION", "ap-northeast-1")
    else:
        os.environ.pop("SF_STORE", None)
    if args.cmd == "list":
        return cmd_list(args)
    if args.cmd == "stats":
        return cmd_stats(args)
    if args.cmd == "accept":
        return _set_status(args, "accepted")
    if args.cmd == "reject":
        return _set_status(args, "rejected")


if __name__ == "__main__":
    sys.exit(main())
