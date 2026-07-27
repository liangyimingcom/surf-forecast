# Roadmap — 甲·忠实整体重建（Vite+Vue3）

> 排序原则：先排查降级态根因 → 后端契约重塑（前端可并行依赖）→ 前端脚手架/build 服务 → 逐页迁移（目录→详情→首页）→ 会员锁占位 → **新 E2E 全绿** → 切换切旧 → self-iterate 冻结 → 收尾。**新 E2E 绿之前不切 `/`**（甲-b 护栏）。
> 每阶段可独立本地验证；真部署留 **G 门**。遇边缘情况选**保守选项**（改动面最小/可逆），记 `docs/implementation-notes.md` 的 Deviations，继续推进不停等。

## R0 · 摸底 + 降级态根因（前置阻断）
- CodeLens SOP 摸底：`render_json`/`/api/report`/`/api/catalog/scores` 形状与爆炸半径、`demoAuth`/`#gate`/`SAMPLE_*`/硬编码泄漏定位。
- **排查线上降级态根因**（Fable5 §4.5 §5.5）：为何横幅显"示例数据"、评分缓存流水线（EventBridge refresh 14:00 GMT+8）是否健康、`/api/catalog/scores` 完备性。**降级态不消除或不能显式标注则首屏推荐不可信**——这是硬前置。

## P1 · 后端契约重塑（甲-q，前端可并行依赖）
- `Recommendation` 派生模型（region/generated_at GMT+8/best{headline,key_factors}/alternatives≤2/degraded）。
- `GET /api/recommend?region=` **公开**（首屏唯一请求）+ `GET /api/regions` 公开（区域列表聚合 catalog）。
- 报告动态化（清硬编码泄漏 §1.3）：`checklist` 按浪点/当周生成、footer 免责只留通用口径具体值取当次 report、`#extras` 引擎不能按浪点生成则砍。
- `FeatureFlags.member_lock_enabled=false`（env/config）· 诚实分层鉴权设计（一期公开、二期锁，中间件就位开关关）。
- 微信占位路由（`/api/auth/wechat/qr` 等返回 501 + 文档注释）· User 加 `wechat_openid`/`membership` 可空字段。
- `report.schema.json` 随 payload 变更同步 + 后端测试（新接口/降级/契约红线双侧钉死）。

## P2 · 前端脚手架 + build/ 服务（甲-1）
- Vite + Vue 3 + Vue Router（history）+ Pinia（spot/auth/region 三 store），建在 `web/frontend/`（不碰 `浪报MVP.html`）。
- FastAPI `StaticFiles` 挂 Vite build/ + SPA 回退（非 /api 路径 → index.html）；**Dockerfile 加 `npm run build`**、产物进镜像。**不改 terraform/CloudFront**。
- SVG 图表逻辑封装为 Vue 组件原样迁移（不引 ECharts）；hls.js/Leaflet 路由懒加载。

## P3 · `/spots` 全国目录页迁移（逻辑最独立，先打通全链路）
- 58 点列表 + 区域筛选 + 搜索 + 评分徽标 + Leaflet 地图 + 收藏置顶 + 「仅直播」checkbox。

## P4 · `/spot/:slug` 详情页迁移（体量最大）
- 日期条/本周必冲卡/逐日深度卡片（五维/SVG 图表/风质条/物理小课堂/行动方案）/小白·高手模式/昨日回看+自评。
- 新增：偏差校准展示（接 `/api/accuracy/bias`，§2.3）· 直播内嵌入口（有摄像头浪点 hls.js 弹层，替代直播墙）。
- 修正：checklist/免责按浪点动态（P1 产出）。

## P5 · `/` 首页新建（决策助手，消费 `/api/recommend`）
- 首访选地区引导（localStorage 记忆可换）· 一屏答案（✅ 某日·某点｜关键因子｜行动首句）· 亚军≤2 · 三渐进入口（为什么/昨天准吗/看全国）· **降级态显式**（本区 X/Y 点有分）。

## P6 · 会员锁占位 + 鉴权中间件（开关关）+ 微信占位
- 锁屏组件 + 「会员专享·即将上线」角标（一期不真拦截）· 中间件读 `member_lock_enabled`（false 全放行）· 微信占位路由前端入口。

## P7 · 删旧内容（清理，切换前）
- 删 `SAMPLE_*` 四数组/「其他」Tab/公告/活动墙/拼车/周边/关于商务 · 删 `#gate`/`demoAuth`/`surf2026`（代码+文档）· 删隐藏查询栏/墓碑注释/排水量残留。

## P8 · 新 E2E 全套重写（甲-b 护栏 · 切换的安全网）
- 按新路由重写 Playwright 用例 + 首页推荐/降级态/锁占位三组新用例 + 直播内嵌/偏差校准。**全绿是切 `/` 的前置门**。引擎 pytest 零改动。

## P9 · 切换切旧 + self-iterate 冻结（甲-y）
- 新 E2E 全绿后：`/` 切 Vue、`web/浪报MVP.html` 归档 `reference/`（不删，反面/历史）。
- **冻结 self-iterate 前端自动通道**：req_pipeline `gate_path_whitelist` 前端项暂关，只留后端/bug 类；记 ADR-9（冻结）+ ADR-10（稳定后目录级重定义蓝图）。

## P10 · 收尾
- 全量 pytest + **新 E2E 全绿** + `report.schema` 校验真实 payload + `node --check`/`bash -n` + 文档回写（product.md/README/structure.md）+ implementation-notes Progress 记录。

## G 门 · 真部署（生产写操作，人工授权）
- build v0.2.0（**major bump**：架构级变更）→ redeploy → **金丝雀跑新 E2E**（失败自动 rollback）→ git tag v0.2.0 → CHANGELOG 审计链。
