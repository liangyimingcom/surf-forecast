# Roadmap — 交接后阶段划分（2026-08-05 起）

> 事实来源：[`docs/HANDOFF-to-kiro.md`](docs/HANDOFF-to-kiro.md)。本文件只排阶段与验收口径。
> 复选框在 `tasks.md`。生产写操作（部署/回滚/改生产数据）一律留人工确认门。

## H0 · 交接收口（已完成）

- 合并 PR #37（merge commit，保留 12 个版本提交以便 tag 锚定）→ master 含 v0.3.x 全部代码，
  **消除"从 master 构建会回退生产"的风险**。
- 补 git tag `v0.3.0`~`v0.3.3`（锚在各版本 VERSION 自洽提交上），审计链自 v0.1.1 起连续。
- 修 `deploy.sh smoke` 过时 401 断言 → 改为公开面 200 × 4 + **合规红线 `/api/cams` 匿名 401**。
- goal 三件套改为以交接文档为唯一事实来源（本次）。

**验收**：`gh pr view 37` = MERGED · `git tag -l 'v0.3.*'` = 4 个且已推 · `deploy.sh smoke <prod>` 全绿。

## H1 · 遗留清理（不需要用户拍板，可直接推进）

1. **sl75/sl76 坐标损坏**（已定位根因，待修）：源快照 `reference/data/shilaoren_spots.json` 中这两点
   `lat=110.363232`（>90 非法，实为经度值），Open-Meteo 直接返回
   `Latitude must be in range of -90 to 90°` → 每日刷新固定 2 点失败（58/60）。
   修法 = 按同 `beach_group` 兄弟点校正坐标 + **在注册表写入路径加范围校验**（让它不可能再静默复发）。
2. **X-Test-Access 密钥未配置**：`SF_TEST_ACCESS_KEY` 未设，E2E 测试点对所有人隐藏（含 E2E 自己）。
3. **测试账号凭据未入库**：`tester@surf.local` 密码只在原开发机 `/tmp`，需重建并记录到安全位置。

**验收**：`/api/status` 当日 `succeeded == expected`（60/60）· 刷新连续 2 天无 failed · pytest 不倒退。

## H2 · 设计方向落地（**阻塞在用户拍板**）

用户从 `docs/design-directions.html`（v4 最克制 → v7 最全，层层递进）中选定一版后，
把该版功能集实施进 `web/frontend`；原型内含全部交互逻辑与简化算法可直接参考。

**验收**：选定版功能集全落地 · `vue_spa.mjs` E2E 全绿且 0 JS 报错 · 契约门 `schema_check` 绿 ·
金丝雀通过后才切生产。

## H3 · 二期会员化（未开工，Fable5 决策）

微信扫码登录（后端占位路由已 501）→ 启用 `member_lock` 开关 → 直播从"测试账号解锁"切到会员制。

**验收**：一期公开面不回退（report/recommend/catalog/status 仍匿名 200）· cams 合规门不放宽 ·
锁开关关闭时行为与今日完全一致（可无损回退）。

## 发版流程（每次上生产都走）

`deploy.sh build`（版本号取自 `VERSION`，双 tag `:latest` + `:vX.Y.Z`）
→ `deploy.sh rollback vX.Y.Z`（**正向切版也用它**；`redeploy` 只滚 `:latest`，可能不是你要的）
→ `deploy.sh canary`（真浏览器 E2E，失败自动回滚）
→ `deploy.sh smoke`
→ `git tag -a vX.Y.Z` + `CHANGELOG.md` 追加审计行。
