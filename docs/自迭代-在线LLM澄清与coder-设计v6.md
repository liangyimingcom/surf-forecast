# 自迭代 · 在线 LLM 澄清 + LLM coder · 设计与实施计划 (v6)

> 本文汇总"需求→功能实现"里两块 AI 环节（在线澄清 + coder）的决策与实施计划。
> 决策正本见 `.kiro/specs/self-iterate-ops/design.md` ADR-5~8；治理红线见 `docs/自迭代闭环-治理模型-v5.md`。
> 实施排序原则（用户约定）：**最可能调整的决策 → 数据模型 → 新接口 → 用户可见 → 内部逻辑 → 机械/测试垫底**（红线逻辑测试随层）。

## 一、ADR 汇总（已定案 2026-07-26）
| ADR | 决策 |
|-----|------|
| ADR-5 | LLM 进**在线匿名澄清**(ECS 调 alblitellm/sonnet-4-6)。**连通性已实测**(生产私有子网+NAT → PROBE_REACHABLE http 401)，可达 |
| ADR-6 | **每步自动调**(澄清每轮选项由 LLM 生成) |
| ADR-7 | **仅应用层限流**：per-IP + 全局日预算硬闸 + 同页同类选项缓存 + 超限/不通/报错降级预置模板 + LLM 输出 schema 校验 + key 进 Secrets Manager + 反注入(系统/数据分隔)。**不引 WAF** |
| ADR-8 | LLM coder **可写实现但一律人工审 draft PR**(守 v5 G1,无自动合并/部署)；锚点 patch(禁全文重写)、禁碰 web/e2e/(冻结)、过硬门+secret/后门扫描、需求当数据、删除功能永不自动 |

## 二、前置状态
- ✅ ECS→网关连通性（实测可达）。
- ⬜ 网关 key 进 Secrets Manager + ECS 任务角色 valueFrom（实施时）。
- 既有可复用：feedback 表(+lane/spec_ref)、模板澄清 UI(降级兜底)、req_pipeline(6 门)、audit_trace、每日 cron。

## 三、实施计划（决策优先排序）

### L0 决策（已定案，见 ADR-5~8）—— 无待拍板项

### L1 数据模型 / 契约
- 限流/预算状态：`{prefix}-llm_usage`(或复用现表) 记 per-IP 计数(滑动窗) + 全局日累计(预算硬闸)；写 float→Decimal。
- 选项缓存键：`hash(page-schema版本 + 步骤 + 已选路径)` → 缓存 LLM 选项集（内存 LRU 或 DynamoDB 短 TTL）。
- LLM 输出**结构化需求对象 schema**（复用 feedback 字段 + 澄清中间态），校验器拦畸形输出。

### L2 新接口
- 后端 `POST /api/clarify`（匿名+限流）：入参 {page, 步骤, 已选/自由文本} → 出参 {下一步选项菜单 | 收敛为结构化需求}。内部：查选项缓存→未命中调 alblitellm(key from Secrets)→schema 校验→写缓存；预算/限流/报错→降级模板。
- coder：`req_pipeline` 加 `--llm-coder`（读 accepted 需求 → 调网关生成锚点 patch → 走既有硬门 → 出 draft PR，**永远人工审**）。

### L3 用户可见
- 前端澄清 UI：每步调 `/api/clarify`（loading 态；≤4 轮收敛；"跳过写自由文本"逃生）；超限/降级时无缝切预置模板、提示不报错。

### L4 内部逻辑（护栏）
- per-IP 限流 + 全局日预算硬闸（超限 → 降级模板，不再调网关）。
- 反注入：用户文本作 data 段，系统指令分隔；不回显源码/内部。
- coder：锚点 patch 应用（禁全文重写）+ 禁碰 web/e2e/ + diff secret/后门/新出网扫描 + 需求当数据。

### L5 机械 / 测试（垫底；红线逻辑随层）
- 单测（边界双侧+mutation）：限流阈值、日预算硬闸、选项缓存命中/失效、LLM 输出 schema 校验拒畸形、降级触发。
- 集成：/api/clarify 降级路径（模拟网关不通/超限）；coder patch 应用+硬门+禁碰 e2e。
- 部署（G 门）：Secrets 注入 + task 角色权限 + build+redeploy+canary。

## 四、红线（沿用）
人主导(AI 只出 draft PR,无自动合并/部署) · 匿名 LLM 仅应用层护栏+日预算硬闸+降级 · 反注入 · CodeLens/源码不外露 · 缓存不碰可见性 · GMT+8/DATA CONTRACT/float→Decimal/全401/SG禁0.0.0.0/0/terraform禁-auto-approve · 单一驱动器 · 真部署 G 门。

## 五、范围外
无人值守自动合并/部署(含 LLM-authored) · WAF/CloudFront 基建 · LLM 略过人眼上线 · 每步自动之外的成本无界调用。
