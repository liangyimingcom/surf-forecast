# Design — Self-Iterate Ops（用户建议自迭代闭环 · 人主导，v2 新增）

> 对应 requirements.md。治理基准 [docs/自迭代闭环-治理模型-v5.md](../../../docs/自迭代闭环-治理模型-v5.md)（G1-G5 + 实施计划 L0-L5）。
> **纯设计文档**。ADR（§7）中的 L0 决策附推荐值，**待评审拍板**，非既定。

## 1. 架构定位

**工具/流程 spec**，服务"如何演进本产品"，与产品功能 5-spec 解耦。核心原则（v5 G1-G5）：
- G1 pipeline = 人主导辅助工具（AI 只出 draft PR；**去无人值守**，覆盖历史 Q4/Q8）。
- G2 建议入口常开；G3 每日 triage 仪式；G4 accepted 按风险分流；G5 直连 vs 升格 = 人工标注 + 硬规则兜底。

```
用户(匿名) ──POST /api/feedback──▶ DynamoDB feedback(status=new)
                                        │
        每日 cron(surf_triage) ──只读+预过滤+摘要──▶ 审阅人(对话 gate1)
                                        │ accept/reject(人授权)
                          accepted ─────┴──── 标 lane
                     ┌── direct ──▶ req_pipeline 硬门(gate2) ──▶ draft PR ──▶ 人审合(gate3) ──▶ 发布+金丝雀 ──▶ shipped
                     └── promote ─▶ 升格进产品 spec requirements/tasks ──▶ 既定排期
                                        │
                     审计链: 需求ID ↔ pipeline ↔ PR/commit ↔ 版本tag ↔ CHANGELOG ↔ 部署时间 (audit_trace)
```

边界：本 spec 拥有「反馈落库/澄清/审阅/分流/执行门/审计」；复用 surf-report-web 鉴权、deployment-and-ops 发布地基、既有工具（review_queue/req_pipeline/audit_trace/surf_triage）。**不拥有**产品功能实现。

## 2. 数据模型

### 2.1 feedback 需求对象（DynamoDB `{prefix}-feedback`，表已上线）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | S(PK) | uuid12 或 seed-* |
| status | S | new→triaged→accepted→in_progress→(promoted / shipped) / rejected / expired |
| kind | S | bug/improve/new_feature/remove |
| page/text/repro/expect/accept | S | 结构化需求正文 + 验收 |
| claim_code / created_gmt8 | S | 匿名认领 / GMT+8 |
| expiresAt | N | TTL：仅 new/rejected 设；采纳去 TTL |
| **lane**(新) | S | direct / promote（G4/G5；旧行缺→默认 unset，读容错） |
| **spec_ref**(新) | S | promote 时指向的 spec/task |
| **decided_gmt8**(新) | S | 审阅决策时间 |

红线：写入 float→Decimal(`_to_decimal`)；新增字段**读路径容忍旧行缺失**（默认值），避免 KeyError；含数据变更**不可回滚**（前向修复）。

### 2.2 状态机
`new` ──accept──▶ `accepted` ──lane=direct──▶ `in_progress` ──PR合并+发布──▶ `shipped`
`accepted` ──lane=promote──▶ `promoted`（进产品 spec，脱离直连产线，永不 TTL）
`new` ──reject──▶ `rejected`(留TTL) ；`new/rejected` 超期──▶ `expired`(TTL清)

## 3. 接口变更（均新增，向后兼容）

- `tools/review_queue.py`：新增 `mark <id> --lane direct` 与 `promote <id> --spec <name>`（写 lane/spec_ref/decided_gmt8；promote 置 status=promoted）。
- `tools/req_pipeline.py`：新增 `--from-queue <id>`（读生产 accepted+lane=direct 需求，取代 seed json 入口）；出口 lane-aware：硬门不过 → 自动 `promote` 回退 + 通知。
- 无新增 HTTP 端点（审阅在本地/对话，非公网）；`/api/feedback` 与 `/api/feedback/track` 已上线不变。

## 4. 硬规则兜底（G5，确定性，非 AI 判断）
`direct` lane 的 diff 必须同时满足，否则强制退回 `promote`：
1. 改动路径 ⊆ `{web/浪报MVP.html}`；**禁碰 `web/e2e/`**（冻结基线）。
2. 非删除（净结构签名不减）。
3. diff 不含契约关键字：`wdeg|tp|tp2|tideEvents|times|windows|hs|wind|gust|_to_decimal|DATA CONTRACT|__SF_READY__`。
4. 无 secret/后门/新增出网端点。
（1-2-4 已在 req_pipeline 现有门实现；3 为本 spec 新增的契约关键字扫描。）

