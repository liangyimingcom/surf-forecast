# Roadmap — 数据健康收口 R0~R5

> 目标与边界见 `north_star.md`；复选框见 `tasks.md`；事实来源 `docs/HANDOFF-to-kiro.md`。
> **顺序执行**，每阶段自带验收。资源紧张时跑定向测试，收口阶段(R5)才跑全量。

## R0 · 起手（每轮第一件事）

1. `ls STOP_LOOP` —— 存在就立刻停。
2. 确认在 `master` 且已 `pull`（本三件套随 PR #39 合入 master；若不在 master，先切过去）。
3. 建工作分支 `feat/data-health-r3`（若已存在则继续用），**全程不推 master**。
4. 读 `docs/HANDOFF-to-kiro.md` §5 运维知识 + §7 交接后更新，避免重踩已知坑。

**验收**：分支就位、工作树干净、`pytest -q` 基线绿（当前基线 **293 passed**）。

## R1 · 堵住「绿灯≠可用」（核心）

`refresh` 的成功判定目前只要写出 `latest.json` 就算 `succeeded`，即使报告 `days == 0`
（落点：`src/web/refresh.py` 的 `refresh_spots`，约 107-124 行——`writer.put` 后直接
`summary[slug] = "ok"`，从不看 `report["days"]`）。
改为：**产出报告必须 `days > 0` 才计 ok**，否则记 `skipped: empty_report(...)`，
并**沿用既有「不覆盖上一版缓存」策略**（同 validate 失败的处理，R5.4 原则），
别让空报告把上一版好数据冲掉。

注意：这会让 `sl82 Canggu` 立刻从 succeeded 掉到 failed —— **这是预期且正确的行为**
（真实状态浮出水面），不要为了让数字好看而回避。

**验收**：单测覆盖「写出但 days=0 → failed 且原因可读」「days>0 → succeeded」两侧边界；
`refresh` 相关测试全绿；`/api/status` 的 `failed` 能显示原因（不只是 slug 列表）。

## R2 · 让 `/status` 能自己发现三类静默故障

把下面三类暴露到 `/api/status`（前端 `/status` 页同步显示，措辞守数据诚实）：

1. **空报告**：`days == 0` 的点（R1 之后自然进 `failed`，但要能看出原因是"上游格点全空"）。
2. **坐标非法**：注册表里带 `coord_invalid` 标记的行（PR #38 的护栏会打这个标）。
3. **坐标重复**：4dp 相同坐标的分组（当前已知 3 组：`sl49/sl93`、`sl54/sl84`、`sl2/sl58`）。

**验收**：`/api/status` 新增字段有单测钉死形状；`web/e2e/vue_spa.mjs` 的状态页断言覆盖新区块；
零新增持久化（全部派生自 registry + manifest + 缓存，遵循 `status.py` 现有约定）。

## R3 · `find_registry_by_coord` 歧义防护

重复坐标时它静默取首个匹配（v0.3.2「缓存从未命中」bug 同族）。
改为：命中多行时**记日志告警并选取确定性的一行**（如 slug 字典序最小），使行为可预测、可观测；
两个 store 实现（`InMemoryStore` / `DynamoDBStore`）语义必须一致。

**验收**：单测覆盖「单命中」「多命中→确定性选取 + 告警」；两 store 行为一致性测试。

## R4 · 上游格点巡检脚本（只读，不写生产）

`tools/probe_grid_health.py`：遍历注册表坐标，探测上游是否返回全空；
对全空点搜索邻近格点（±0.05°/±0.1° 网格）给出**可用坐标建议**，输出报告到 stdout。
纯只读 + 标准库/现有依赖，**不得写 DynamoDB**（那是 🔒 G1）。

**验收**：本地对全量 registry 干跑通过；至少复现 `sl82 Canggu` 的诊断
（当前格点 `-8.75/115.25` 全空 → 建议 ≈`115.05` 落入 `-8.75/115.0`，实测 1.74m 有数据）。

## R5 · 收口

1. `pytest -q` 全量全绿（基线 293，只增不减）。
2. `vue_spa.mjs` E2E 全绿 + 0 JS 报错（起后端需 `SF_SEED_SPOTS=reference/data/shilaoren_spots.json`
   + `SF_SPA_DIST=web/frontend/dist`，先 `npm run build`；base URL 用位置参数传）。
3. 文档回写：`docs/implementation-notes.md` 追加逐日记录 + `docs/HANDOFF-to-kiro.md` §7 追加本轮结论
   + `tasks.md` 勾选。
4. 开 PR（不合并）。
5. 整理 **🔒 门项待人工确认清单**（Canggu 坐标微调、3 组重复坐标与 Kirra 串行的数据修正、
   `SF_TEST_ACCESS_KEY`、测试账号重建），写清每项的"做什么/为什么/怎么回退"。
6. 创建 `STOP_LOOP` 并汇报。

## 阶段之后（本轮不做，等门开）

- **H2 设计方向落地**：等用户从 `docs/design-directions.html` v4~v7 拍板（⛔ G5）。
- **H3 二期会员化**：微信扫码登录 → 启用 `member_lock` → 直播切会员制。
- 发版流程（每次上生产）：`deploy.sh build` → `rollback vX.Y.Z` 切版 → `canary` → `smoke`
  → `git tag -a` → `CHANGELOG` 追加审计行。（全在 🔒 G2，人来执行）
