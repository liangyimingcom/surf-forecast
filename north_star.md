# North Star — 甲·忠实整体重建（Vite+Vue3 决策助手）

> 依据 `docs/Fable5迭代建议.md`（八项已确认决策）+ `docs/implementation-notes.md`（保守自治协议）。
> 用户在本 session 显式选定 **方向甲·忠实整体重建**，并逐题拍板四项架构决策（见下）。
> ⚠️ 这是本项目**爆炸半径最大**的一次改动——同时动前端框架 + 后端契约 + E2E + 契约门四线。已如实警示裸奔风险，用户明确承担。

## 一句话目标

把现有 2000 行单 HTML（`web/浪报MVP.html`）忠实重建为 **Vite + Vue 3 决策助手**：首屏一屏答案（`/`）+ 浪点详情（`/spot/:slug`）+ 全国目录（`/spots`），删除示例模块、清硬编码泄漏、诚实分层鉴权、真会员制预埋（一期占位不拦截），并同步重塑后端契约与新接口。

## 四项已锁架构决策（不可在 loop 内擅自推翻）

| # | 决策 | 结论 |
|---|------|------|
| **甲-1** | 前端 build/ 服务方式 | **后端 `StaticFiles` 挂 Vite build/ + SPA 回退，`/api` 照旧，单镜像** → **不动 terraform/CloudFront**（deployment-and-ops 基本不改） |
| **甲-b** | 迁移策略 | **Big-bang 直接切换 + 同一 goal 内重写 E2E**；但**新 E2E 必须先全绿、才切 `/` 到 Vue**，把裸奔窗口压到最小 |
| **甲-y** | self-iterate 白名单 | 重建高动荡期**冻结 self-iterate 前端自动通道**（只留后端/bug 类）；Vue 站稳后再按目录级（甲-x）重定义解冻。记 ADR |
| **甲-q** | 前后端契约 | **前端重建 + 后端契约同步重塑一步到位**：新增 `/api/recommend`·`/api/regions`、接 `/api/accuracy/bias`、报告动态 checklist、清硬编码、`report.schema.json` 随之更新 |

## Fable5 八项产品决策（承载内容）

1. 决策助手（首屏一屏答案）· 2. 按地区自动圈定推荐 · 3. 删「其他」5 模块 · 4. 直播降为详情页内嵌 · 5. Vite+Vue3 重建 · 6. 真会员制（微信扫码二期，一期预留接口）· 7. 首屏公开·深度锁会员 · 8. 一期全公开·锁仅占位（`member_lock_enabled=false`）。

## 完成定义（DoD）

- Vite+Vue3 三路由页（`/`·`/spot/:slug`·`/spots`）功能对齐并**取代**单 HTML；旧文件归档 `reference/`。
- 后端：`/api/recommend`·`/api/regions` 上线、`/api/accuracy/bias` 前端接线、报告 checklist/免责动态化、`FeatureFlags.member_lock_enabled` 开关、诚实分层鉴权（删 `demoAuth`/`#gate`/`surf2026`）、微信占位路由（501）。
- 契约：`web/report.schema.json` 随 payload 变更同步、契约测试全绿。
- **新 E2E 全套重写并全绿**（新路由 + 首页推荐/降级/锁占位三组）后才切 `/`；引擎 pytest 零改动。
- SVG 图表逻辑封装为 Vue 组件**原样迁移**（不引 ECharts，保持零重依赖视觉）。
- 文档回写：product.md 范围边界、README 状态、structure.md（前端结构 + self-iterate 甲-y 冻结 ADR）。
- 真部署留 **G 门**（生产写操作，人工授权）。

## 红线（继承 + 本 goal 专属）

- **数据诚实**：首屏推荐强依赖每日评分缓存——缓存不全**必须显式降级**（只推有分的点 + 标注），绝不拿旧分/样例分冒充（首屏=产品信誉）。清硬编码泄漏是**正确性 bug**（切三亚不能显"青岛潮汐表"）。
- **降级态根因**：Fable5 §4.5 指出线上此刻在降级横幅下运行；R0 必须先排查评分缓存流水线为何降级，**不在坏缓存上建首屏**。
- **裸奔最小化**：新 E2E 绿之前不切 `/`（甲-b 的护栏）。
- **单一驱动器**：仅 dashboard auto-nudge 驱动，**绝不调 task_run**。
- **DATA CONTRACT**：wdeg 数组 + 数字图表数组 + GMT+8 + 预报/历史日期互斥；float→Decimal；受保护接口鉴权只在后端。
- **CodeLens 先摸底**（SOP）· ALB SG 永不含 0.0.0.0/0 · terraform 禁 -auto-approve。
- **self-iterate G1**：LLM coder 一律人工审，无自动合并/部署。
