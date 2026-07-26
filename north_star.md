# North Star — 自迭代闭环 A(对话审阅台) → E(全链薄彩排)

## 目标
把"活的用户建议"接成**真正的闭环**：
1. **A 对话审阅台**：从生产 feedback 表拉待审建议 → 人工在对话里 accept/reject → 改 status（accepted 进 pipeline 队列，去 TTL）。补上"输入端↔执行端"缺失的中段。
2. **E 全链薄彩排**：取一条真实 accepted 需求，跑通整环——
   `建议 → 审阅accept → req_pipeline安全门 →(纯前端全绿=自动 / 否则人工)draft PR → 合并 → 部署+金丝雀 → status=shipped → 更新日志/认领码可见 → 审计链贯通`。

## DoD（每阶段）
- 相关 pytest/冻结E2E 全绿(64/0)+0 JS 报错；schema_check ✅；红线零违反；据实勾选。
- A：review_queue 工具有确定性单测（状态流转/过滤/去重双侧钉死）；对生产表操作**逐条由人工在对话里授权**。
- E：一条真需求端到端可追溯——`audit_trace --requirement-id` 全环 ✅ 贯通（不再 ⏳）。

## 红线（不可妥协）
- **单一驱动器**：dashboard auto-nudge 唯一驱动，**绝不调 task_run**。
- **AI 绝不自动合并 master / 自动部署生产**：pipeline 只出 draft PR；真发布(build/redeploy/canary/tag)统一停「生产写操作门 G」等人工确认。
- **审阅 accept/reject 改生产 status = 人工在对话里逐条授权**（人即是门），非无人值守。
- 自动路径仅当：路径 ⊆{web/浪报MVP.html} + 非删除 + pytest/E2E 全绿 + diff 安全扫描过；**禁碰 web/e2e/**（冻结基线）。
- 沿用既有红线：GMT+8 / DATA CONTRACT wdeg / DynamoDB float→Decimal(_to_decimal) / 全 401 / ALB SG 禁 0.0.0.0/0 / terraform 禁 -auto-approve。
- 新增 DynamoDB 表/IAM 走既有教训（任务角色按表 ARN 授权 + IAM 最终一致）。
- 每轮改前 grep/CodeLens 摸底 + 算爆炸半径；改后 pytest/E2E 不倒退。
- **LLM coder 未接线**（方向 D 未选）：E 彩排的 edit 由 agent 据需求手工写声明式 edit，此为唯一人工缝、显式标注。

## 范围外
匿名触发合并/部署；向匿名暴露 CodeLens/源码；云端 LLM 澄清接线（方向 C）；LLM 自动写 edit（方向 D）；TTL 误删已采纳需求。

## 停止
所有本地可交付完成、仅剩生产写操作门(G)时，创建 STOP：
`/Users/yiming/.meshclaw/workspace-surf-forecast/.stop-chat-3-1783779532`
