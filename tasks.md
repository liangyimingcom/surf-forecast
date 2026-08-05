# Tasks — 数据健康收口（映射 `roadmap.md`）

> 每完成一项**立刻勾选**并在 `docs/implementation-notes.md` 追加一行（含偏离计划的理由）。
> 🔒 = 硬门，**loop 不得执行**，只整理成待人工确认清单。
> 每轮开始先查停止信号：`ls /Users/yiming/Downloads/all_the_meshclaw/surf-forecast/.stop-chat-3-1783779532`
> （由 auto-nudge 指定的真实路径；存在即停。旧文中的 `STOP_LOOP` 已作废）。

## R0 · 起手

- [x] R0.1 查停止信号（真实路径见上）确认无停止
- [x] R0.2 在 `master` 且已 pull；建/切工作分支 `feat/data-health-r3`（不推 master）
- [x] R0.3 `pytest -q` 取基线 = **293 passed**
- [x] R0.4 读 `docs/HANDOFF-to-kiro.md` §5 + §7（已知坑与已修事项）

## R1 · 绿灯必须等于可用（核心）

- [x] R1.1 `src/web/refresh.py` 的 `refresh_spots`：加 `days > 0` 判定；空报告记
      `skipped: empty_report(upstream grid all-null)`，且**不覆盖上一版缓存**（同 validate 失败策略）
- [x] R1.2 失败原因贯通到 `/api/status`：`failed` 保持 slug 列表（前端 `join` 契约不破），
      新增 `failed_detail = {slug: 原因}`；前端 `StatusPage.vue` 渲染 `slug — 原因`
- [x] R1.3 单测双侧钉死：空报告 → 非 ok + 原因含 `empty_report`/`upstream` + 不覆盖上一版 + 不写当日快照；
      有 days → 仍 ok；端到端 → `manifest.failed` 带原因
- [x] R1.4 定向测试绿（refresh/status_api/refresh_cli/governance **32 passed**）
- [x] R1.5 预期变化已确认：判定生效后 `sl82 Canggu` 将从 succeeded 掉入 failed（正确行为）
- [x] R1.6 **顺手修掉一个测试污染**：`/api/status` 走进程内 `_agg_cache`（TTL 300s），
      上一个测试的响应会串给下一个（同 fixture 数据时看不出来）。`test_status_api.py`
      加 autouse fixture 每例前后清空


## R2 · `/status` 能自己发现三类静默故障

- [x] R2.1 空报告：`failed_detail` 里能看出「上游格点全空」这类原因（承 R1.2，已完成）
- [ ] R2.2 坐标非法：`/api/status` 暴露带 `coord_invalid` 标记的行（PR #38 护栏会打此标）。
      ⚠️ **生产当前应为 0 行**（sl75/sl76 坐标已修，且护栏只作用于未来 seed）——
      这是"未来复发的探测器"，别以为查不到就是没接通；用单测 + 本地 seed 造数据验证
- [ ] R2.3 坐标重复：暴露 4dp 相同坐标的分组（已知 3 组 `sl49/sl93`、`sl54/sl84`、`sl2/sl58`）
- [ ] R2.4 前端 `/status` 页同步显示这三块，措辞守数据诚实（不可用就说不可用）
- [ ] R2.5 单测钉死 `/api/status` 新字段形状；**零新增持久化**（派生自 registry+manifest+缓存）
- [ ] R2.6 `web/e2e/vue_spa.mjs` 状态页断言覆盖新区块

## R3 · 坐标解析歧义防护

- [ ] R3.1 `find_registry_by_coord` 多行命中时：记日志告警 + **确定性选取**（如 slug 字典序最小），
      不再静默取首个
- [ ] R3.2 `InMemoryStore` 与 `DynamoDBStore` 两实现语义一致
- [ ] R3.3 单测：单命中 / 多命中→确定性 + 告警 / 两 store 一致性

## R4 · 上游格点巡检脚本（只读）

- [ ] R4.1 新建 `tools/probe_grid_health.py`：遍历注册表坐标探测上游是否全空；
      全空点搜索邻近格点（±0.05°/±0.1°）给出可用坐标建议；输出到 stdout
- [ ] R4.2 **只读**：不得写 DynamoDB（那是 🔒 G1）；不引新依赖。
      数据来源二选一：① 生产 registry 只读 scan（`AWS_PROFILE=oversea1`、`ap-northeast-1`、
      表 `surf-forecast-dev-spot_registry`）；② 本地快照 `reference/data/shilaoren_spots.json`
      （注意快照里 sl75/sl76 仍是坏坐标，生产已修——两者会不一致，属预期）
- [ ] R4.3 对全量 registry 干跑通过，且能复现 `sl82 Canggu` 诊断
      （现格点 `-8.75/115.25` 全空 → 建议经度 ≈`115.05` 落入 `-8.75/115.0`，实测 1.74m）

## R5 · 收口

- [ ] R5.1 `pytest -q` 全量全绿（基线 293，只增不减）
- [ ] R5.2 `vue_spa.mjs` E2E 全绿 + 0 JS 报错
      （`npm run build` → 起后端带 `SF_SEED_SPOTS=reference/data/shilaoren_spots.json`
      + `SF_SPA_DIST=web/frontend/dist` → `node web/e2e/vue_spa.mjs http://127.0.0.1:PORT`）
- [ ] R5.3 文档回写：`docs/implementation-notes.md` 逐日记录 + `docs/HANDOFF-to-kiro.md` §7 本轮结论
- [ ] R5.4 开 PR（**不合并**，🔒 G4）
- [ ] R5.5 整理 🔒 门项待人工确认清单（见下），每项写清「做什么/为什么/怎么回退」
- [ ] R5.6 创建 `STOP_LOOP` 并汇报

## 🔒 待人工确认清单（loop 只整理，不执行）

- [ ] 🔒 G1-a Canggu 坐标微调（经度 ≈`115.05`）—— 生产 DynamoDB 写
- [ ] 🔒 G1-b 3 组重复坐标去歧义 + `sl84 Kirra` 坐标疑与 `sl54` 串行
      （Kirra 在澳洲，注册表却是 `22.60,114.91` = 广东境内）—— 生产 DynamoDB 写
- [ ] 🔒 G2-a 配置 `SF_TEST_ACCESS_KEY`（task def env），E2E 带 `X-Test-Access` 头访问测试点
- [ ] 🔒 G2-b 本轮代码上生产（build → rollback 切版 → canary → smoke → tag → CHANGELOG）
- [ ] 🔒 G1-c 重建测试账号 `tester@surf.local`，凭据记到安全位置（不入库、不进仓库）

## 已完成（上一轮，勿重做）

- [x] PR #37 合并 master（merge commit `7e9f481`，保留 12 提交以便 tag 锚定）
- [x] git tag `v0.3.0`(`0372fd7`)/`v0.3.1`(`b1f60c1`)/`v0.3.2`(`ef0bfd6`)/`v0.3.3`(`6c97860`)
- [x] `deploy.sh smoke` 断言修正（公开面 200×4 + 合规红线 cams 匿名 401），对生产实跑 6/6 绿
- [x] sl75/sl76 坐标护栏（导入路径补 `validate_coord`，非法即隔离）+ 5 单测（PR #38）
- [x] sl75/sl76 生产坐标修正 + 刷新验证 **60/60 · failed=[]**（PR #39 记录）
- [x] goal 三件套改为以 `docs/HANDOFF-to-kiro.md` 为唯一事实来源
