"""FastAPI 应用 —— 鉴权 + 位置查询接引擎（web R1/R2, design web §1/§3）。

路由：
  GET  /api/health
  POST /api/auth/{register,login,logout}
  GET  /api/report?lat&lon&days&spot        [鉴权] → REPORT(含 wdeg)
  GET  /api/report/history?lat&lon&spot      [鉴权] → HISTORY（昨日，P6 完善）
鉴权全后端；前端零信任；密钥/凭据走环境变量（禁明文）。
"""

from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from . import auth, db, deps, feedback, spots

app = FastAPI(title="Surf Forecast API", version="0.1.0")

# 前端 HTML 由后端在 `/` 直供（去 CloudFront 后，ALB 直接服务前端）
_FRONTEND = os.getenv("SF_FRONTEND", "/app/frontend/浪报MVP.html")


@app.get("/", response_class=HTMLResponse)
def index() -> FileResponse:
    if os.path.exists(_FRONTEND):
        return FileResponse(_FRONTEND, media_type="text/html; charset=utf-8")
    raise HTTPException(status_code=404, detail="前端未内置")


class Credentials(BaseModel):
    email: str
    password: str = Field(min_length=6)
    level: str = "free"


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/auth/register")
def register(body: Credentials) -> dict:
    try:
        return auth.register(db.get_store(), body.email, body.password, body.level)
    except auth.AuthError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/auth/login")
def login(body: Credentials, request: Request, response: Response) -> dict:
    try:
        token = auth.login(db.get_store(), body.email, body.password)
    except auth.AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    # secure 按请求协议自动判定：https→True（生产），http→False（本地/测试）
    secure = request.url.scheme == "https" or os.getenv("SF_COOKIE_SECURE") == "1"
    response.set_cookie(
        deps.COOKIE_NAME, token, httponly=True, secure=secure,
        samesite="lax", max_age=60 * 60 * 12,
    )
    return {"ok": True}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response,
           user: dict = Depends(deps.current_user)) -> dict:
    # 服务端删除会话 + 清 cookie（前端零信任）
    token = request.cookies.get(deps.COOKIE_NAME)
    auth.logout(db.get_store(), token)
    response.delete_cookie(deps.COOKIE_NAME)
    return {"ok": True}


def _validate_coord(lat: float, lon: float) -> None:
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail="经纬度非法")


@app.get("/api/report")
def report(lat: float, lon: float, spot: str = "未命名浪点", days: int = 3,
           user: dict = Depends(deps.current_user)) -> dict:
    _validate_coord(lat, lon)
    days = deps.clamp_days(user["level"], days)
    try:
        return deps.get_report(lat, lon, days, spot)
    except Exception as e:  # noqa: BLE001
        # 内陆/无海浪数据或数据源故障
        raise HTTPException(status_code=502, detail=f"浪报生成失败：{e}")


@app.get("/api/report/history")
def report_history(lat: float, lon: float, spot: str = "未命名浪点",
                   user: dict = Depends(deps.current_user)) -> dict:
    _validate_coord(lat, lon)
    try:
        history = deps.get_history(lat, lon, 6, spot)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"昨日回看生成失败：{e}")
    return {"history": history}


class Vote(BaseModel):
    spot: str
    date: str
    kind: str


@app.post("/api/accuracy/vote")
def accuracy_vote(body: Vote, user: dict = Depends(deps.current_user)) -> dict:
    try:
        return feedback.record_vote(db.get_store(), user["email"], body.spot, body.date, body.kind)
    except feedback.FeedbackError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/accuracy/bias")
def accuracy_bias(spot: str, user: dict = Depends(deps.current_user)) -> dict:
    return feedback.compute_bias(db.get_store(), user["email"], spot)


# —— 浪点管理（custom-spots R2，全 401 保护）——
class SpotCreate(BaseModel):
    name: str
    lat: float
    lon: float
    facing: float | None = None
    days: int = 6


class SpotUpdate(BaseModel):
    name: str | None = None
    facing: float | None = None


@app.get("/api/spots")
def spots_list(user: dict = Depends(deps.current_user)) -> dict:
    return {"spots": spots.list_spots(db.get_store(), user)}


@app.post("/api/spots")
def spots_create(body: SpotCreate, user: dict = Depends(deps.current_user)) -> dict:
    try:
        return spots.create_spot(db.get_store(), user, body.name, body.lat, body.lon,
                                 facing=body.facing, days=body.days,
                                 budget_hook=deps.instant_budget)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except spots.SpotError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.patch("/api/spots/{slug}")
def spots_update(slug: str, body: SpotUpdate,
                 user: dict = Depends(deps.current_user)) -> dict:
    try:
        return spots.update_spot(db.get_store(), user, slug, name=body.name, facing=body.facing)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except spots.SpotError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/spots/{slug}")
def spots_delete(slug: str, user: dict = Depends(deps.current_user)) -> dict:
    try:
        return spots.delete_spot(db.get_store(), user, slug)
    except spots.SpotError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/spots/{slug}/select")
def spots_select(slug: str, user: dict = Depends(deps.current_user)) -> dict:
    try:
        return spots.select_spot(db.get_store(), user, slug)
    except spots.SpotError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/catalog")
def catalog_list(user: dict = Depends(deps.current_user)) -> dict:
    """P3 形态C：全国浪点目录(58+)。登录可见；从注册表返回基础信息+区域+是否有直播。
    lat/lon 兼容 Decimal(DynamoDB)/float(内存)。评分留待前端按点取报(用缓存)。"""
    rows = db.get_store().list_active_registry() or []
    catalog = []
    for r in rows:
        try:
            lat, lon = float(r["lat"]), float(r["lon"])
        except (TypeError, ValueError, KeyError):
            continue
        catalog.append({
            "slug": r["slug"], "name": r.get("spot"), "city": r.get("city"),
            "region": r.get("region_cn", "其他"), "lat": lat, "lon": lon,
            "facing": float(r.get("spot_facing_deg", 0) or 0),
            "facing_calibrated": bool(r.get("facing_calibrated", False)),
            "has_live": bool(r.get("live_src")), "days": int(r.get("days", 6) or 6),
        })
    return {"catalog": catalog}


@app.get("/api/catalog/scores")
def catalog_scores(user: dict = Depends(deps.current_user)) -> dict:
    """P3.2 形态C：批量评分(从每日预算缓存读，避免 58×实时)。
    无缓存桶(本地/未配置)→ scores 空、cached=False；前端可用点击已看浪点回填徽标兜底。"""
    reader = deps._cache_reader()
    if reader is None:
        return {"scores": {}, "cached": False}
    rows = db.get_store().list_active_registry() or []
    scores = {}
    for r in rows:
        try:
            rep = reader.get(f"{r['slug']}/latest.json")
            if rep and rep.get("days"):
                scores[r["slug"]] = rep["days"][0].get("score")
        except Exception:  # noqa: BLE001
            pass
    return {"scores": scores, "cached": True}


# 直播目录只读接口 /api/cams（形态C Task 4）：权威实现在 web.cams（单一真源），此处挂载。
# 受保护(401, 同 /api/spots) · 只读(仅GET) · slug→live_src · 视频前端 hls.js 直连上游不经后端 · 附来源免责。
from .cams import router as cams_router  # noqa: E402

app.include_router(cams_router)
