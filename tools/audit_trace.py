#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_trace.py — 审计链贯通验证（D4，纯标准库）。

追溯并校验一条需求的全链路：
  需求ID ↔ pipeline审计(gates/verdict) ↔ 分支/PR/commit ↔ 版本tag ↔ CHANGELOG条目 ↔ 部署时间

每一环标 ✅存在 / ⏳待D3 / ❌断裂(不一致)。链全绿=可追溯发布；有 ⏳=尚未 ship；❌=审计链断裂需修。

用法：
  python3 tools/audit_trace.py --requirement-id seed-0001
  python3 tools/audit_trace.py --version v0.1.0        # 子链：版本↔CHANGELOG↔部署时间(基建演示)
  python3 tools/audit_trace.py --requirement-id seed-0001 --no-gh   # 跳过 gh 网络查询

约定：需求驱动的发布，CHANGELOG 摘要须含 `需求<ID>`（deploy.sh 发布时 SF_RELEASE_NOTE="需求<ID>: ..."）。
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, "reference", "data", "pipeline_audit.jsonl")
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")

PRESENT, PENDING, BROKEN = "✅存在", "⏳待D3", "❌断裂"


def sh(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, cwd=ROOT, timeout=timeout, capture_output=True, text=True)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:  # noqa
        return 1, "", "%r" % e


# ---------- 解析器（确定性，可单测） ----------

