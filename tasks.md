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
- [x] R2.2 坐标非法：`/api/status` 的 `data_issues.coord_invalid` 暴露带标记的行。
      ⚠️ **生产当前应为 0 行**（sl75/sl76 坐标已修，且护栏只作用于未来 seed）——
      这是"未来复发的探测器"，别以为查不到就是没接通；用单测 + 本地 seed 造数据验证
- [x] R2.3 坐标重复：暴露 4dp 相同坐标分组，**并分级**——同 `beach_group`=同滩机位(expected，只计数)，
      跨滩/跨区=suspect(才上报)。生产 3 组里只有 `sl54/sl84`(Kirra 在澳洲) 是真异常；
      不分级则 2/3 是误报、告警会被无视
- [x] R2.4 前端 `/status` 新增「数据治理待办」卡片，按分级展示（合理重复只报数）
- [x] R2.5 单测钉死字段形状 + 分级语义 + 测试点不外泄；零新增持久化
- [x] R2.6 E2E 覆盖新区块（canned status 补 `data_issues`，否则该 UI 分支等于没被测）

## R3 · 坐标解析歧义防护

- [x] R3.1 新增共享 `db.pick_registry_match`：多行命中 → 按 slug 字典序取最小 + WARNING 告警
      （文案含全部候选、实际选中者，并指向 /status 的治理区块）
- [x] R3.2 两 store 都改为「收全部匹配 → 委托 pick_registry_match」，语义一致由构造保证
- [x] R3.3 `tests/test_coord_resolution.py` 10 例：无/单/多命中 · 反序输入同结果 ·
      caplog 验告警含全部候选 · inactive 忽略 · 4dp 精度(6位入库4位查得中) ·
      **moto 真跑双 store 选中同一行** · 无命中返回 None

## R4 · 上游数据可用性（**范围偏离：先修根因，脚本降级为次要**）

> 偏离理由：动手前核对引擎实际取数参数时发现，`fetch.py` 里「WAM 缺则回退 best_match」
> （需求 1.5）**是死代码**——best 请求的 hourly 从来没要 `wave_height/direction/period`。
> 实测 best_match 在 Canggu 格点 `-8.625/115.125`（比 WAM 的 `-8.75/115.25` 更贴近实际位置）
> 有完整数据（1.36m / Tm 12.9s）。**修回退比写巡检脚本高一个数量级**：不需要写生产数据、
> 不需要猜坐标，就能救回该点；而巡检脚本只是"帮人找可用坐标"。

- [x] R4.0 修复回退死代码：best 请求补 `wave_height/wave_direction/wave_period`
- [x] R4.0b 溯源可见（tech.md「可信度一等公民」）：`_day_to_dict` 输出 `dataSource`，
      详情页在校准时间戳下提示「浪高取自 best_match 备用模型，Tp 留空不估算」——不静默换源
- [x] R4.0c 测试：请求层含回退字段 · WAM 全空→回退且 source 标记正确 · Tp 留空不编造 ·
      两源皆空仍产不出点（此时才是真"上游无数据"，由 R1 计入 failed）· WAM 有数据时不被顶替
- [x] R4.0d 真实验证：Canggu 真坐标跑引擎 → **3 天 × 24 点**，源 `best_match(fallback)`
- [x] R4.1 巡检脚本 `tools/probe_grid_health.py`（stdlib、只读、`--source snapshot|store`、
      `--slug/--limit/--json`、exit 2 可接 cron）。判定与引擎一致：WAM→best_match 回退后
      仍无浪高才算 dead，并对 dead 点搜邻近格点给坐标建议
- [x] R4.2 **生产全量实跑结论**：58 点 = `ok_wam 55` · `ok_fallback 1`(sl82 Canggu，已被
      R4.0 救回) · `dead 2`：
      - `sl97 SURFPARK` 坐标 `39.894,116.598` = **北京**，是人工浪池 → 海洋预报对它
        天生无意义，不该在海洋刷新池里（处置=治理标记，不是改坐标）
      - `sl71 海螺湾` 声称 `region_cn=浙江`，坐标却在广西/广东内陆，且经度与
        `sl57 石梅湾-艾美` 完全相同 → 上游串行（见 R2.7）

## R2.7 · 坐标分量串行探测（本轮新增，抓 4dp 探测器看不见的一类）

- [x] R2.7a `governance.coord_component_collisions`：多点共享同一**高精度**(≥6 位小数)
      lat 或 lon 值 → 跨 `region_cn` 即 suspect。高精度浮点巧合相同物理上不可能，
      只可能是上游串行；而串行**可只发生在单个分量**，此时组合坐标唯一、4dp 探测器看不见
- [x] R2.7b `/api/status` 暴露 + 前端「数据治理待办」展示（跨区标注）
- [x] R2.7c 测试含**关键对照**：只串一个分量时 `coord_duplicate_groups` 抓不到、
      本探测器必须抓到；低精度值不报（防误报）；真实快照回归 sl84/sl85/sl71
- [x] R2.7d **生产实测抓到 3 例，其中 1 例任何其他检查都发现不了**：
      `sl85 Currumbin`(澳洲) 的 lat 取自 `sl60 南燕湾`(海南)、lon 取自 `sl49 西涌`(广东)
      —— 两个分量来自**不同**国内点，组合坐标唯一，坐标落在南海且有浪场数据
      → 为澳洲浪点静默产出"看起来很合理"的错误预报（最坏的一种失败，踩数据诚实红线）


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

- [~] 🔒 G1-a Canggu 坐标微调 —— **很可能已不必要**：R4.0 修好回退后该点用真实
      best_match 数据即可出报告（实测 3 天 ×24 点）。待代码上生产后复核 /status 再决定
- [ ] 🔒 G1-b **4 个国外/异常浪点的坐标串行修正** —— 生产 DynamoDB 写：
      `sl84 Kirra`(整套借 sl54) · `sl85 Currumbin`(lat 借 sl60 + lon 借 sl49，**在出错的预报**) ·
      `sl71 海螺湾`(lon 借 sl57，声称浙江却在内陆) · `sl97 SURFPARK`(北京人工浪池，
      应治理标记而非改坐标)。需权威坐标，不宜再推断
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
