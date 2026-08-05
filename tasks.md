# Tasks — 映射 `roadmap.md`（事实来源：`docs/HANDOFF-to-kiro.md` §4）

> 每完成一项就勾选并在 `docs/implementation-notes.md` 追加一行。
> 🔒 标记 = 生产写操作，须人工确认后才执行。

## H0 · 交接收口

- [x] H0.1 合并 PR #37（merge commit `7e9f481`，保留 12 提交以便 tag 锚定）
- [x] H0.2 补 git tag v0.3.0(`0372fd7`) / v0.3.1(`b1f60c1`) / v0.3.2(`ef0bfd6`) / v0.3.3(`6c97860`) 并推送
- [x] H0.3 修 `deploy.sh` smoke 过时 401 断言 → 公开面 200×4 + 合规红线 cams 匿名 401（对生产实跑全绿）
- [x] H0.4 goal 三件套改为以交接文档为唯一事实来源
- [ ] H0.5 CHANGELOG 补记：tag 补齐一行 + 标注 v0.3.0 条目原记 commit `8415a7b` 有误
      （其树 VERSION=0.2.1，系从脏工作树构建时的 HEAD；正确锚点为 `0372fd7`）

## H1 · 遗留清理

- [ ] H1.1 sl75/sl76 坐标损坏修复
  - [x] 根因定位：源快照两点 `lat=110.363232`（>90 非法，实为经度值），Open-Meteo 返回
        `Latitude must be in range of -90 to 90°`；58 点中恰这 2 点异常 → 非上游格点缺数据
  - [x] 修正坐标验证：按同 beach_group 兄弟点取值，Open-Meteo 返回 24 个有效浪高点
        （sl75 石梅湾 ≈ `18.66,110.27`，兄弟 sl57/sl91；sl76 富力湾 ≈ `18.529,110.109`，兄弟 sl39）
  - [ ] 代码护栏：注册表写入路径加坐标范围校验（lat ∈ [-90,90] / lon ∈ [-180,180]），
        非法即拒绝并报错，杜绝静默复发 + 补单测
  - [ ] 🔒 生产数据修正：更新 DynamoDB 这两行的 lat/lon（先记录旧值以便回退）
  - [ ] 验证：触发一次刷新后 `/api/status` 当日 `succeeded == expected`（60/60）
- [ ] H1.2 配置 `SF_TEST_ACCESS_KEY`（🔒 改 task def env），E2E 带 `X-Test-Access` 头访问测试点
- [ ] H1.3 重建测试账号 `tester@surf.local` 并把凭据记到安全位置（不入库、不进仓库）

## H2 · 设计方向落地（阻塞：等用户拍板）

- [ ] H2.0 **用户从 `docs/design-directions.html` 的 v4~v7 中选定一版**（阻塞项，非技术）
- [ ] H2.1 把选定版功能集实施进 `web/frontend`（原型含交互逻辑与简化算法可参考）
- [ ] H2.2 新增/更新 `web/e2e/vue_spa.mjs` 断言覆盖新功能，跑到全绿 + 0 JS 报错
- [ ] H2.3 🔒 发版上线（build → rollback 切版 → canary → smoke → tag → CHANGELOG）

## H3 · 二期会员化（未开工）

- [ ] H3.1 微信扫码登录（后端 501 占位路由实装）
- [ ] H3.2 启用 `member_lock` 开关（须可无损回退到今日全公开行为）
- [ ] H3.3 直播从"测试账号解锁"切到会员制（cams 合规门不得放宽）
