# 需求对象 Schema（D1）—— 用户建议自迭代闭环

需求对象贯穿：用户澄清(B3) → 落库(/api/feedback) → 人工审阅(C) → 本地 Pipeline 实现(D) → 发布 → 审计链。

## 字段
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | str | 唯一 ID（uuid12 或 seed-*）|
| `status` | enum | 状态机：`new`→`triaged`→`accepted`→`in_progress`→`shipped` / `rejected` / `expired` |
| `kind` | enum | `new_feature`/`improve`/`remove`/`bug` |
| `page` | str | 来源 tab：`live`/`report`/`other`（对齐 PAGE_SCHEMA）|
| `text` | str | 结构化需求正文（≤2000，含 [主题] 前缀）|
| `repro` | str | 复现步骤（bug 用，≤1000）|
| `expect` | str | 期望效果 |
| `accept` | str | **验收标准**（Pipeline 出 PR 时据此自评）|
| `rollbackable` | bool | 可回滚性：纯前端=true；含 DynamoDB 数据/schema=false（只能前向修复）|
| `auto_eligible` | bool | 是否符合无人值守自动门候选（纯前端+非删除；最终仍由 CI 路径白名单+全绿+扫描裁定）|
| `claim_code` | str | 匿名提交者认领码（查进展）|
| `created_gmt8` | str | 提交时间 GMT+8 |

## 状态机 + TTL（红线）
- TTL 仅清 `status ∈ {new, rejected}` 且超 14 天者；**`accepted`/`in_progress`/`shipped` 绝不被 TTL 删**（防冷点炸弹同类耦合）。
- 人工审阅(C)把靠谱需求 `new→accepted`（去 TTL 进 Pipeline 队列）；不靠谱 `→rejected`（TTL 清）。

## 手工种子
`reference/data/seed_requirement.json` = 一条 `accepted` 种子（纯前端·可回滚·auto_eligible），供 D2 本地 Pipeline 消费做端到端演示。

## 审计链约定（D4）
全链路：`需求ID ↔ pipeline审计(pipeline_audit.jsonl) ↔ 分支/PR/commit ↔ 版本tag ↔ CHANGELOG条目 ↔ 部署时间`。
- **需求驱动的发布**：`deploy.sh frontend` 时设 `SF_RELEASE_NOTE="需求<ID>: <摘要>"`，使 CHANGELOG 摘要含需求ID（`audit_trace.py` 据此贯通）。
- **git tag**：D3 发布应在发布 commit 打 `git tag vX.Y.Z`（当前仅有 ECR 镜像 tag，git tag 未打→"版本↔commit"环靠 CHANGELOG 的 commit 字段兜底，打 git tag 后可 `git checkout vX.Y.Z` 复现）。
- 验证：`python3 tools/audit_trace.py --requirement-id <ID>`（全绿=贯通 / ⏳=待发布 / ❌=断裂）。
