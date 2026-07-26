# Tasks — 自迭代闭环 E→D→B

> 单一驱动器(auto-nudge,禁 task_run)。改前 grep/codelens 摸底；改后 pytest/E2E/bash -n。
> 勾选须与文件一致,禁记未落地。触碰生产统一在「生产写操作门 G」停下等确认。
> 基线：pytest 147 · E2E 64/64 · 生产 v0.1.0 · Phase0 地基(版本/回滚/金丝雀/审计/告警)已上线。

## E 可行性 spike（先做，出结论+风险，不写产品代码）
- [x] E1 ECS→`alblitellm` 连通性：网关=公网IP+key鉴权(本地GET /v1/models 200,含 bedrock-claude-sonnet-4-6);ECS 私有子网+NAT已调Open-Meteo公网→**强推可达**;定论级实测(execute-command/探针)待接线时。结论落 docs/spike-E-可行性.md
- [x] E2 本地试调网关 sonnet-4-6：`POST /v1/chat/completions` OpenAI 兼容(200,choices[].message.content+usage,~4s);坏key 401;非200 应降级模板。结论落文档
- [x] E3 Pipeline 出 PR 试跑：编辑+pytest 机制通;**关键发现**——冻结 E2E 的 networkidle 在 probeCamsLive 下稳定超时(假失败),D 用作自动门前必须改显式元素等待/测试期短路探活。试探改动已回滚
- [x] E4 结论落 `docs/spike-E-可行性.md`（三项结论+风险+对 D/LLM 取舍）：E1/E2 ✅可行;E3 给 D 加前置 D0
  → Go/No-Go：B 可直接做(零依赖);D 需先 D0 加固 E2E;云端 LLM 澄清接线前补 E1 定论级实测

## D 最薄执行端闭环
- [x] D0 **✅ 已解决** 加固冻结 E2E：app bootstrap 末置就绪信号 `window.__SF_READY__`+`body[data-ready=1]`(整链含深链完成后)；E2E 全部 networkidle→domcontentloaded+`await ready()`(等就绪信号)。**3/3 跑 64/0 稳定确定性**,深链亦过。pytest153/schema✅。→ D 自动门现可靠可上
- [x] D1 需求对象 schema：`docs/requirement-schema.md`(字段+status状态机+TTL红线+可回滚性/auto_eligible) + 手工种子 `reference/data/seed_requirement.json`(1条 accepted·纯前端·可回滚)
- [x] D2 本地 pipeline 脚本 `tools/req_pipeline.py`(纯stdlib)：读 accepted 需求→声明式确定性 edit(幂等,LLM coder 后续接线)→**确定性安全门**(资格/路径白名单⊆{web/浪报MVP.html}禁碰web-e2e/非删除净签名判定/secret+后门+新出网扫描)→node--check/schema_check/pytest/**冻结E2E(起服SF_FRONTEND+SF_SEED_SPOTS)**→全绿=AUTO_OK 出 draft PR(默认dry-run,真开需--create-pr)。审计→pipeline_audit.jsonl。**种子端到端 AUTO_OK(pytest174+E2E64/0)**;负路径实证(eval注入被扫描拦且未落盘/e2e路径被白名单拦→NEEDS_HUMAN)。门单测 `tests/test_req_pipeline.py` 21条双侧钉死(pytest153→174)
- [ ] D3 人工合并→deploy.sh 发布+canary→CHANGELOG(需求ID)  ← 真发布属 G 门
- [x] D4 审计链贯通验证 `tools/audit_trace.py`(纯stdlib)：追溯 `需求ID↔pipeline审计↔分支/PR/commit↔版本tag↔CHANGELOG↔部署时间`,每环标 ✅存在/⏳待D3/❌断裂。seed-0001 链**已接线**(需求↔pipeline ✅ verdict=AUTO_OK 8/8门绿;PR/tag/CHANGELOG/部署 ⏳待D3);v0.1.0 子链 CHANGELOG 真实数据全✅。解析器单测 5 条(pytest174→179)。约定:需求发布 SF_RELEASE_NOTE="需求<ID>:..."写CHANGELOG。**发现:git tag 从未打(仅ECR镜像tag)→D3发布应补 git tag vX.Y.Z 闭合"版本↔commit"环**

## B Phase1 无 LLM 输入端
- [x] B1 `/api/feedback`(匿名POST,长度上限,GMT+8,status=new+认领码) 落库；db 双store add/list/set_feedback_status;DynamoDB TTL 仅 new/rejected(采纳去TTL)。pytest 147→**150**(+3)
- [x] B2 page-schema：`PAGE_SCHEMA`(live/report/other 各含 label/features/topics) 定义于 HTML;`web/e2e/schema_check.mjs` 纯node守卫(键==maintab data-tab,防漂移)✅
- [x] B3 预置模板澄清 UI：悬浮「💡提建议」→ 弹层 3 步(类别→PAGE_SCHEMA主题→文本,可跳过,≤3步)→结构化需求 POST /api/feedback→显示认领码。焦点探针跑通(类别→主题→文本→claim码);零 LLM。E2E 持久断言并入 B5
- [x] B4 公开更新日志页(GET /api/changelog 读 CHANGELOG)+匿名认领码查进展(GET /api/feedback/track?claim,只回状态/时间/类别)；前端「其他」tab #changelog 块(切页加载+状态中文映射)。探针:日志4条+查进展显"待审阅"。生产镜像需含 CHANGELOG.md→G门
- [x] B5 覆盖：pytest 150→**153**(+changelog/track/bad-claim) · schema_check.mjs ✅ · inline JS OK；B3/B4 交互经 Playwright 焦点探针验证(全套 E2E 断言待 D0 加固后并入)

## [生产写操作门 G]（停下发 blocker 等人工确认）
- [ ] G.D3 D 的真实发布(build+redeploy+canary)
- [ ] G.B1 生产 DynamoDB 建表/灌数据 + /api/feedback 真上线
