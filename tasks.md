# Tasks — v4 三屏 ✅ 档落地（映射 `roadmap.md`）

> 每完成一项**立刻勾选**，并在 `docs/implementation-notes.md` 追加一行（含偏离理由）。
> 视觉规格 = `docs/design-v4-update1.html`（照它做，不另出 mockup）。
> 每轮开工先查停止文件（路径见 auto-nudge 消息）；存在即停。
> 🚫 = 本轮明确不做（🟡🟠🔴 档，碰即越界）。

## S0 · 起手

- [x] S0.1 查停止文件确认无停止信号
- [x] S0.2 分支 `feat/v4-three-screen-ui`（off master `0a4db78`）
- [x] S0.3 基线记录：pytest **329** · vue_spa **32/0**
- [x] S0.4 基准图沿用上轮已入库的 `docs/screenshots/43-design-v4-update1-3screens.png`（同一文件、0 报错状态）

## S1 · 设计令牌 + 夜读模式（地基，先做）

- [x] S1.1 `style.css` 从 5 行扩到 **29 个令牌**：11 个纸墨海（值逐字取自原型 `.dirA`）
      + 6 个状态色（本 App 独有：/status、直播、角标、校验）+ 12 个图表色（取自原型 `T()`）
      + 衬线字族/圆角/阴影 + 4 个纸感原语类（paper-title/num/sect/card）
- [x] S1.2 夜读模式：`body.night` 只覆盖变量（不碰任何组件规则）+ 顶部 🌙 开关（🌙/☀️ 互切）
      + localStorage `sf_night_v1`（沿用单 HTML 版键名，老用户偏好不丢）+ **无偏好时跟随系统深色**
- [x] S1.3 令牌化 **126 处**硬编码色：四页 69 + 三组件 19 + App.vue 全清 + `charts.js` **51 处**
      （图表原本写死 sky/emerald/amber，夜读必露馅；改取 `--ch-*` 变量，SVG 内联可继承）
      现全前端硬编码色只剩 `LiveCam` 的 `#000`（视频信箱底，两态都该黑，已注明）
- [x] S1.4 验收：日/夜双态截图 `45-s1-tokens-{day,night}.png`；`getComputedStyle` 抽查 3 处确认
      取变量值（夜态链接 `rgb(124,196,224)`=`--sea` 夜值、按钮底 `rgb(43,39,31)`=`--soft` 夜值）；
      E2E 加 **5 条**夜读断言（开关/日态/挂类/夜态/刷新持久化）→ **32→37 全绿**；
      pytest **329 不变**（印证后端零改动围栏）

## S2 · 首页（原型①）

- [x] S2.1 verdict 大标题 + 报头 `浪报 SURF DAILY · <GMT+8 日期>`（日期用 Intl+Asia/Shanghai，禁 UTC 推星期）
- [x] S2.2 覆盖计数 `fresh/total` + degraded 时附「部分点非当日新鲜，已排除」
- [x] S2.3 **本周走势 sparkline**：新增 `charts.sparkline(days)`，折线 + 峰值放大标注 +
      SVG 原生 `<title>` 提示 + `aria-label`（Vue 版无 tooltip 机制，不为此新引入一套）；
      色走 `--ch-*` 令牌，夜读自动跟随。数据靠**渐进增强**取（verdict 先出，走势后到，不阻塞首屏）
- [x] S2.4 校准戳 + 「先验证过去，再相信未来 → 数据健康」链到 `/status`
- [x] 🚫 已按围栏跳过并加 E2E 反向断言（页面不得出现「今日注意」「现场众报」「车程」）
- [x] S2.5 验收：对**生产真数据**截图（本地服新包 + `/api` 转发到生产只读 GET，
      因本地无 S3 缓存桶）→ `46-s2-home-real.png`；走势实测 6 点、峰值周一 8.65 且唯一放大；
      E2E +8 条首页断言 → **37→45 全绿**；pytest 329 不变

## S3 · 详情页 · 小白模式（原型②）

- [x] S3.1 一屏答案改纸感排版（日卡加边框，与令牌统一）
- [x] S3.2 **倒计时**：新建 `src/countdown.js` 纯函数模块（无 DOM/无 I/O，便于假时钟钉边界）。
      取 `day.windows[0]` 的数字小时对而非解析 `window` 字符串（更稳）；GMT+8 口径自算不依赖运行环境时区；
      秒级 tick；≥48h 改「N天 M小时」（实测最佳日常在数天后，原样会显示「114小时 18分 9秒」）
- [x] S3.3 三态 + **双侧边界钉死**（Playwright 假时钟冻结时间，7 例）：
      起点前1秒→before · **起点整→during** · 终点前1秒→during · **终点整→after** ·
      当日深夜→after · 前一天(该日属未来)→before · 后一天(该日已过)→after。
      主 E2E 并入 2 条边界例（起点整/终点整）
- [x] S3.4 **通勤倒推**：`departure()` 纯函数（窗口起点 − 车程 − 收拾装备 15min）；
      ± 可调并存 `sf_commute_v1`；早于零点会标「前一天」；仅小白模式显示（原型②专属）
