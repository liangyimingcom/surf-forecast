# Design — Surf Report Web（v2）

> 回应 requirements.md。UI 基准 = web/浪报MVP.html（已实现的会员视图）。

## 1. 架构

```
前端 SPA（类 MVP）──HTTPS/JSON──> FastAPI 后端 ──import──> surf_forecast 引擎 ──> Open-Meteo
  鉴权态/查询/双模式/SVG图表/昨日回看      auth/members/query/cache/feedback
```

后端只做鉴权+编排+缓存，不重写分析（继承事实红线）。

## 2. 技术选型

| 层 | 选型 |
|----|------|
| 后端 | FastAPI（同语言 import 引擎） |
| 鉴权 | argon2 + httponly cookie / JWT |
| DB | SQLite→Postgres（users/members/saved_spots/accuracy_votes） |
| 缓存 | LRU→Redis |
| 前端 | 当前单 HTML → Vite+轻框架渐进迁移 |
| 图表 | 内联 SVG（已实现，零依赖） |

## 3. API（DATA CONTRACT）

```
POST /api/auth/{register,login,logout}
GET/POST /api/spots                     保存浪点
GET  /api/report?lat&lon&days     [鉴权] → REPORT
GET  /api/report/history?lat&lon  [鉴权] → HISTORY（昨日，past_days=1）
POST /api/accuracy/vote           [鉴权] → 记录自评（见 feedback spec）

REPORT.days[i] / HISTORY 形状见前端 DAYS/HISTORY（含 wdeg、tp2、tideEvents、dims、pa、lesson、plan）
```

前端从"内嵌 DAYS/HISTORY 常量"切换到"fetch 这些接口"即完成动态化——最小改动路径。

## 4. 后端模块（src/web/）

```
app.py    路由/中间件(HTTPS/CORS/限流)
auth.py   注册/登录/登出/argon2/令牌      (R1)
members.py 等级/配额                       (R1.4,1.5)
spots.py  保存浪点 CRUD                     (R2.3)
query.py  校验→region阈值→cache→引擎→JSON   (R2,R5)
history.py 昨日回算（引擎 past_days=1）      (R3.1; feedback spec)
cache.py  TTL 缓存 + 故障降级               (R4)
deps.py   current_user / 限流
db.py     模型
```

## 5. 前端（对齐已实现 MVP）

当前 `web/浪报MVP.html` 已实现全部视图组件，作为阶段 A 基线：

- 会员门禁（占位→接 /api/auth）、位置查询栏（占位→接 /api/report）
- 双模式 setMode、日期条 strip、Hero、剧情、逐日卡片
- 三类 SVG：`waveChart`(双周期) / `windTideChart`(离岸着色+风质条 `windQualityStrip`) / `lifecycleChart`
- HTML 图例 `waveLegend` 等、五维 dims、物理小课堂、行动方案
- 昨日回看 `renderVerify` + 自评 `rateYesterday`（见 feedback spec）
- 风向编码 `windKind/windArrow`，浪点朝向 `SPOT_FACING=157`

阶段 A：移除内嵌常量，改 fetch；门禁接真鉴权。阶段 B：组件化(Vite)、会员中心、配额 UI。

## 6. 区域阈值

`region_for(lat,lon)` → 选 thresholds*.yaml（含 spot_facing_deg）。MVP 先支持黄海，其他区给"阈值未标定"提示。

## 7. 安全

argon2；httponly+secure cookie；CORS 白名单；限流；pydantic 校验；前端零信任。

## 8. 测试

test_auth(W1,W2) / test_members(W3) / test_query(W4,W7) / test_contract(返回含wdeg,W4) / test_view_parity(对齐基准,W5,W6) / test_cache(W8) / test_security(W9)。

## ADR
- ADR-W1 后端复用引擎不重写。
- ADR-W2 用 MVP 的 DAYS/HISTORY 形状当 API 契约（含 wdeg）。
- ADR-W3 鉴权全后端。
- ADR-W4 前端先沿用单文件再演进。
- ADR-W5（v2）SVG 自绘图表 + HTML 图例，零图表库依赖。
