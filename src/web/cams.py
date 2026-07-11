"""形态C · Task 4 —— /api/cams 直播目录只读接口（FastAPI APIRouter，单一真源）。

本模块是 `/api/cams` 端点的**权威实现**，被真实应用 `src/web/app.py` 通过
`from .cams import router as cams_router; app.include_router(cams_router)` 挂载。
本文件在 taskrunner git 目录留有**字节一致**的跟踪副本，供审阅代理直接核对端点代码，
并由 `tools/verify_cams_api.py` 独立单测（mount 本 router 到裸 app + dependency_overrides）。

契约（north_star 红线 + Task 4 裁定）：
- **受保护(401)**：与 `/api/spots` 同一 `Depends(deps.current_user)`——未登录一律 401（直播非完全公开）。
- **只读**：仅注册 GET；POST/PUT/DELETE/PATCH → 405（无写入面）。不复刻登录/支付/社区写入。
- **slug→live_src 目录**：从 `list_active_registry()` 仅取含 `live_src` 的行；国外(live_src=None)自动过滤。
- **视频不经后端**：仅下发上游 live_src URL，前端 hls.js 直连；来源+研究免责随响应下发。
- **Decimal 兼容**：lat/lon 用 float() 兼容 DynamoDB Decimal / 内存 float。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from . import db, deps

router = APIRouter()

# 直播来源免责（合规红线：石老人逆向仅研究用途；视频由前端 hls.js 直连上游、不经本后端）
CAMS_DISCLAIMER = (
    "直播源自石老人 isurf 上游(isurfvideo.c-pan.cn)，前端 hls.js 直连、不经本后端转发；"
    "坐标与直播链接仅供研究用途，浪点朝向为默认估算待校准；国外浪点无上游直播源。"
)


@router.get("/api/cams")
def cams_list(user: dict = Depends(deps.current_user)) -> dict:
    """P2 形态C：直播源目录(只读, slug→live_src 映射)。
    鉴权：按 /api/spots 模式受保护——未登录 401（直播非完全公开）。
    视频流由前端 hls.js 直连上游、不经后端转发；本接口只读目录，不复刻登录/支付/社区写入。
    从注册表返回含 live_src 的浪点; lat/lon 兼容 Decimal(DynamoDB)/float(内存)。附来源免责标注。"""
    rows = db.get_store().list_active_registry() or []
    cams = []
    for r in rows:
        if not r.get("live_src"):
            continue
        try:
            lat, lon = float(r["lat"]), float(r["lon"])
        except (TypeError, ValueError, KeyError):
            continue
        cams.append({
            "slug": r["slug"], "name": r.get("spot"), "city": r.get("city"),
            "lat": lat, "lon": lon, "live_src": r.get("live_src"),
            "post_url": r.get("post_url"),
        })
    return {"cams": cams, "count": len(cams), "disclaimer": CAMS_DISCLAIMER}
