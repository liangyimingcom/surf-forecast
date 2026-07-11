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
