# Roadmap — surf-forecast 移植石老人复刻功能

> 依赖顺序；每阶段后跑 pytest 子集 + Playwright E2E 回归，勿破坏现有 MVP/生产。用 codelens 摸底。

## R0 — 基线核验 + 摸底（先行）
- 跑 `pytest -q` 确认 118 基线；本地起 web，Playwright 打开 `web/浪报MVP.html` 确认现有功能正常。
- codelens explain_code/find_symbol 摸清 浪报MVP.html 前端结构（渲染入口/SPOT 列表/弹层模式）+ `/api/spots` 数据形状(lat/lon/facing)。建改动地图。

## R1 — 真实浪点增强（地图/收藏/搜索排序，纯前端）
- ⭐ 收藏（localStorage）+ 🔍 搜索（名称/坐标）+ 排序（评分/浪高/收藏优先），作用于 `/api/spots` 浪点。
- 🗺️ Leaflet+OSM(零key) 浪点地图：用浪点 lat/lon 标记，点击→加载该点浪报。

## R2 — 社区/工具（示例 sample，前端 + 轻后端）
- 公告详情、意见反馈、关于·商务合作：示例内容（静态或 `/api/samples/*`），标注"示例数据"。
- 活动墙（列表+类型筛选+详情）、冲浪搭子/拼车：示例 sample 数据，脱敏。
- 【补充模块】F 排水量计算器（石老人同款公式，纯前端工具）、D 周边推荐（示例商户：冲浪店/餐厅/酒店）、A 在线视频直播占位（示例占位卡，无真实 HLS 流）。

## R3 — 后端示例接口（可选，若走 API）
- 若前端从后端拉示例：加 `/api/samples/{news,carpool,notice}` 只读公开示例端点；否则前端内置示例常量。
- 新增任何 DynamoDB 写入必过 float→Decimal（本目标预计无写入）。

## R4 — 测试
- pytest 新增功能测试（后端示例接口/契约），基线从 118 增长。
- 扩 Playwright E2E 覆盖新前端路径；循环修复至全绿 + 0 JS 报错。

## R5 — headless Chrome 截图
- 各新功能界面截图 → `docs/screenshots/`。

## R6 — 文档
- 功能介绍 / 交互操作指南 / 教学教程（引用截图），存 `docs/`。

## R7 — 收尾
- 勾选 tasks.md；pytest + E2E 最终复核；README/功能矩阵更新；验收结论。

## R8 — 自动部署运行（AWS oversea1 / 153705321444 / ap-northeast-1）
- 前置：R4 E2E 全绿 + pytest 增长且全绿。
- `./deploy.sh test`（门禁）→ `./deploy.sh frontend`（t4g 云端构建 ARM64 镜像推 ECR + ECS 滚动部署，前端内置镜像）→ `./deploy.sh smoke`（health 200 + 未登录 401）→ CloudFront 端到端复核。
- 纯 web 层变更**不跑 terraform apply**；若需基建变更（新表/资源/SG）→ 停止发 blocker 等人工审批，禁 `-auto-approve`（红线）。

## 依赖
```
R0 → R1 ─┐
    R2 ──┼→ R4 → R5 → R6 → R7 → R8(部署上线)
    R3 ──┘   (R3 视实现方式，可并入 R2)
```
