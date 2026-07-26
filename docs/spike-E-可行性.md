# Spike E — 可行性结论（自迭代闭环 E→D→B）

> 目的：动手前退掉三大未知。逐项更新，E4 汇总取舍。GMT+8。

## E1 · ECS → 外部 LLM 网关连通性 ✅（强推可达，定论级实测待接线时）
- 网关 `alblitellm.liangym.people.aws.dev` DNS → **公网 IP** 34.193.201.46 / 98.90.116.88（AWS 公网，非内网专用）。
- 本地 `GET /v1/models`（Bearer key）→ **HTTP 200**，返回模型列表（含 `bedrock-claude-sonnet-4-6`）。→ 端点**公网可达 + key 鉴权，无需 Midway**。
- 生产 ECS：`enableExecuteCommand=False`（无法直接进容器 curl）；任务在**私有子网 + `assignPublicIp=DISABLED`（NAT 出网）**。
- 判断：app **已成功调用 Open-Meteo 公网 HTTPS**（同 NAT 路径），网关又是公网端点 → **ECS→网关强推可达**。
  - **定论级验证方式**（留到真接线云端澄清时任一）：临时 `enableExecuteCommand` 后容器内 curl；或部署一个一次性 `/api/_llmping` 探针路由。
  - **风险**：若届时不可达 → 退「云端模板澄清(B 已是无 LLM) + 仅本地调网关」，不阻塞 B。
- **对后续取舍**：B(无 LLM 输入端)不依赖此结论，可径直做；云端 LLM 智能澄清(Phase 后续)接线前必须做定论级实测。

## E2 · LLM 网关请求/响应格式 ✅
- 端点 `POST /v1/chat/completions`，**完全 OpenAI 兼容**。鉴权 `Authorization: Bearer <key>`。
- 请求：`{"model":"bedrock-claude-sonnet-4-6","messages":[{role,content}],"max_tokens":N}`。
- 响应(200)：`choices[0].message.content` = 文本；带 `usage`{prompt_tokens/completion_tokens/total_tokens...}。实测延迟 ~4s。
- 错误码：坏 key → **401**。（预算耗尽预期 429/402——应用侧对任何非 200 一律**降级预置模板**，不重试打爆。）
- 结论：后端/本地用标准 OpenAI SDK 或 urllib 直调即可；key 存 Secrets Manager，代码引名不硬编码。

## E3 · Pipeline 出 PR 试跑 ✅（机制通，但暴露 E2E 门稳健性缺口——关键发现）
- 试探：种子需求「直播弹层免责文案微调」→ grep 定位 → 改 `web/浪报MVP.html`(附加式) → `node --check` OK → pytest **147** OK。
  → **编辑+单测环节 pipeline 机制可行**。
- **关键发现（对 D 的自动门致命）**：跑冻结 E2E 时 `page.reload({waitUntil:'networkidle'})`(6 处) **稳定超时 30s**——
  根因是 `probeCamsLive` 从浏览器 fetch 39 个上游 m3u8(部分挂起到 4.5s abort)，网络永不 idle。
  - 早前多轮/生产金丝雀 64/64 通过是因当时上游快；**上游慢时该门稳定变红 = 假失败/会误触自动回滚**。
  - 粗暴改 `networkidle→load` 能跑完但两条**依赖等待时长**的断言(脏值回退/深链恢复)因 settle 不足变红(62/2)。
- **结论/取舍**：**D 把 E2E 当自动合并门之前，必须先加固 E2E**——① 用**显式元素等待**(waitForSelector/期望文本)取代 networkidle 与固定 waitForTimeout；② 或测试期禁用/短路 probeCamsLive(加 `?e2e=1` 旗标)。否则自动门不可靠。
- 试探改动已回滚，工作树干净(networkidle 恢复、文案复原)。

## E4 · 汇总结论与取舍 ✅
**三项未知全部退掉，可推进 D/B；但给 D 加一条前置硬约束。**

| 未知 | 结论 | 对后续的取舍 |
|------|------|-------------|
| E1 ECS→LLM 网关连通 | 公网可达+key鉴权，ECS 强推可达（定论级实测待接线） | 云端 LLM 澄清可行；**B 无 LLM 不依赖它** |
| E2 网关调用格式 | OpenAI 兼容 `/v1/chat/completions`(200/usage,坏key 401,~4s) | 后端 urllib/OpenAI SDK 直调；key 进 Secrets Manager；非200 降级模板 |
| E3 Pipeline 出 PR | 编辑+pytest 机制通；**E2E 门在探活下 networkidle 稳定超时=假失败** | ⚠️ **D 前置**：先加固 E2E(显式元素等待/测试期短路探活)，否则自动门不可靠、会误触回滚 |

