#!/usr/bin/env python3
"""关键端点计数告警（Phase 0 P0.5）——纯标准库(urllib)，可本地/cron 跑。

复用前端 demoAuth 的 demo 账号登录，检查 /api/catalog /api/cams /api/report 计数。
任一关键计数跌 0（"冷点炸弹"同类事故） → 打印 ALERT 并 exit 2；正常 exit 0。

用法：python3 tools/monitor_counts.py [BASE_URL]
  BASE_URL 缺省取 env SF_MONITOR_URL，再缺省 https://d2hmhl7n8yga53.cloudfront.net
告警接线（send_message/cron）属 ops：cron 里 `python3 tools/monitor_counts.py || <notify>`。
"""
import json
import os
import sys
import urllib.request
from http.cookiejar import CookieJar

BASE = (sys.argv[1] if len(sys.argv) > 1 else
        os.getenv("SF_MONITOR_URL", "https://d2hmhl7n8yga53.cloudfront.net")).rstrip("/")
DEMO = {"email": "demo@surf.local", "password": "surf2026demo"}
TIMEOUT = 15

_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def _post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        return _opener.open(req, timeout=TIMEOUT).status
    except urllib.error.HTTPError as e:
        return e.code


def _get_json(path):
    req = urllib.request.Request(BASE + path)
    with _opener.open(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def _auth():
    if _post("/api/auth/login", DEMO) != 200:
        _post("/api/auth/register", DEMO)
        if _post("/api/auth/login", DEMO) != 200:
            raise SystemExit("AUTH_FAIL: demo 登录失败")


def main():
    _auth()
    catalog = len(_get_json("/api/catalog").get("catalog", []))
    cams = _get_json("/api/cams").get("count", 0)
    rep = _get_json("/api/report?lat=36.092&lon=120.468&spot=%E9%9D%92%E5%B2%9B%E5%B1%B1%E4%B8%9C%E5%A4%B4&days=3")
    report_days = len(rep.get("days", []))
    print(f"[monitor] {BASE} · catalog={catalog} cams={cams} report_days={report_days}")
    alerts = []
    if catalog == 0:
        alerts.append("catalog=0（全国目录空——疑似冷点回收/注册表异常）")
    if cams == 0:
        alerts.append("cams=0（直播目录空）")
    if report_days == 0:
        alerts.append("report_days=0（引擎取报为空）")
    if alerts:
        print("🔴 ALERT " + BASE + " :: " + " ; ".join(alerts))
        sys.exit(2)
    print("✅ OK 关键端点计数正常")


if __name__ == "__main__":
    main()