## 5. 复用组件（已建，不重写）
`tools/review_queue.py`(A 审阅台) · `tools/req_pipeline.py`(D 执行端 6 门) · `tools/audit_trace.py`(审计链) · `tools/crons/surf_triage.py`(每日 cron 8e721bb9) · deployment-and-ops 的 `deploy.sh`(版本tag/rollback/canary/CHANGELOG)。

## 6. 测试策略
- 红线逻辑（lane 判定 / 契约关键字扫描 / 兜底退回）单测**边界双侧钉死 + mutation**，**随层编织**（不推迟到最后；见执行注意 2）。
- review_queue↔req_pipeline 串联集成测试用内存 store，不碰生产。
- 冻结 E2E 作发布金丝雀（生产真浏览器），非本 spec 新增。

## 7. ADR（L0 决策 — **已定案 2026-07-26**）

- **ADR-1（D-a）契约关键字黑名单**：**定案 = §4.3 列表**（`wdeg/tp/tp2/tideEvents/times/windows/hs/wind/gust/_to_decimal/DATA CONTRACT/__SF_READY__`）。理由：恰好覆盖 DATA CONTRACT 红线关键面，命中即退回 promote。（实现时清单集中一处常量，便于增补。）
- **ADR-2（D-b）升格目标映射**：**定案 = promote 时人工指定目标产品 spec，追加为该 spec `tasks.md` 一条新 task（引用 feedback id）**。不建集中式第三 backlog——单一真相源，避免 backlog 分裂。
- **ADR-3（D-c）lane 记录方式**：**定案 = feedback 落 `lane` 字段**（可追溯、审计链完整）；旧行缺字段读路径默认值容错。
- **ADR-4（D-d）triage 摘要渠道**：**定案 = dashboard 通知（`send_message` 默认，非 Slack）**。低打扰，贴"不打断既定开发"取向；每日 cron 已按此实现。

### ADR-5~8（云端 LLM 澄清 + LLM coder — **已定案 2026-07-26**；覆盖旧"范围外"）
- **ADR-5 在线 LLM 澄清接入**：**定案 = LLM 进"面向匿名终端用户的在线澄清"**（ECS 调 alblitellm 网关，OpenAI 兼容，模型 bedrock-claude-sonnet-4-6）。**前置连通性已实测确认**（2026-07-26 一次性 run-task 从生产私有子网+NAT 探测 → `PROBE_REACHABLE http 401`，TLS+HTTP 往返成功；401 因未带 key）→ ECS→网关可达，加 key 即可用；不通场景退模板仍作降级兜底。
- **ADR-6 触发模式**：**定案 = 每步自动调**（澄清每轮选项由 LLM 生成，最智能）；代价=延迟/成本，靠 ADR-7 护栏收敛。
- **ADR-7 限流护栏层**：**定案 = 仅应用层**（FastAPI per-IP 限流 + **全局日预算硬闸** + **同页同类选项缓存**(page-schema+步骤+已选→复用) + 超限/不通/报错**降级预置模板**）。**不引 WAF/CloudFront 基建**。多实例计数走 DynamoDB。LLM 输出须 schema 校验(防畸形需求对象)；网关 key 存 Secrets Manager，ECS 任务角色 valueFrom 注入。用户自由文本进 prompt 须系统指令/数据分隔(反注入)。
- **ADR-8 LLM coder 边界**：**定案 = LLM 可写实现，但 LLM-authored 变更一律停 draft PR 等人工审**（守 v5 G1，**无自动合并/部署**，即便纯前端+全绿）。coder 出**锚点 patch(禁全文重写)**、**禁碰 web/e2e/**(冻结基线)、过硬门+secret/后门扫描；需求文本当**数据**处理(反注入)；"删除功能"永不自动。

## 8. 范围外（更新后）
无人值守自动合并/部署（含 LLM-authored，守 v5 G1）；LLM 略过人眼自动上线；新增公网审阅端点；WAF/CloudFront 基建（ADR-7 定为仅应用层）。
（原"云端 LLM 澄清 / LLM coder 自动写实现"已由 ADR-5~8 转入在场并加护栏，不再范围外。）
