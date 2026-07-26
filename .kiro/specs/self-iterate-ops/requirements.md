# Requirements — Self-Iterate Ops（用户建议自迭代闭环 · 人主导，v2 新增）

> EARS 格式。本 spec 把「用户建议 → 每日人工 triage → 按风险分流 → AI 出 draft PR → 人主导发布 → 审计追溯」固化为一等能力。
> **定位：工具/流程 spec，非产品功能 spec**。它服务于"如何演进本产品"，与 analyzer/web/accuracy-feedback/custom-spots（产品功能）泾渭分明，绝不侵蚀产品范围。
> 治理基准：[docs/自迭代闭环-治理模型-v5.md](../../../docs/自迭代闭环-治理模型-v5.md)（G1-G5 + 实施计划 L0-L5）。
> 复用：surf-report-web 的鉴权/前端、deployment-and-ops 的发布地基(版本tag/rollback/金丝雀/CHANGELOG)、已建工具 `tools/review_queue.py` / `tools/req_pipeline.py` / `tools/audit_trace.py` / `tools/crons/surf_triage.py`。

## 文档目的

产品需要一条"用户声音 → 受控演进"的闭环，但**绝不能让匿名输入直通生产**。v5 已定性为**人主导辅助工具**：AI 只出 draft PR，人按既定节奏审并合；无人值守被移除。本 spec 用 EARS 把该闭环的需求与红线钉死，供后续实现。当前已上线部分：匿名 `/api/feedback` 落库 + 认领码 track + 更新日志；`review_queue`（对话审阅台）+ 每日 triage cron。尚缺：按风险分流(direct/promote)的接口与硬规则兜底、需求→spec 升格流。

## 1. 建议提交与澄清（输入端）

**1.1** THE SYSTEM SHALL 允许终端用户在任意功能页匿名提交建议（`POST /api/feedback`），落库为结构化需求对象（kind/page/text/repro/expect + status=new + 认领码 + created_gmt8）。
**1.2** THE SYSTEM SHALL 对用户自由文本施加长度上限并仅存结构化字段，进任何下游前脱敏、不回显他人内容（反注入）。
**1.3** THE SYSTEM SHALL 提供预置模板澄清 UI（基于每 tab 的 page-schema，≤4 轮收敛、每轮更具体、可"跳过直接写"），产出结构化需求对象；**默认零 LLM**（云端智能澄清为范围外，见 §范围外）。
**1.4** THE SYSTEM SHALL 以认领码提供匿名进展查询（`GET /api/feedback/track`），仅回状态/时间/类别，不泄漏他人文本。

## 2. 每日 Triage 审阅（人工门 gate1）

**2.1** THE SYSTEM SHALL 每日（GMT+8 定时）拉取 `status=new` 队列、做垃圾（空/过短/非法 kind）与重复（归一化文本）预过滤、按优先级（bug>改进>新增>删除）排序，并把摘要投递给审阅人。
**2.2** WHEN 审阅人在对话中授权，THE SYSTEM SHALL 将建议置为 accepted（去 TTL，进处理队列）或 rejected（留 TTL 到期自动清）。
**2.3** THE SYSTEM SHALL 绝不自动 accept/reject——status 变更**必须由人逐条授权**（人即是门）。
**2.4** THE SYSTEM SHALL 对 `status ∈ {new, rejected}` 且超期者按 TTL 清理；**accepted/in_progress/promoted/shipped 绝不被 TTL 删**。

## 3. Accepted 按风险分流（gate 分流）

**3.1** WHEN 一条建议被 accepted，THE SYSTEM SHALL 由审阅人标注处理 lane：`direct`（琐碎纯前端小改）或 `promote`（触碰功能逻辑/引擎/契约）。
**3.2** WHERE lane=promote，THE SYSTEM SHALL 要求把该需求升格进某个产品 spec 的 requirements/tasks（记 spec_ref），走既定 spec-driven 排期，**不进 AI 直连产线**。
**3.3** WHERE lane=direct，THE SYSTEM SHALL 交由执行端（§4）出 draft PR。
**3.4** THE SYSTEM SHALL 对 lane 判定提供**确定性硬规则兜底**（见 4.3），人工标注误判时机器强制纠正——**不以 AI 判断"是否纯前端"为准**。

