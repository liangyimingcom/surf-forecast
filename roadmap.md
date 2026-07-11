# Roadmap — 石老人 × surf-forecast 形态C整合

> 依赖顺序；每阶段跑 pytest 子集 + Playwright E2E 回归，勿破坏现有 MVP/生产。每阶段先 codelens 摸底。
> 方案详版：docs/石老人整合方案-formC.md

## P0 — 摸底 + 基线（先行）
- pytest 确认 118 基线；codelens 摸清 spot_registry / get_report / db._to_decimal / /api/spots 结构与影响面；守红线（find_route 全401、search wdeg）。建改动地图。

## P1 — 浪点导入（58+）
- 写 tools/import 脚本：从石老人上游 getCamera + getNewForecast 拉 name/city/坐标/live_src（一次性，可离线快照）；补 facing（默认估算+标"待校准"）。
- 写入注册表（DynamoDB spot_registry，float→Decimal）；本地内存 store 提供等价 fixture 供测试。

## P2 — 直播 /api/cams + 前端弹层
- 后端 `/api/cams`（只读，鉴权策略明确）返回 slug→live_src；前端 hls.js 直播弹层，视频直连上游。

## P3 — 列表升级（多浪点 + 地区筛选 + 评分）
- 前端浪点列表扩为 58+；地区筛选 Tab；每点综合评分（引擎首日值，用缓存避免 58×实时）；复用收藏/搜索/地图（地图标记按评分/离岸风着色）。

## P4 — 详情融合
- 浪点详情：引擎评分/离岸风质/双周期 Tm-Tp/物理叙事 + 直播入口 + 周边推荐。

## P5 — 昨日回看接入多浪点
- 历史回看校验对任一浪点可用（引擎历史模式）。

## P6 — 测试（部署前）
- pytest 新增（注册表导入/cams 契约），基线从 118 增长；Playwright E2E 覆盖新路径，循环至全绿 + 0 JS 报错。

## P7 — 自动部署 + 部署后 E2E + 截图 + 文档
- `AWS_PROFILE=oversea1 ./deploy.sh test→frontend→smoke` + CloudFront 端到端复核；**部署后再跑一次线上 E2E**。
- headless Chrome 截图 → docs/screenshots/；3 份文档（功能介绍/交互操作指南/教学教程）。
- 需基建变更（新表/资源/SG）→ 停下发 blocker 等人工审批，禁 -auto-approve。

## 依赖
```
P0 → P1 → P2 → P3 → P4 → P5 → P6(部署前E2E) → P7(部署+部署后E2E+截图+文档)
```