def load_audit(req_id):
    """从 pipeline_audit.jsonl 取该需求最新一条审计记录。"""
    if not os.path.exists(AUDIT):
        return None
    rec = None
    with open(AUDIT, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue  # 逐条隔离坏行
            if r.get("requirement_id") == req_id:
                rec = r  # 保留最后一条(最新)
    return rec


_CL_RE = re.compile(
    r"^-\s*(?P<date>[\d\-]+(?:\s+[\d:]+\s+GMT\+8)?)\s*·\s*(?P<ver>v[\d.]+)\s*·\s*"
    r"(?P<commit>[^·]+?)\s*·\s*(?P<note>.+?)\s*·\s*(?P<result>[^·]+)\s*$")


def parse_changelog():
    """解析 CHANGELOG.md 的 Releases 行 → [{date,ver,commit,note,result}]。"""
    out = []
    if not os.path.exists(CHANGELOG):
        return out
    for line in open(CHANGELOG, encoding="utf-8"):
        m = _CL_RE.match(line.rstrip())
        if m:
            out.append({k: m.group(k).strip() for k in ("date", "ver", "commit", "note", "result")})
    return out


def changelog_for_requirement(req_id, entries=None):
    """找摘要含 `需求<ID>` 的 CHANGELOG 条目。"""
    entries = entries if entries is not None else parse_changelog()
    key = "需求%s" % req_id
    return [e for e in entries if key in e["note"] or req_id in e["note"]]


def changelog_for_version(ver, entries=None):
    entries = entries if entries is not None else parse_changelog()
    return [e for e in entries if e["ver"] == ver]


# ---------- 链路环校验 ----------

def link(name, status, detail):
    return {"link": name, "status": status, "detail": detail}


def trace_requirement(req_id, use_gh=True):
    chain = []
    audit = load_audit(req_id)

    # 环1：需求ID ↔ pipeline 审计
    if audit:
        verdict = audit.get("verdict")
        ng = sum(1 for g in audit.get("gates", []) if g.get("ok"))
        nt = len(audit.get("gates", []))
        chain.append(link("需求↔pipeline审计", PRESENT,
                          "verdict=%s · 门 %d/%d 绿 · %s" % (verdict, ng, nt, audit.get("ts_gmt8", ""))))
        branch = audit.get("branch")
    else:
        chain.append(link("需求↔pipeline审计", BROKEN, "pipeline_audit.jsonl 无 %s 记录(先跑 req_pipeline)" % req_id))
        branch = None

    # 环2：分支/PR/commit
    if branch:
        pr_detail = "分支 %s" % branch
        st = PENDING
        if use_gh:
            rc, out, _ = sh(["gh", "pr", "list", "--head", branch, "--state", "all",
                             "--json", "number,state,mergeCommit", "--limit", "1"])
            if rc == 0 and out and out != "[]":
                try:
                    pr = json.loads(out)[0]
                    mc = (pr.get("mergeCommit") or {}).get("oid", "")[:7]
                    st = PRESENT
                    pr_detail = "PR #%s (%s)%s" % (pr.get("number"), pr.get("state"),
                                                    " merge=" + mc if mc else "")
                except Exception:
                    pass
        chain.append(link("分支↔PR↔commit", st,
                          pr_detail + ("" if st == PRESENT else " · 未开PR(待D3 --create-pr/人工)")))
    else:
        chain.append(link("分支↔PR↔commit", BROKEN, "无分支信息"))

    # 环3+4+5：版本tag ↔ CHANGELOG ↔ 部署时间（靠 CHANGELOG 含需求ID）
    cl = changelog_for_requirement(req_id)
    if cl:
        e = cl[-1]
        chain.append(link("CHANGELOG(需求ID)", PRESENT, "%s · %s · %s" % (e["ver"], e["date"], e["result"])))
        # 版本 tag 是否存在
        rc, out, _ = sh(["git", "tag", "-l", e["ver"]])
        tag_ok = bool(out.strip())
        chain.append(link("版本tag(git)", PRESENT if tag_ok else PENDING,
                          e["ver"] + ("(git tag 已打)" if tag_ok else "(git tag 未打→待D3发布时打)")))
        chain.append(link("部署时间", PRESENT, e["date"]))
    else:
        chain.append(link("CHANGELOG(需求ID)", PENDING, "CHANGELOG 无 需求%s 条目(待 D3 发布写入)" % req_id))
        chain.append(link("版本tag(git)", PENDING, "待 D3 发布时打 vX.Y.Z"))
        chain.append(link("部署时间", PENDING, "待 D3 发布"))

    return chain


def trace_version(ver):
    chain = []
    cl = changelog_for_version(ver)
    if cl:
        for e in cl:
            chain.append(link("CHANGELOG@%s" % ver, PRESENT,
                              "%s · %s · %s · %s" % (e["date"], e["commit"], e["note"][:40], e["result"])))
    else:
        chain.append(link("CHANGELOG@%s" % ver, BROKEN, "无该版本条目"))
    rc, out, _ = sh(["git", "tag", "-l", ver])
    chain.append(link("git tag %s" % ver, PRESENT if out.strip() else PENDING,
                      "已打" if out.strip() else "git tag 未打(仅 ECR 镜像 tag)"))
    return chain


def render(title, chain):
    print("=" * 64)
    print("审计链追溯 · %s" % title)
    print("=" * 64)
    for c in chain:
        print("  %s  %-18s %s" % (c["status"], c["link"], c["detail"]))
    statuses = {c["status"] for c in chain}
    print("-" * 64)
    if BROKEN in statuses:
        verdict, rc = "❌ 链路断裂(需修)", 3
    elif PENDING in statuses:
        verdict, rc = "⏳ 链路已接线,部分环待 D3 发布落地", 2
    else:
        verdict, rc = "✅ 审计链贯通", 0
    print("裁定: %s" % verdict)
    print("=" * 64)
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--requirement-id")
    ap.add_argument("--version")
    ap.add_argument("--no-gh", action="store_true")
    args = ap.parse_args()
    if args.version:
        return render("版本 %s" % args.version, trace_version(args.version))
    if args.requirement_id:
        return render("需求 %s" % args.requirement_id,
                      trace_requirement(args.requirement_id, use_gh=not args.no_gh))
    ap.error("需 --requirement-id 或 --version")


if __name__ == "__main__":
    sys.exit(main())