## 4. AI 出 Draft PR（执行端 gate2，人主导）

**4.1** WHEN 处理一条 lane=direct 的 accepted 需求，THE SYSTEM SHALL 经确定性安全门后产出 **draft PR**（pytest + 冻结 E2E 全绿 + schema 校验）；PR 附「验收标准 vs 实现」自评。
**4.2** THE SYSTEM SHALL 绝不自动合并 master、绝不自动部署生产——draft PR 停在等人 review+合并（去无人值守，覆盖历史 Q4/Q8）。
**4.3** THE SYSTEM SHALL 用确定性硬门裁定自动候选：改动路径 ⊆ 白名单 `{web/浪报MVP.html}` 且非删除 且 diff 不含契约关键字（wdeg/tp/tp2/tideEvents/times/windows/hs/wind/gust/_to_decimal/DATA CONTRACT/__SF_READY__）且无 secret/后门/新增出网；**任一不满足 → 强制退回 lane=promote**，不出直连 PR。
**4.4** THE SYSTEM SHALL 禁止自动路径触碰 `web/e2e/`（冻结基线，防 AI 自测自过）；需改测试的需求一律走 promote。
**4.5** THE SYSTEM SHALL 幂等去重、失败不无限重试。

## 5. 人主导发布与回滚（gate3 + 审计）

**5.1** WHEN 人合并 draft PR，THE SYSTEM SHALL 由人按既定节奏经发布地基发布（build+redeploy+金丝雀），**无自动部署**。
**5.2** THE SYSTEM SHALL 发布时打不可变版本 tag + 写 CHANGELOG（含需求ID）；金丝雀（生产真浏览器 E2E）失败可回滚。
**5.3** THE SYSTEM SHALL 维护审计链：需求ID ↔ pipeline 审计 ↔ PR/commit ↔ 版本tag ↔ CHANGELOG ↔ 部署时间，可用 `audit_trace` 贯通验证。
**5.4** WHERE 变更含 DynamoDB 数据/schema，THE SYSTEM SHALL 标记为**不可回滚**（仅前向修复）；纯前端变更可回滚（回上一版本镜像）。
**5.5** WHEN 建议上线，THE SYSTEM SHALL 置需求 status=shipped，并使认领码 track 可见该进展。

## 6. 数据正确性、安全与红线（约束性需求）

**6.1** THE SYSTEM SHALL 保持**单一自动驱动器**（每日 cron / pipeline / 任何 goal 不并发写同一文件）。
**6.2** THE SYSTEM SHALL 绝不向匿名用户暴露 CodeLens/源码/内部 spec；CodeLens 仅后端内部调用。
**6.3** THE SYSTEM SHALL 向 DynamoDB 写入前 float→Decimal（`_to_decimal`）；feedback 扩展字段（lane/spec_ref/decided_gmt8）读路径须容忍旧行缺字段（默认值）。
**6.4** THE SYSTEM SHALL 沿用既有红线：全程 GMT+8 / `/api/*` 全 401 / ALB SG 禁 0.0.0.0/0（仅 pl-58a04531）/ terraform 禁 `-auto-approve` / DATA CONTRACT 每日含 wdeg 数字数组。
**6.5** THE SYSTEM SHALL 为 pipeline 提供 kill-switch（STOP 文件）与每日处理上限，防跑飞。

## 范围外（明确不做）
- 无人值守自动合并/自动部署；匿名触发合并/部署。
- 云端 LLM 智能澄清接线（外部网关 alblitellm）——独立后续 spec/决策。
- LLM coder 自动生成实现代码（当前 edit 由人据需求手写）。
- feedback 绕过 spec 改核心逻辑；「是否纯前端」纯 AI 判定。
