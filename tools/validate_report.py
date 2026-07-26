#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_report.py — REPORT 数据契约校验器（stdlib，无 jsonschema 依赖）。

对照 web/report.schema.json 的**红线关键子集**校验 render_json 输出：
- days 非空;每日含 wdeg 数字数组 + 图表字段(times/hs/wind/gust/tp)数字数组(与 times 等长);
- tp2 为 数字|null 数组;tideEvents 为 [小时,潮位] 数字对;
- calibratedAt 以 GMT+8 结尾;date 为 YYYY-MM-DD;恰好一个 best 日;
- history 为 null 或 day 形状+predict,且**历史日期不与预报区重叠**(红线)。

返回错误列表（空=通过）。供 pytest 与 CI 用；bool 校验器可作契约漂移守卫。
"""
import re

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NUM_ARRAYS = ("times", "hs", "wind", "gust", "tp", "wdeg")


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _num_array(v):
    return isinstance(v, list) and all(_is_num(x) for x in v)


def _check_day(d, where, errs):
    if not isinstance(d, dict):
        errs.append("%s 不是对象" % where); return
    for k in ("date", "week"):
        if not isinstance(d.get(k), str):
            errs.append("%s.%s 缺失或非字符串" % (where, k))
    if not (isinstance(d.get("date"), str) and _DATE.match(d["date"])):
        errs.append("%s.date 非 YYYY-MM-DD" % where)
    for k in ("today", "best"):
        if not isinstance(d.get(k), bool):
            errs.append("%s.%s 非布尔" % (where, k))
    if not _is_num(d.get("score")):
        errs.append("%s.score 非数字" % where)
    n = len(d["times"]) if _num_array(d.get("times")) else None
    for k in _NUM_ARRAYS:
        if not _num_array(d.get(k)):
            errs.append("%s.%s 非数字数组(红线)" % (where, k))
        elif n is not None and len(d[k]) != n:
            errs.append("%s.%s 长度(%d)≠times(%d)" % (where, k, len(d[k]), n))
    # tp2: 数字|null 数组
    tp2 = d.get("tp2")
    if not (isinstance(tp2, list) and all(x is None or _is_num(x) for x in tp2)):
        errs.append("%s.tp2 非 数字|null 数组" % where)
    # tideEvents: [num,num] 对
    te = d.get("tideEvents")
    if not (isinstance(te, list) and all(
            isinstance(p, list) and len(p) == 2 and _is_num(p[0]) and _is_num(p[1]) for p in te)):
        errs.append("%s.tideEvents 非 [小时,潮位] 数字对数组" % where)


def validate_report(rep) -> list:
    errs = []
    if not isinstance(rep, dict):
        return ["REPORT 不是对象"]
    if not isinstance(rep.get("spot"), str):
        errs.append("spot 缺失或非字符串")
    coord = rep.get("coord")
    if not (isinstance(coord, list) and len(coord) == 2 and all(_is_num(c) for c in coord)):
        errs.append("coord 非 [lat,lon] 数字对")
    cal = rep.get("calibratedAt")
    if not (isinstance(cal, str) and cal.rstrip().endswith("GMT+8")):
        errs.append("calibratedAt 未以 GMT+8 结尾(时区红线)")
    if not isinstance(rep.get("ranking"), list):
        errs.append("ranking 非数组")
    days = rep.get("days")
    if not (isinstance(days, list) and days):
        errs.append("days 缺失或空(红线:非空)")
        return errs
    for i, d in enumerate(days):
        _check_day(d, "days[%d]" % i, errs)
    best_ct = sum(1 for d in days if isinstance(d, dict) and d.get("best") is True)
    if best_ct != 1:
        errs.append("best 日应恰好 1 个,实为 %d" % best_ct)
    # history: null 或 day+predict,且日期不与预报区重叠
    hist = rep.get("history")
    if hist is not None:
        _check_day(hist, "history", errs)
        if not isinstance(hist.get("predict"), dict):
            errs.append("history.predict 缺失或非对象")
        day_dates = {d.get("date") for d in days if isinstance(d, dict)}
        if hist.get("date") in day_dates:
            errs.append("history.date 与预报区重叠(红线:预报/历史互斥)")
    return errs


if __name__ == "__main__":
    import json
    import sys
    rep = json.load(open(sys.argv[1], encoding="utf-8")) if len(sys.argv) > 1 else json.load(sys.stdin)
    errs = validate_report(rep)
    if errs:
        print("❌ 契约校验失败 %d:" % len(errs))
        for e in errs:
            print("  -", e)
        sys.exit(2)
    print("✅ REPORT 合乎契约")
