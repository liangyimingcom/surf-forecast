# Tasks — 在线 LLM 澄清 + coder 实现（L1-L5）

> 单一驱动器(auto-nudge,禁 task_run)。LLM 全程 mock 测试(不触网/不烧钱);真调网关/Secrets/部署留 G 门。
> 改前 codelens-dev 摸底;红线逻辑测试随层双侧钉死+mutation。全程 GMT+8;据实勾选。
> 基线：pytest 211 · 冻结E2E 64/0 · 生产 v0.1.3 · ADR-5~8 定案+连通性已实测 · 设计 docs/自迭代-在线LLM澄清与coder-设计v6.md。

## R0 摸底
- [x] R0.1 注入点定位：前端降级基点 openFeedback→fbRender(1kind/2topic/3text)→fbSubmit(零LLM模板) · 后端 RequirementIn(app.py:224)+submit_feedback 旁加 /api/clarify · LLM key 走 env(SF_LLM_KEY/URL/MODEL,Secrets valueFrom 同 SF_CACHE_BUCKET) · coder 挂 req_pipeline.apply_edit(find/replace 声明式,--llm-coder 让 LLM 生成 edit 再走既有门)

## L1 数据模型
- [x] L1.1 `src/web/llm_guard.py`：RateLimiter(per-IP滑窗) + DailyBudget(全局每日硬闸,GMT+8跨天重置) + option_cache_key + validate_clarify(options≤8/≤60字 或 requirement{kind,text} schema校验)。纯stdlib注入时钟。选项缓存值复用 cache.TTLCache
- [x] L1.2 `tests/test_llm_guard.py` 15 用例边界双侧钉死+mutation(限流N/N+1·预算max/max+1·跨天重置·options 0/8/9·60/61字·kind非法·空text)。pytest 211→**226**

## L2 接口
- [x] L2.1 `src/web/llm_client.py`(OpenAI兼容stdlib,env配置SF_LLM_URL/KEY/MODEL,is_configured,chat抛LLMError) + `POST /api/clarify`(缓存→per-IP限流→日预算硬闸→调网关(可注入mock)→schema校验→任一不过降级模板;反注入prompt)。tests/test_clarify.py 5用例(降级/LLM/畸形/网关错/缓存命中,全mock)。pytest 226→**231**
- [x] L2.2 `req_pipeline --llm-coder`：`_llm_generate_edit`(自包含urllib,锚点find/replace patch,禁全文重写/禁碰web-e2e/需求当数据) → 无edit时生成 → 走既有硬门 → draft PR;**LLM-authored一律人工审**(永不自动合并,守G1)
- [x] L2.3 tests/test_req_pipeline_coder.py 4用例(生成→过门AUTO_OK/生成失败→NEEDS_HUMAN/无flag→人工/未配置抛错,全mock)。pytest 231→**235**

## L3 用户可见
- [x] L3.1 前端 `_fbClarifyEnhance()`：澄清步骤2 模板即显 + 后台调 /api/clarify,LLM 选项替换(标🤖AI追问);未配/降级/失败保持模板不阻塞。渐进增强(接key前行为=现状)
- [x] L3.2 冻结 E2E **64/0** 不倒退(本地未配LLM→降级模板) + /api/clarify 降级冒烟(template)。pytest 仍 **235**

## L4 内部逻辑(护栏)
- [x] L4.1 per-IP 限流 + 全局日预算硬闸(超限→降级不再调网关) + 反注入(系统/数据分隔) — 已在 /api/clarify 实现(llm_guard)
- [x] L4.2 coder 锚点patch(禁全文重写)+禁碰web/e2e/(gate_path_whitelist)+diff secret扫描(gate_secret_scan)+需求当数据 — L2.2 实现+既有 test_req_pipeline 覆盖
- [x] L4.3 tests/test_clarify_guard.py 3用例(限流超限→降级/预算超限→降级/反注入prompt结构)。pytest 235→**238**

## L5 收尾
- [x] L5.1 全量 pytest **238**(LLM全mock) + 冻结 E2E 64/0 + py语法OK + schema同步;提交PR + STOP

## [生产写操作门 G]（停下发 blocker 等人工确认）
- [ ] G.1 Secrets Manager 存网关 key + ECS 任务角色 valueFrom + (若新表)建表+IAM(按新表ARN授权,IAM最终一致)
- [ ] G.2 部署(build+redeploy+canary+tag+CHANGELOG) + 生产真调网关冒烟(带预算/限流)
