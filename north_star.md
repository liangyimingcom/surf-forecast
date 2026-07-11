# North Star — surf-forecast 会员视图 UI 交互布局持续优化

## 业务目标
用 skill `surf-forecast-codelens-dev` 方法论，**持续优化 `web/浪报MVP.html` 的 UI 交互与布局**，并**迭代因 UI 改进而新增/变更/优化的配套功能**；然后确认 **E2E 全绿**后，用 **headless Chrome 抓新界面截图**，完成**功能介绍 / 交互操作指南 / 教学教程**三份中文文档。

## 已有基础（本轮起点，勿重复）
前端已含：3 主标签页(实时浪报/浪报详情/其他) + hero 元信息随浪点动态(#metaSpot 可点跳详情) + 实时浪报「目录/直播」子视图切换 + 主导航吸顶 + 回到顶部按钮 + 收藏/搜索/排序/Leaflet 地图 + 目录 58 浪点(区域 chips+评分徽标) + hls.js 直播 + 公告/反馈/关于/活动墙/拼车(示例) + 排水量已移除。后端：get_report 引擎自算 + /api/catalog + /api/cams + /api/spots(全 401)。pytest 145、E2E 29/29 为当前基线。

## 优化方向（每轮挑单个最高杠杆，不必全做）
- **视觉层级/信息密度**：目录卡片布局(网格/紧凑)、评分徽标排序(按分排目录)、空态友好提示(无收藏/无搜索结果)。
- **加载体验**：loadCatalog/loadLive/loadCams 加载态骨架屏或 spinner，避免白屏/空列表。
- **导航/记忆**：记住上次 tab / 子视图(localStorage)；目录搜索与收藏搜索的一致性。
- **主题**：深色模式切换(尊重 prefers-color-scheme + 手动切换持久化)。
- **可达性**：键盘可操作、aria-label、焦点态、点击热区。
- **联动**：目录卡片直接收藏(★)；地图标记按评分/离岸风着色。
- **移动端**：触控热区、横向滚动 chips、弹层滚动锁。
> 每轮 1–2 项，附带迭代其配套逻辑与契约。避免过度设计；不改后端引擎内核。

## 成功判据（DoD）
1. 每轮 UI 改动为**纯前端附加/重构式**，不改后端引擎内核(physics/scoring/validate)，pytest **145 基线勿倒退**。
2. 新增/变更交互都有 Playwright E2E 断言覆盖（`web/e2e/new_features.mjs`），**全绿 + 0 JS 报错**（排除资源404/直播流）。
3. 数据诚实：不显示与浪点无关的写死值（延续 hero 修复原则）；示例数据显著标注。
4. headless Chrome 截图新界面 → `docs/screenshots/*.png`。
5. 三份中文文档更新/新增：功能介绍 / 交互操作指南 / 教学教程（引用截图）。
6. （可选，高风险）部署到生产：**不在 loop 内自动推生产**，到部署步骤停下发 blocker 等人工确认。

## 红线（务必遵守）
- 全程 GMT+8；DATA CONTRACT 每日含 wdeg，图表字段为数字；预报区与历史区日期互斥。
- 不改引擎内核；DynamoDB 写入必过 float→Decimal；受保护接口全 401。
- 附加式不破坏现有 MVP/生产；slug 不可变作缓存键。
- ALB SG 永不含 0.0.0.0/0；`terraform apply` 禁 -auto-approve；纯 web 变更不跑 apply。
- 合规：社区/直播示例与免责保留；不复刻登录态/支付/写入。

## 方法论（surf-forecast × CodeLens）
每轮：① 改前先 **grep 实际 HTML** 确认函数/元素是否已存在(防并发/重复) → ② codelens 摸底/算爆炸半径/守红线(find_route/search_spec_artifacts) → ③ 实现 → ④ node --check + pytest 子集 + Playwright E2E → ⑤ 勾 tasks(必须与文件一致，禁记未落地) → ⑥ 到截图/文档/部署阶段按 roadmap。
CodeLens MCP: https://d1t9q5qxrql3xj.cloudfront.net/mcp/ package liangyimingcom/surf-forecast。

## 纪律（防上次并发写冲突复发）
**单一驱动器**（本 loop 唯一）；勾选与实际文件严格一致；禁止记录未落地完成项。

## AWS / 环境
profile `oversea1`，账号 `153705321444`，region `ap-northeast-1`；CloudFront `d2hmhl7n8yga53`。
本地起后端：`SF_SEED_SPOTS=reference/data/shilaoren_spots.json SF_STORE=memory SF_FRONTEND=$PWD/web/浪报MVP.html python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8848`。
跑 E2E：`node web/e2e/new_features.mjs http://127.0.0.1:8848`。
停止循环：创建 `/Users/yiming/Downloads/all_the_meshclaw/surf-forecast/surf-forecast-kiro-v2/STOP_LOOP`。
