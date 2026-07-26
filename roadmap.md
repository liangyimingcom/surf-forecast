# Roadmap — 自迭代闭环 E→D→B

单一驱动器(auto-nudge)。每轮挑最高杠杆一步，改前 grep/codelens 摸底，改后 pytest/E2E/bash -n；
触碰生产统一在「生产写操作门 G」停下等人工确认。顺序 E→D→B。

## E 可行性 spike（先做，只出结论+风险，不写产品代码）
- E1 ECS→`alblitellm` 连通性：探生产 ECS 出网能否直连该内网域(方案：临时探测/ecs execute-command/或退回结论"不可达→云端澄清需 NAT 或退模板")。
- E2 LLM 网关请求/响应：本地用 key(Secrets Manager 存,代码引名)试调 sonnet-4-6，记录 OpenAI 兼容格式/鉴权/错误码。
- E3 Pipeline 出 PR 试跑：取一条真实小需求(如"目录空态文案微调")→codelens 摸底→改 web/浪报MVP.html→pytest+E2E→draft PR，验证"能过冻结 E2E"。
- E4 结论落 `docs/spike-E-可行性.md`(三项结论+风险+对 D/LLM 的取舍)。

## D 最薄执行端闭环
- D1 需求对象 schema(JSON: id/类型/页面/复现/期望/验收/可回滚性/status)；先支持手工种子一条。
- D2 本地 pipeline 脚本：读一条 accepted 需求→实现纯前端小改→跑 pytest+E2E→路径白名单+非删除+diff 安全扫描→出 draft PR(gh)。
- D3 人工合并(gate)→复用 deploy.sh 发布(build+redeploy)+金丝雀(canary)→CHANGELOG(需求ID)。
- D4 审计链验证：需求ID↔PR↔版本tag↔CHANGELOG↔部署时间 一条样例贯通。

## B Phase1 无 LLM 输入端
- B1 `/api/feedback` 落 DynamoDB 新表(float→Decimal,status 状态机,TTL 按 status)；匿名可提+每IP限流。
- B2 page-schema：每 tab 能力上下文卡，从代码派生(或校验 UI 变更同步)。
- B3 预置模板澄清 UI：基于 page-schema 给选项菜单/输入框(零 LLM,≤4 轮收敛,可跳过)→产出结构化需求对象。
- B4 公开更新日志页(读 CHANGELOG) + 匿名认领码(查自己那条 status)。
- B5 pytest/E2E 覆盖新增；node --check。

## [生产写操作门 G]（高风险，停下发 blocker 等人工确认后执行）
- G.D3 D 的真实发布(build+redeploy+canary)；G.B1 生产 DynamoDB 建表/灌数据；其余真部署。
