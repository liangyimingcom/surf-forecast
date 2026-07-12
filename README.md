# 🏄 浪报 Surf Forecast（Kiro v2）

面向会员的**动态冲浪浪报网站**：查询指定位置 → 逐日深度分析（评分/图表/物理解释）→ 用**昨日回看**校验预报准度建立信任。

采用 **[Kiro](https://kiro.dev) spec-driven development** 组织。本版(v2)以项目当前真实状态重建。

## v2 有什么新（相对 v1）

- **产品重心**：从"分析引擎"升级为"Web 会员产品 + 信任机制"。
- **离岸风(offshore)**：风向作为一等参数，图示用色块+箭头编码 offshore/cross/onshore。
- **昨日回看校验**：用真实历史回算 + 用户体感自评，校准系统性偏差（新增独立 spec）。
- **双周期口径** Tm/Tp、**GMT+8** 全程显式校准时间戳。
- **三个 spec**：analyzer / web / accuracy-feedback，外加 **deployment-and-ops**（生产部署 + 每日自动更新）与 **custom-spots**（浪点自定义与管理）。

## 快速导航

| 想… | 看 |
|-----|----|
| 产品定位与原则 | [.kiro/steering/product.md](.kiro/steering/product.md) |
| 领域知识(阈值/物理/离岸风/校验) | [.kiro/steering/domain-knowledge.md](.kiro/steering/domain-knowledge.md) |
| 架构/数据源/风向编码/时区 | [.kiro/steering/tech.md](.kiro/steering/tech.md) |
| 分析引擎 spec | [.kiro/specs/surf-forecast-analyzer/](.kiro/specs/surf-forecast-analyzer/) |
| 会员网站 spec | [.kiro/specs/surf-report-web/](.kiro/specs/surf-report-web/) |
| 昨日回看校验 spec | [.kiro/specs/forecast-accuracy-feedback/](.kiro/specs/forecast-accuracy-feedback/) |
| 生产部署+每日自动更新 spec | [.kiro/specs/deployment-and-ops/](.kiro/specs/deployment-and-ops/) |
| 浪点自定义与管理 spec | [.kiro/specs/custom-spots/](.kiro/specs/custom-spots/) |
| 会员视图实现 | [web/浪报MVP.html](web/浪报MVP.html) |
| UI 验收基准 | [reference/reports/ui-golden-sample-浪报MVP.html](reference/reports/ui-golden-sample-浪报MVP.html) |
| 后续开发指南 | [docs/kiro-development-guide.md](docs/kiro-development-guide.md) |
| 生产化 gap 分析+AWS架构+成本 | [docs/production-gap-analysis.md](docs/production-gap-analysis.md) |
| 浪点自定义 架构图+工作量排期 | [docs/custom-spots-visual-and-estimate.md](docs/custom-spots-visual-and-estimate.md) |
| AgentCore 重构设计 | [docs/agentcore-refactor-design.md](docs/agentcore-refactor-design.md) |
| v1→v2 迁移记录 | [docs/migration-notes-v1-to-v2.md](docs/migration-notes-v1-to-v2.md) |

## 当前状态

- ✅ Kiro 文档体系完整（4 steering + 5 spec三件套 + 2 hooks）
- ✅ `web/浪报MVP.html`：会员视图功能完整 MVP（双模式、三类 SVG 图表、离岸风质条、昨日回看、GMT+8）
- ✅ `src/surf_forecast/physics.py` 已实现并通过校验（含风向判定）
- ⬜ 引擎其余模块、Web 后端、校验持久化为脚手架，按各 spec 的 tasks 推进

## 数据源

Open-Meteo（同源 ECMWF WAM/IFS，免 key），含 `past_days` 历史回算。**不爬 Windy**。详见 [tech.md](.kiro/steering/tech.md)。

## 核心信条

> 冲浪日的上限由最差的参数决定，不由最好的参数决定。
> 先验证过去（昨日回看），再相信未来。

## 石老人复刻功能移植（2026-07 新增）

从「石老人实时浪报」复刻验收成果移植/新增到前端 `web/浪报MVP.html` 的 11 项功能。真实浪点数据 vs 示例 sample 明确区分；全程 GMT+8；附加式实现，引擎/后端零改动，pytest 118 零倒退。

| 功能 | 数据 | 状态 |
|------|------|------|
| ⭐ 浪点收藏（localStorage 置顶） | 真实 /api/spots | ✅ |
| 🔍 搜索 + 排序（名称/纬度/收藏优先） | 真实 | ✅ |
| 🗺️ Leaflet 浪点地图（真实坐标标记→切换） | 真实 | ✅ |
| 📢 公告详情（富文本弹层） | 示例 | ✅ |
| 💬 意见反馈（7类枚举+校验，演示不写库） | 示例 | ✅ |
| ℹ️ 关于·商务合作（脱敏） | 示例 | ✅ |
| 📰 活动墙（列表+类型筛选+详情） | 示例 | ✅ |
| 🚗 冲浪搭子/拼车（联系脱敏） | 示例 | ✅ |
| 🏄 排水量计算器（模块F，同款公式 70kg中级=31L） | 前端工具 | ✅ |
| 📍 周边推荐（模块D，分类商户） | 示例 | ✅ |
| 📹 在线直播占位（模块A，无真实流） | 示例占位 | ✅ |

- **测试**：pytest 118 passed；Playwright E2E 25/25（`web/e2e/new_features.mjs`）+ 0 JS 报错。
- **截图**：`docs/screenshots/*.png`（12 张）。
- **文档**：`docs/移植功能-01~03`（功能介绍 / 交互操作指南 / 教学教程）。
- **合规**：仅公开只读/前端示例，不做登录态/支付/发布，不引外部内容 API。

## 形态C整合：石老人×surf-forecast 统一后端（2026-07 新增）

按 [docs/石老人整合方案-formC.md](docs/石老人整合方案-formC.md)，把石老人「实时浪报」形态（全国 58+ 浪点 + 真实摄像头直播）整合进 surf-forecast 统一后端；**预报一律引擎自算**，直播前端 hls.js 直连上游。引擎内核零改动，pytest 118→126。

| 能力 | 实现 | 数据 |
|------|------|------|
| 全国浪点目录(58) | /api/catalog + 前端区域筛选/搜索/评分徽标 | 石老人导入坐标 + 引擎自算评分 |
| 真实直播(42) | /api/cams + hls.js 直连上游(不代理) | 石老人 live_src（研究用途·401门禁） |
| 详情融合 | 引擎评分/离岸风质/双周期/叙事 + 直播入口 | 引擎自算 |
| 昨日回看多浪点 | /api/report/history 引擎历史模式 | 引擎自算 |

- **导入**：`tools/import_shilaoren_spots.py`(快照) + `tools/load_registry.py`(灌注册表,float→Decimal) + `src/web/seed.py`。
- **测试**：pytest 126 (含 tests/test_formc.py 8项)；Playwright E2E 30/30 + 0 JS报错。生产验证 catalog=58/cams=42/取报含wdeg+GMT+8。
- **截图/文档**：docs/screenshots(17张) + docs/形态C-01~03。
- **合规**：石老人逆向部分仅研究用途；直播 401 门禁；社区示例；浪点朝向 facing 待校准。

## 会员视图 UI 交互布局优化（2026-07 新增）

对 `web/浪报MVP.html` 的一系列**纯前端**交互/布局优化，引擎内核与后端契约零改动，pytest 145 不倒退、Playwright E2E 47/47 + 0 JS 报错。

| 优化 | 说明 |
|------|------|
| 🗂️ 3 主标签页 | 实时浪报 / 浪报详情 / 其他，吸顶导航 |
| 🌊 目录/直播子视图 | 默认只显目录，避免 58+42 卡超长单页 |
| 📌 主导航吸顶 + ↑ 回顶 | 长列表随时切页/回顶 |
| 📍 hero 元信息动态 | 浪点名随浪点变、可点跳详情；删写死日出/水温/月相脏字段 |
| ↕️ 目录排序 | 推荐/综合评分↓/有直播优先/名称/地区 |
| 🌙 深色模式 | CSS 变量 body.dark + 跟随系统 + localStorage 持久化 |
| 💀 加载骨架屏 + spinner | 消除首屏/切浪点白屏 |
| 💾 tab/子视图记忆 | localStorage(sf_tab_v1/sf_liveview_v1) 刷新恢复 + 脏值回退 |
| 🈳 空态友好提示 | 目录/收藏搜索无结果引导文案 |
| 🧭 布局重定位 | 浪点名条移到主标签栏下(#spotbar) · 直播入口移到日期条下 |
| ⭐ 目录卡片直接收藏 | 全国目录卡片 ★ 一键收藏(复用 FAV_KEY，点星不加载) |
| 🗺️ 地图收藏着色 | 地图标记金=已收藏/蓝=未收藏 + 图例 |
| ♿ 可达性 | 主标签 ARIA tablist/tab+aria-selected · :focus-visible 焦点态 · 图标 aria-label |
| 📱 移动端 chips 横滑 | 区域/活动 chips 单行横向滚动(不换行堆叠) |
| 🔗 分享浪点深链 | 🔗 复制 #spot=lat,lon,name 链接，打开即定位该浪点并进详情 |

- **测试**：pytest **145**；Playwright E2E **56/56** + 0 JS 报错（`web/e2e/new_features.mjs`）。
- **截图/文档**：`docs/screenshots/`(28 张，含 26 浪报详情新布局 / 27 目录★收藏 / 02 地图彩色标记) + `docs/UI优化-01~03`（功能介绍/交互操作指南/教学教程，均含第二轮）。
- **合规**：纯前端附加式；不改引擎内核/后端契约（wdeg/GMT+8/float→Decimal）；受保护接口全 401；社区/直播示例与免责保留。
