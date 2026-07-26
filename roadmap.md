# Roadmap — 自迭代闭环 A(对话审阅台) → E(全链薄彩排)

单一驱动器(auto-nudge)。每轮挑最高杠杆一步，改前 grep/CodeLens 摸底，改后 pytest/E2E/bash -n；
生产写操作(真发布/真改生产 status)统一在「生产写操作门 G」或人工对话授权下执行。顺序 A→E。

## A 对话审阅台（连接输入↔执行的中段；工具本地实现+单测，对生产操作人工授权）
- A1 审阅工具 `tools/review_queue.py`(纯 stdlib)：子命令 list/accept/reject/stats；
     读 feedback（status 过滤）+ 垃圾/超短/重复预过滤 + 摘要展示；accept→status=accepted(去TTL)，reject→status=rejected(留TTL)。
     支持 `--store dynamo`(生产,需 creds) 与 `--store memory`(测试/dry-run)。
- A2 对话审阅体验：review_queue list 拉待审 → 我在对话把摘要+预分类拉给你 → 你说"接受X/驳回Y" → 我调 accept/reject 改 status（逐条人工授权）。
- A3 覆盖：review_queue 状态流转/过滤/去重 确定性单测（双侧钉死边界）；用内存 store 模拟，不碰生产。

## E 全链薄彩排（一条真需求跑通整环）
- E1 选一条真实 accepted 需求（A 审阅产出；队列空则用一条真实提交样本 accept）→ 备 req_pipeline 可消费的需求对象（agent 据需求手工写声明式 edit，标注=LLM coder 缝）。
- E2 跑 `req_pipeline`：安全门 →(纯前端+全绿=AUTO_OK / 否则 NEEDS_HUMAN)→ 出 draft PR（--create-pr，真开）。
- E3 合并（自动路径判定/人工）→ deploy.sh 发布(build+redeploy)+金丝雀(canary 64/0)→ git tag + CHANGELOG(需求ID)。  ← 真发布=G门
- E4 闭环通知：该需求 status→shipped；生产 /api/changelog 可见；认领码 track 显示 shipped。
- E5 审计链验证：`audit_trace --requirement-id <该需求>` 全环 ✅ 贯通（不再 ⏳）。

## [生产写操作门 G]（停下发 blocker 等人工确认后执行）
- G.E2 真开 draft PR（--create-pr 推分支+建 PR）
- G.E3 真发布(build+redeploy+canary+git tag+CHANGELOG)
- G.status 改生产 feedback status（accept/reject/shipped）——逐条人工对话授权
