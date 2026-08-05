# Tasks — 映射 `roadmap.md`（事实来源：`docs/HANDOFF-to-kiro.md` §4）

> 每完成一项就勾选并在 `docs/implementation-notes.md` 追加一行。
> 🔒 标记 = 生产写操作，须人工确认后才执行。

## H0 · 交接收口

- [x] H0.1 合并 PR #37（merge commit `7e9f481`，保留 12 提交以便 tag 锚定）
- [x] H0.2 补 git tag v0.3.0(`0372fd7`) / v0.3.1(`b1f60c1`) / v0.3.2(`ef0bfd6`) / v0.3.3(`6c97860`) 并推送
- [x] H0.3 修 `deploy.sh` smoke 过时 401 断言 → 公开面 200×4 + 合规红线 cams 匿名 401（对生产实跑全绿）
- [x] H0.4 goal 三件套改为以交接文档为唯一事实来源
- [x] H0.5 CHANGELOG 补记：tag 补齐一行 + 标注 v0.3.0 条目原记 commit `8415a7b` 有误
      （其树 VERSION=0.2.1，系从脏工作树构建时的 HEAD；正确锚点为 `0372fd7`）

## H1 · 遗留清理

- [x] H1.1 sl75/sl76 坐标损坏修复（**已闭环，生产 60/60**）
  - [x] 根因定位：源快照两点 `lat=110.363232`（>90 非法，实为经度值），Open-Meteo 返回
        `Latitude must be in range of -90 to 90°`；58 点中恰这 2 点异常 → 非上游格点缺数据
  - [x] 修正坐标验证：按同 beach_group 兄弟点取值，与兄弟点真实坐标落在同一 Open-Meteo 格点
  - [x] 代码护栏：导入路径补 `sm.validate_coord`，非法坐标 → 隔离（`refresh_enabled=False`
        + `op_status=pending` + `coord_invalid`）而非静默入池；+5 单测（`tests/test_coord_guard.py`）
  - [x] 生产数据修正：sl75 `18.652,110.279` / sl76 `18.532,110.112`，同步重算 `dedup_key`，
        加 `coord_source` 标注推断来源；旧值备份 `docs/ops-backup/`；全表 4dp 碰撞检查通过
  - [x] 验证：`refresh_cli retry` → manifest **60/60 · failed=[]**；两点详情报告 6 日数据正常
- [ ] H1.2 配置 `SF_TEST_ACCESS_KEY`（🔒 改 task def env），E2E 带 `X-Test-Access` 头访问测试点
- [ ] H1.3 重建测试账号 `tester@surf.local` 并把凭据记到安全位置（不入库、不进仓库）
- [ ] H1.4 **sl82 Canggu 产出空报告**（2026-08-05 新发现）：坐标正确（-8.661,115.133 = 巴厘岛），
      但 WAM025 在格点 `-8.75/115.25` 返回 48 时点**全空** → 报告 `days: 0`。
      **这才是真正的"上游格点无数据"**。已探明邻近格点 `-8.75/115.0` 有完整数据（1.74m），
      把经度微调到 ≈`115.05` 即可落入可用格点。
      连带暴露契约洞：**manifest 把"写出了 latest.json"算作 succeeded，即使 `days=0`**
      → 60/60 绿但该点实际不可用（`coverage` 里体现为 pool 37 / fresh 36）。
      建议：刷新成功判定加 `days > 0`，否则计入 failed。
- [ ] H1.5 **注册表存在 3 组重复坐标**（4dp 相同）：`sl49/sl93`、`sl54/sl84`、`sl2/sl58`。
      `find_registry_by_coord` 取首个匹配 → 坐标→slug 解析有歧义，同族于 v0.3.2 那个缓存 bug。
      另注 `sl84 Kirra`（澳洲）坐标为 `22.60,114.91`（广东境内）——疑与 `sl54` 数据串行。


## H2 · 设计方向落地（阻塞：等用户拍板）

- [ ] H2.0 **用户从 `docs/design-directions.html` 的 v4~v7 中选定一版**（阻塞项，非技术）
- [ ] H2.1 把选定版功能集实施进 `web/frontend`（原型含交互逻辑与简化算法可参考）
- [ ] H2.2 新增/更新 `web/e2e/vue_spa.mjs` 断言覆盖新功能，跑到全绿 + 0 JS 报错
- [ ] H2.3 🔒 发版上线（build → rollback 切版 → canary → smoke → tag → CHANGELOG）

## H3 · 二期会员化（未开工）

- [ ] H3.1 微信扫码登录（后端 501 占位路由实装）
- [ ] H3.2 启用 `member_lock` 开关（须可无损回退到今日全公开行为）
- [ ] H3.3 直播从"测试账号解锁"切到会员制（cams 合规门不得放宽）
