# 迁移记录 — v1 → v2

> 记录为何重建、改了什么、关键决策。

## 1. 为什么需要 v2

v1（`surf-forecast-kiro/`）把产品定义为"分析引擎(CLI/库)"，只有 1 个 spec。但项目在 v1 之后大幅演进，重心转向 **Web 会员产品 + 信任机制**，v1 的 spec 已严重落后于实现。v2 以**项目当前真实状态**重新整理、重建 Kiro 规格。

## 2. v1 之后发生了什么（被 v2 纳入规格）

| 演进 | 说明 |
|------|------|
| 富交互会员视图 | 单 HTML：小白/高手双模式、日期条、Hero、逐日卡 |
| 三类 SVG 图表 | 浪高+双周期、风况+潮位、7 日生命周期（全自绘，零依赖） |
| **离岸风编码** | 风向判 offshore/cross/onshore，色块+箭头+风质条 |
| **昨日回看校验** | 历史回算 + 四档自评 + 偏差校准——全新信任机制 |
| 双周期口径 | Tm 实线 / Tp 虚线 |
| GMT+8 | 显式校准时间戳；今天/昨天按北京时间日界 |
| 会员门禁 + 位置查询 | 占位，待后端 |

## 3. v1 → v2 结构映射

| v1 | v2 |
|----|----|
| 1 spec: surf-forecast-analyzer | 3 spec: analyzer（更新）+ web（更新）+ **accuracy-feedback（新）** |
| steering ×4 | steering ×4（domain 增离岸风/生命周期/校验；tech 增风向编码/GMT+8/历史模式） |
| web/浪报MVP.html（早期版） | web/浪报MVP.html（当前富交互版）+ reference UI 黄金样本快照 |
| 1 hook | 2 hook（validate 增离岸/历史互斥校验；新增 refresh-data） |

## 4. 关键决策（ADR 汇总）

- **拆出第三个 spec（accuracy-feedback）**：昨日回看是独立、可复用、有自己数据流与红线的能力，值得单独成 spec 而非塞进 web。
- **离岸风进评分+JSON+图示**（analyzer ADR-6）：风向比风速大小更影响浪面质量，必须一等对待；JSON 输出 `wdeg` 字段，前端已消费。
- **历史回算复用同一管线**（analyzer ADR-7 / feedback ADR-F1）：仅 `past_days` 不同，口径一致是校验有效的前提。
- **校准只提示不篡改原评分**（feedback ADR-F2）：数据诚实优先于"显得更准"。
- **昨日回看置于预报之后**（feedback ADR-F3）：信任工具不抢首屏黄金位。

## 5. v2 期间修正的事实问题（沉淀为红线）

| 问题 | 修正 |
|------|------|
| "昨天"星期算错（周四 vs 实际周五） | 红线：今天/昨天按 GMT+8 日界算 |
| 同一天既在预报又在历史 | 红线：历史区与预报区日期互斥 |
| 时区未显式 | 红线：全程 GMT+8 + 校准时间戳 |
| 风向缺失 | 离岸风进评分/图示（domain 第三节） |

（v1 既有教训——星期错一天、潮型↔月相、水温、虚构先行波——继续保留在 domain 第九节。）

## 6. 当前完成度

- ✅ v2 全套 steering、3 spec三件套、2 hook、README、本迁移记录、开发指南。
- ✅ 资产迁移：当前 HTML、引擎脚手架、配置、reference 报告、UI 黄金样本快照。
- ✅ physics.py 实现并通过校验。
- ⬜ 引擎其余模块/Web 后端/校验持久化按各 spec tasks 推进。

## 7. 下一步

见 [kiro-development-guide.md](./kiro-development-guide.md)：先跑通 analyzer 的 JSON 输出（含 wdeg + 历史模式），再 web 动态化，再 feedback 持久化。
