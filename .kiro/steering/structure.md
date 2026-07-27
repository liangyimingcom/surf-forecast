---
inclusion: always
---

# Structure Steering — 项目结构与约定（v2）

## 目录结构

```
surf-forecast-kiro-v2/
├── .kiro/
│   ├── steering/                 # 始终加载的引导文档
│   │   ├── product.md            # 产品定位（Web会员+校验机制）
│   │   ├── tech.md               # 架构、数据源、风向编码、时区
│   │   ├── structure.md          # 本文件
│   │   └── domain-knowledge.md   # 冲浪/波浪物理领域知识（核心资产）
│   ├── specs/
│   │   ├── surf-forecast-analyzer/    # 分析引擎（后端模块）
│   │   ├── surf-report-web/           # 会员网站（鉴权/查询/视图）
│   │   ├── forecast-accuracy-feedback/# 昨日回看校验机制（v2 新增）
│   │   ├── deployment-and-ops/        # 生产部署+每日自动更新（v2 新增）
│   │   ├── custom-spots/              # 浪点/位置自定义与管理（v2 新增）
│   │   └── self-iterate-ops/          # 用户建议自迭代闭环（工具/流程 spec，v2 新增）
│   └── hooks/
├── web/
│   └── 浪报MVP.html              # 单文件 MVP（甲重建后作兜底/归档，见 web/frontend）
│   └── frontend/                 # Vite+Vue3 决策助手重建（甲）：pages(/·/spots·/spot)+components(ChartBox/LockBadge)+charts.js+stores(region/auth/spot)
├── prompts/                      # 原始提示词归档
├── reference/
│   ├── reports/
│   │   ├── ui-golden-sample-浪报MVP.html  # UI 黄金样本（验收基准快照）
│   │   ├── v2-report-golden-sample.md     # 分析叙事质量基准
│   │   ├── v1-report-baseline.md           # 反面教材（含事实错误）
│   │   └── fact-check-comparison.md        # 事实核查（validate 来源）
│   └── data/
├── src/surf_forecast/            # 引擎源码（physics.py 已实现，余脚手架）
├── config/thresholds.yaml        # 评分阈值+权重+spot_facing_deg
├── templates/                    # 报告模板（CLI 用）
├── tests/
├── docs/
│   ├── kiro-development-guide.md # 后续开发思路与建议
│   ├── migration-notes-v1-to-v2.md
│   └── production-gap-analysis.md # 生产化 gap 分析 + AWS 架构 + 成本估算（v2 新增）
└── README.md
```

## 六个 Spec 的边界（5 产品功能 + 1 工具/流程）

| Spec | 负责 | 不负责 |
|------|------|--------|
| **surf-forecast-analyzer** | 取数→评分→物理→校验→渲染 JSON/MD | 鉴权、HTTP、UI |
| **surf-report-web** | 鉴权、会员、位置查询、缓存、会员视图前端 | 分析逻辑（调引擎） |
| **forecast-accuracy-feedback** | 昨日历史回算、预报vs体感自评、偏差校准 | 实时预报（用引擎历史模式） |
| **deployment-and-ops** | IaC、计算托管、存储、**每日定时刷新**、CDN、可观测性、安全、CI/CD | 业务逻辑（部署上述三者） |
| **custom-spots** | 浪点注册表、自定义经纬度、多点管理(CRUD)、动态刷新编排(去重/即时预算/冷点回收) | 评分/渲染(调引擎)、鉴权(用 web 会话)、调度基建(用 deployment) |
| **self-iterate-ops** 🔧 | 用户建议落库/澄清/每日triage审阅/按风险分流/AI出draft PR/人主导发布/审计链（**工具·流程 spec，非产品功能**） | 产品功能实现(升格进对应产品spec)、无人值守自动合并/部署(明确不做) |

依赖：web 与 feedback 都依赖 analyzer；feedback 在 web 视图中呈现；deployment-and-ops 部署前述者，并提供「每日自动更新」调度链路（与在线请求读写解耦）。**custom-spots** 依赖 analyzer(引擎)、web(会话/视图)、deployment(缓存/调度)——把 deployment 的硬编码 `DEFAULT_SPOTS` 升级为 DynamoDB 动态浪点注册表。**self-iterate-ops**（工具/流程）复用 web 鉴权、deployment 发布地基与既有工具(review_queue/req_pipeline/audit_trace/surf_triage cron)；它演进"产品如何迭代"，与 5 个产品功能 spec 解耦，绝不侵蚀产品范围。治理见 [docs/自迭代闭环-治理模型-v5.md](../../docs/自迭代闭环-治理模型-v5.md)。

## 命名约定

- 模块小写下划线；pydantic 模型大驼峰（`ForecastPoint/DailyAnalysis/HistoryReview/AccuracyVote`）。
- 评分函数 `score_<参数>`；物理函数量名（`wavelength/group_velocity`）；风向 `wind_kind/wind_arrow`。
- 前端数据对象：`DAYS`（预报）、`HISTORY`（昨日）、`REPORT`（API 返回）。
- 报告文件 `<spot>-<days>日冲浪浪报-<YYYYMMDD>.md`。

## 数据流（单向）

```
fetch(+past_days) → models(校验) → analyze(评分+风向+短板) → validate(事实自检)
  → DailyAnalysis[]/HistoryReview → render(JSON) → 前端 DAYS/HISTORY → SVG 图表+叙事
                                                  ↘ 用户自评 → AccuracyVote → 偏差校准
```

## 关键约束

- **reference/ 只读**：质量基准与反面教材，不改不 import。
- **叙事不进计算层**；**阈值不进代码**；**鉴权不进前端**。
- **预报区 vs 历史区日期互斥**：今天起为预报，昨天为历史，不重叠（v2 教训）。
- 每个改动遵循对应 spec；需求变更先改 requirements。
