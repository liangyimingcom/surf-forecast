# Tasks — Surf Report Web（v2）

> 前置：引擎能 build_context→render(JSON 含 wdeg)。UI 基准 web/浪报MVP.html。

## 阶段 0：前端契约（零后端可验证）
- [x] 0.1 web/浪报MVP.html 实现全部会员视图（双模式/三图表/离岸风质条/昨日回看）— 当前已完成
- [ ] 0.2 抽 DAYS/HISTORY/REPORT 形状为 web/report.schema.json（前后端契约单一来源，含 wdeg/tp2/tideEvents）_(R2.4)_

## 阶段 1：后端骨架与鉴权
- [x] 1.1 FastAPI app + db(users/members/saved_spots/accuracy_votes) + 中间件 _(R6)_ ✅ app.py + db.py（InMemoryStore + **DynamoDBStore** moto验证，SF_STORE=dynamo 切换；compute env 已接，待 apply 生效）
- [x] 1.2 auth.py 注册(argon2)/登录/登出 _(R1.1,1.2,1.6;W2)_ ✅ argon2 哈希 + 服务端 session token
- [x] 1.3 deps.current_user + 401 保护 _(R1.3;W1)_ ✅ httponly cookie，前端零信任
- [x] 1.4 members 等级/配额 _(R1.4,1.5;W3)_ ✅ clamp_days(free=3/paid=7)
- [x] 1.5 test_auth + test_members ✅ test_web 8 项（注册/登录/登出/401/配额钳制）

## 阶段 2：查询接口
- [x] 2.1 query.py 校验+region阈值 _(R2.1,5.2)_ ✅ 经纬度校验（region阈值待多海域）
- [x] 2.2 接引擎→返回 REPORT(含 wdeg) _(R2.4,5.1)_ ✅ /api/report → build_context→render_json
- [x] 2.3 内陆/无数据报错 _(R2.5)_ ✅ 502 + 错误信息
- [x] 2.4 history.py 昨日回算 _(R3.1)_ ✅ deps.get_history + /api/report/history（feedback spec P6 接入）
- [x] 2.5 test_query + test_contract(校验 wdeg/tp2 齐全) _(W4,W7)_ ✅ 含 wdeg 断言

## 阶段 3：缓存容错
- [ ] 3.1 cache.py TTL _(R4.1,4.2)_
- [ ] 3.2 Open-Meteo 故障降级不白屏 _(R4.3;W8)_
- [ ] 3.3 test_cache

## 阶段 4：保存浪点
- [ ] 4.1 spots.py CRUD _(R2.3)_

## 阶段 5：前端对接（MVP→动态，阶段 A）
- [x] 5.1 移除内嵌 DAYS/HISTORY，改 fetch /api/report 与 /history _(R2.4,3.1)_ ✅ const→let + loadLive() fetch（失败回退内嵌不白屏）
- [x] 5.2 门禁占位→真 /api/auth + 会话态 _(R1;W9)_ ✅ SF_LOGIN→/api/auth/login(credentials:include)；**门禁移除（2026-06-25）**：页面加载即 bootstrap→demoAuth(固定 demo 账号建会话)→loadLive 直接进入；顶部 meta 校准时间戳/日期范围随实时数据更新（数据诚实红线）
- [ ] 5.3 自定义经纬度+保存浪点接 /api/spots _(R2.2,2.3)_
- [x] 5.4 走查对齐 UI 黄金样本（双模式/三图表/离岸风质条/HTML图例/GMT+8） _(W5,W6,W10)_ ✅ headless Chromium 走查(2026-06-25)：双模式按钮、SVG 图表 **0 NaN/负宽**、Hero/日期条/逐日卡/剧情当日实时(GMT+8 周四 2026-06-25)、校准时间戳实时；JS 报错仅 favicon 404（非代码）。🔸 残留：月相/日出日落为静态值（API 未提供，次要）

## 阶段 6：前端演进（阶段 B，可选）
- [ ] 6.1 组件化(Vite)、会员中心、配额提示/升级引导 _(R1.5,3.x)_
- [ ] 6.2 响应式与可访问性打磨

## 阶段 7：安全上线
- [ ] 7.1 test_security（无泄露/限流/注入） _(R6;W9)_
- [ ] 7.2 密钥环境变量、部署文档

## 依赖
```
0.2→1.x→2.x→3.x→5.x→6.x→7.x ; 4.x∥ ; 引擎(JSON含wdeg)→2.2/2.4
```

## 完成定义
代码+单测+满足需求+前端走查对齐基准无倒退+报告不违反红线+鉴权无前端绕过+全程 GMT+8。