**Go/No-Go**：
- ✅ **B（无 LLM 输入端）可直接做**——不依赖 E1/E3 的任何风险。
- ✅ **D（执行端闭环）可做，但必须先加固 E2E**（新增 D0：E2E 稳健化）再谈"绿 E2E 自动门"。
- ⏸️ **云端 LLM 智能澄清（Phase 后续）**：接线前补 E1 定论级实测(execute-command/探针)。

**建议下一步顺序调整**：D0(加固 E2E) → D1..D4(执行端闭环) → B(无 LLM 输入端)。或先做 B(零风险见效快)。

## D0 探索记录（2026-07-26，止损后结论）
- 试过 `networkidle→domcontentloaded/load` 快改：均破坏"隐式数据就绪"——原 networkidle 恰好等到 loadCatalog/loadCams/loadLive 填完数据，换掉后断言在数据未就绪时执行 → 新失败(62/2、61/3、且偶发早退)。已全部回滚，E2E 恢复基线(networkidle×6)。
- **定性**：D0 非 spike 快改，而是一次**成规模重写**——需给每个数据相关断言加**显式元素等待**(如 `waitForSelector('#catList .cat-item')`/期望文本)取代 networkidle+固定 timeout；同时让 probeCamsLive 的网络活动不阻断就绪判定(如探活并发/超时收紧，或测试期用独立于金丝雀的旗标短路——注意**生产金丝雀也是 Playwright，不能用 navigator.webdriver 短路**)。
- **flaky 触发条件**：仅当上游 isurfvideo 慢/不可达时 networkidle 超时；今早上游快时 64/64 稳定(含生产金丝雀)。即"绿 E2E 自动门"在上游慢时会假失败。
- **取舍**：B(无 LLM 输入端)不依赖 D0，建议**先做 B**；D0 作为 D 的独立前置，另起专门一轮认真重写。

## D0 二次尝试记录（2026-07-26，显式元素等待重写后仍止损）
- 做法：`networkidle→domcontentloaded` + 每次导航/reload 后 `waitForSelector('.maintab-btn.on')` 应用外壳就绪 + 脆弱断言(脏值回退/深链)加定向 waitForFunction。
- 结果：**63/64 稳定通过**（networkidle 的"探活致 hang"已消除，真实改善）；但 **U-e 深链恢复浪点名 稳定失败**——`domcontentloaded` 模式下 reload 后深链 bootstrap 链(demoAuth→loadSpots→loadCatalog→loadLive→应用 #spot hash)未更新 #metaSpot，即便等 20s 也不满足。
- **根因定性**：deep-link 恢复依赖 load 事件后的长异步链 + 无"就绪信号"可等 → 纯 E2E 改等待无法确定性等到。**真正的修法在 app 侧**：给 bootstrap 加一个测试可见的就绪信号(如 `window.__SF_READY__=true` 或 body[data-ready]），E2E 等它而非猜时间；深链恢复亦应在该信号内完成。
- **结论**：D0 = 「app bootstrap 就绪信号 + E2E 改等该信号」的**联合改造**（比纯 E2E 编辑大），是 D 自动门的硬前置。已回滚 E2E 到基线(networkidle×6)避免留红套件。**D 在此前置完成前不能上无人值守自动门**。

## D0 ✅ 已解决（2026-07-26 第三次，就绪信号方案）
- app：`bootstrap()` 末尾(整条链含深链 loadLive 完成后)置 `window.__SF_READY__=true` + `document.body.dataset.ready='1'`。
- E2E：6 处 `networkidle`→`domcontentloaded` + `const ready=()=>page.waitForFunction(()=>window.__SF_READY__===true,{timeout:30000})`，导航/reload 后一律 `await ready()`。reload 后信号自动重置→等 bootstrap 重跑完成。
- 结果：**连跑 3 次 64 passed / 0 failed，确定性稳定**；深链(U-e)亦通过；不受上游探活网络快慢影响。pytest 153 / schema_check ✅ 无倒退。
- **意义**：冻结 E2E 现可作 D 无人值守自动门的可靠判据（绿=真绿，不再假失败误触回滚）。