- [x] S3.5 行动建议沿用既有 `.plan`（与 novice 同文时不重复渲染的逻辑保留）
- [x] 🚫 已按围栏跳过（水温缺 `sst`、首光缺 `sunrise` 属 🟡；报备 🟠；设施 🔴）
- [x] S3.6 验收：生产真数据截图 `47-s3-novice-real.png`（倒计时「4天 18小时」、
      通勤 17:00 出门 → 18:00 下水）；E2E **45→51 全绿**；pytest 329 不变

## S4 · 详情页 · 高手模式（原型③）

- [x] S4.1 五维 chips 与原型③一致（原型也用 chips，无需改结构）；图表色 S1 已全部令牌化，夜读自动跟随
- [x] S4.2 **风向罗盘**：`charts.compass(d)`。扇区＝`SPOT_FACING`（原型写死 157 只因单点 demo，
      生产按 `setFacing(report.spotFacingDeg)` 走）；三支箭＝06/12/18 时 `wdeg`；
      缺某时刻就不画那支（不插值）；一支都画不出则整个罗盘不渲染；扇区色新增令牌 `--ch-facearc`（逐字取原型 `T().face` 日/夜值）
- [x] S4.3 判定全走 `windKind`（罗盘内**零**阈值代码）。断言用 facing 独立重算逐支箭比对：
      337°→off(diff180) · 247°→cross(diff90) · 157°→on(diff0)。晨风结论也复用 `windKind`。
      🔍 **顺带查实**：`spotFacingDeg` 来自 `config/thresholds.yaml` 的**全站单一常量 157°**
      （后端风向评分同源），注册表另有逐点 `facing`（110/135/157/160）但 `facing_calibrated` **全为 false**
      且引擎未采用 → **前端不擅自换源**（会与后端「侧岸(ENE)」判定分叉，正是本条要防的漂移），
      改为**诚实标注**：度数加「＊分析口径，未逐点校准（目录另记该点约 N°，引擎暂未采用）」
- [x] S4.4 小课堂/昨日回看沿用既有块，配色随 S1 令牌切换（昨日回看的 `predict.height` 已接单位换算）
- [x] S4.5 **m/ft 切换**：新建 `src/units.js` 作单一真源（`unit` ref + `fmtH`/`hv`/`convertHeights`）。
      放 Vue `ref` 是为了让 charts.js 里读它的图表 computed **自动重绘**，不必给每个图表函数加参数。
      覆盖：浪高轴刻度 · 柱顶数字 · tooltip（浪高/涌高）· 昨日回看 `predict.height`。1m=3.281ft（取原型 `mLab` 口径）。
      `convertHeights` 只用于**已核实语义是高度**的字段，正则带前后守卫（避开 km/mm/m/s/min）——
      绝不全局套后端文案。按钮仅高手模式（原型③报头位），存 `sf_unit_v1`
- [x] 🚫 已按围栏跳过（DNA/溯源/季节志均无数据源）
- [x] S4.6 验收：真数据截图 `48-s4-expert-day.png` / `48-s4-expert-night-ft.png`（夜读＋英尺同时生效）；
      E2E **51→61 全绿**；pytest 329 不变

## S5 · 收口

- [ ] S5.1 `pytest -q` 不倒退（基线 329；**后端零改动，数字应不变**）
- [ ] S5.2 `vue_spa.mjs` 全绿 + 0 JS 报错，且**扩断言覆盖本轮全部新块**
      （走势 / 倒计时 / 通勤倒推 / 罗盘 / 单位切换 / 夜读持久化）
- [ ] S5.3 三屏截图与原型逐屏对照，贴进 PR
- [ ] S5.4 **新用户零上下文可用性评审**（独立子代理，无本轮上下文）：可发现性 / 措辞黑话 /
      能否自解释；发现折回代码后**重截图**
- [ ] S5.5 文档回写：`implementation-notes.md` 逐阶段 + `HANDOFF-to-kiro.md` §7
- [ ] S5.6 开 PR（不合并，🔒 G4）+ 整理待办清单 + 创建停止文件并汇报

## 🔒 硬门（loop 不执行，只整理）

- [ ] 🔒 本轮 UI 上生产（build → rollback 切版 → canary → smoke → tag → CHANGELOG）
- [ ] 🔒 合并本轮 PR 到 master

## 下轮候选（本轮明确不做）

- [ ] 🟡 后端补 `sunrise`/`sunset`/`sst`/`moonPhase`（引擎已有值、`render._day_to_dict` 未透出）
      → 解锁首光标记 / 水温穿着 / 潮历月相
- [ ] 🟠 现场众报投票 · 入水报备（各需新表 + 端点 + IAM，见 workspace lesson）
- [ ] 🟠 多浪点横评（批量取多点 report 或扩 `/api/recommend`）
- [ ] 🔴 今日注意告警 · 浪点设施 · 浪点 DNA · 涌浪溯源 · 季节志 —— **在有真实数据源之前不做**

## 已完成（上轮，勿重做）

- [x] v0.4.0 上生产（数据健康收口 R1-R4：空报告判定 / `/status` 自查 / 坐标解析 / 回退死代码）
- [x] sl84/sl85/sl71/sl97 标 `pending` 移出推荐池；澳洲两点权威坐标已查到待写
- [x] `design-v4-update1.html` 三屏收敛版收干净（0 JS 报错）+ 索引页两版并列对比（PR #43）
