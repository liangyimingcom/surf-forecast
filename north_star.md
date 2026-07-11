# North Star — surf-forecast 移植石老人复刻功能（社区/工具/地图/收藏）+ E2E + 截图教学

## 业务目标
用 skill `surf-forecast-codelens-dev` 的方法论，把「石老人实时浪报复刻版」验收成果的功能**移植/新增到 surf-forecast 项目**（前端 `web/浪报MVP.html` + 必要的 FastAPI 后端），随后 **Playwright E2E 全绿并修复问题**，最后 **headless Chrome 抓新界面截图** + 产出**功能介绍 / 交互操作指南 / 教学文档**。

要新增的功能：
- **R1 补齐（免登录/示例）**：公告详情、意见反馈、关于·商务合作。
- **R1+R2 社区只读（示例 sample）**：活动墙（列表+类型筛选+详情）、冲浪搭子/拼车。
- **新增增强（真实浪点数据）**：🗺️ Leaflet 浪点地图、⭐ 浪点收藏、🔍 搜索/排序。
- **石老人补充模块（示例移植）**：F 排水量计算器（同款公式，纯前端工具）、D 周边推荐（示例商户）、A 在线视频直播占位（示例占位卡，无真实流）。

## 数据策略（重要）
- **地图/收藏/搜索/排序**：作用于 surf-forecast **真实浪点**（`/api/spots` + 引擎坐标 lat/lon/facing），是真数据。
- **活动墙/拼车/公告/关于/商务合作**：surf-forecast **无对应上游数据源** → 全部用**示例 sample 内容**（脱敏、静态或轻量 `/api/samples/*` 后端），明确标注"示例数据"。**不引入任何外部第三方 API**。
- **字段参考**：`docs/ISURF-功能规格参考.md`（ISURF 小程序功能规格）——构建示例 sample 时按此字段契约结构，保证忠实（值脱敏为示例）。

## 方法论（surf-forecast × CodeLens）
每个功能：① codelens explain_code/find_symbol 摸清前端(浪报MVP.html)与后端(app/spots/deps)结构 → ② get_impact 算爆炸半径 → ③ 守红线(find_route 全 401、search wdeg) → ④ 改 spec → ⑤ 实现 → ⑥ pytest 子集 + Playwright E2E → ⑦ 截图 → ⑧ 文档。
CodeLens MCP: https://d1t9q5qxrql3xj.cloudfront.net/mcp/ package liangyimingcom/surf-forecast。

## 成功判据（DoD）
1. 上述 8 个点名功能 + A/D/F 三补充模块（共 11 项）在 `web/浪报MVP.html` 可用；社区/公告/关于/周边/直播用示例数据并标注。
2. 地图/收藏/搜索/排序作用于真实浪点，收藏 localStorage 持久化。
3. 新增的后端接口（若有，如 `/api/samples/news`）全 401 保护或明确公开只读示例；不碰引擎内核。
4. **pytest 从 118 基线增长**（新增功能测试全绿）；新增前端逻辑 `node --check` 通过。
5. **Playwright E2E 全绿**：真实浪点渲染 + 新功能路径 + 0 控制台 JS 报错（favicon/资源404除外）。
6. **headless Chrome 截图**：各新功能界面截图存 `web/docs/` 或 `docs/screenshots/`。
7. 3 份文档：功能介绍 / 交互操作指南 / 教学教程（引用截图）。
8. **自动部署上线**：R4 全绿后用 `./deploy.sh frontend` 重建镜像滚动部署 + `./deploy.sh smoke` 冒烟 + CloudFront 端到端复核（新界面线上可见、真实数据含 wdeg+GMT+8）。纯 web 层变更不跑 terraform apply；若需基建变更须停止等人工审批。
   - AWS 鉴权：profile `oversea1`，账号 `153705321444`，region `ap-northeast-1`。

## 红线（surf-forecast，务必遵守）
- 全程 **GMT+8**；DATA CONTRACT 引擎 JSON 每日含 **wdeg**，图表字段为数字。
- DynamoDB 写入必过 **float→Decimal**（`src/web/db.py::_to_decimal`）；**不改引擎内核**（physics/scoring/validate）。
- `/api/spots` 及受保护接口全 **401**；ALB SG 永不含 0.0.0.0/0；`terraform apply` 禁 -auto-approve。
- slug 不可变作缓存键；新功能主要在 web 层（前端 + 轻后端），**附加式不破坏现有 MVP 与生产**。
- 不引入外部第三方 API；社区内容为本地示例 sample。

## 约束
- 本地开发；`.venv` python3.12；pytest 基线 118。前端 = 单 HTML `web/浪报MVP.html`。
- 本地起后端：`SF_FRONTEND=web/浪报MVP.html PYTHONPATH=src uvicorn web.app:app --reload`（内存 store）。
- 停止循环：创建 `/Users/yiming/Downloads/all_the_meshclaw/surf-forecast/surf-forecast-kiro-v2/STOP_LOOP`。
