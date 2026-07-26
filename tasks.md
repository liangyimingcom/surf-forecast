# Tasks — 自迭代闭环 A(对话审阅台) → E(全链薄彩排)

> 单一驱动器(auto-nudge,禁 task_run)。改前 grep/CodeLens 摸底；改后 pytest/E2E/bash -n。
> 勾选须与文件一致,禁记未落地。生产写(真发布/改生产 status)统一「生产写操作门 G」或人工对话授权。
> 基线：pytest 179 · 冻结E2E 64/0 · 生产 v0.1.1 · feedback 已上线(/api/feedback+track+changelog)。

## A 对话审阅台
- [x] A1 `tools/review_queue.py`(纯stdlib)：list/accept/reject/stats；status过滤+垃圾(空/<8字/非法kind)/重复(归一化text)/优先级(bug>改进>新增>删除)预过滤+摘要；accept→accepted(去TTL)/reject→rejected(留TTL)；--store dynamo|memory。**强制 AWS_DEFAULT_REGION=ap-northeast-1**(botocore读此非AWS_REGION,曾ResourceNotFound)
- [x] A2 对话审阅体验：`list --store dynamo` 生产只读拉待审(scan)已验证——真实队列 3 条(2测试行+**1真实用户建议 ab141aa90439「拼车增加人数选择」**);accept/reject 生产status写=人工对话逐条授权(未擅自改)
- [x] A3 覆盖：`tests/test_review_queue.py` 9 条确定性单测(spam MIN_TEXT_LEN双侧钉死/normalize/dedup首个规范/priority序/triage排序过滤);内存store,不碰生产。pytest 179→**188**

## E 全链薄彩排
- [ ] E1 选真实 accepted 需求 + 备 req_pipeline 需求对象(agent 据需求写声明式 edit,标注 LLM coder 缝)
- [ ] E2 跑 req_pipeline 安全门→AUTO_OK/NEEDS_HUMAN→出 draft PR(--create-pr)  ← G.E2
- [ ] E3 合并→deploy.sh 发布+canary(64/0)→git tag+CHANGELOG(需求ID)  ← G.E3
- [ ] E4 闭环通知：status→shipped；/api/changelog 可见；认领码 track 显 shipped
- [ ] E5 audit_trace --requirement-id <需求> 全环 ✅ 贯通

## [生产写操作门 G]（停下发 blocker 等人工确认）
- [ ] G.E2 真开 draft PR(--create-pr)
- [ ] G.E3 真发布(build+redeploy+canary+git tag+CHANGELOG)
- [ ] G.status 改生产 feedback status(accept/reject/shipped)——逐条人工对话授权
