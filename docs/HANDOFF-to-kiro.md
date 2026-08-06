# 交接文档 → Kiro（2026-08-05）

> 本文档是 Claude Code 会话（2026-07-27 ~ 08-05）工作成果的完整交接。
> 阅读顺序：本文档 → `docs/implementation-notes.md`（逐日记录）→ 两份 Fable5 建议文档（决策依据）。

---

## 1. 当前系统状态（交接时点实测）

- **生产站**：https://d2hmhl7n8yga53.cloudfront.net · 版本 **v0.3.3**（ECS taskdef 钉不可变 tag）
- **数据健康**（08-05 16:06 实测 /api/status）：
  - 每日刷新自 07-28 IAM 修复后**无人值守稳定运行一周**：02:00/14:00 主跑 58/60，06:00 补跑哨兵正常；
  - 七大区域推荐全部可用（广东 16/16 满覆盖）；「其他」区=测试桶归零属正确行为；
  - sl75（石梅湾九里）/sl76（富力湾全景）持续 DataSourceError = **已知遗留**（疑上游海洋格点无数据，见 §4）。
- **测试基线**：pytest **288** 全绿 · Vue E2E（web/e2e/vue_spa.mjs）**26/26** · 生产浏览器实测 0 JS 错误。
- **测试账号**：tester@surf.local（密码只在原开发机 /tmp/sf_test_account.txt，**未入库**；如丢失可
  `POST /api/auth/register` 重建，直播解锁用）。

## 2. 未合并代码（最重要的交接物）

分支 **`feat/r2-data-health`** 领先 master **12 个 commit，全部未 push**（push 权限未放行，需人工执行
`git push -u origin feat/r2-data-health` 后发 PR）：

```
6c97860 fix(spot): 行动建议与小白结论同文去重
0116131 feat(spot): 小白/高手大差异恢复 + 昨日回看边缘化 (v0.3.3)
7db5b01/ef0bfd6 fix: DynamoDB 坐标精度错位→S3报告缓存从未命中（详情页5.9s→1.3s真凶）
03a80d9 perf: 切页秒开(SWR会话缓存) + 聚合接口提速(bulk_latest并发+5min TTL) (v0.3.2)
1b5958d/b1f60c1 fix: 匿名bias 500 + docs
65c40df feat(live): 测试期账号登录解锁直播 (v0.3.1)
0372fd7 feat(R2): IAM根因修复+目录治理+manifest契约+/status (v0.3.0)
（另有本次交接 commit：设计原型 v4-v7 + CHANGELOG + 本文档）
```

⚠️ **生产镜像(v0.3.0-v0.3.3)已包含这些代码**（经 deploy.sh build 直接构建），但 **git 远程还没有**。
**第一优先级动作：push 该分支 → 发 PR → 合入 master**，否则下次有人从 master 构建会回退生产。

## 3. 本会话完成的工作（按时间线）

| 版本 | 内容 | 关键文件 |
|------|------|----------|
| 规划 | 盲点探测→8+10项决策→《Fable5迭代建议》×2 + 实施计划 | docs/Fable5迭代建议.md, -R2.md, Fable5实施计划.html |
| v0.3.0 | **P0根因**：scheduler IAM/调度钉死 taskdef:5→family级ARN（EventBridge AccessDenied=空首页真凶，CloudTrail实证）；目录治理三字段（op_status/beach_group/is_test，生产61行已迁移）；recommend三道过滤；manifest一致性契约+06:00补跑哨兵；/api/status+/status页 | src/web/governance.py, status.py, refresh.py, refresh_cli.py, tools/migrate_governance.py, iac/.../scheduler/main.tf |
| v0.3.1 | 直播测试期解锁：/api/auth/me + 登录弹层 + LiveCam.vue(hls.js动态import)；修匿名bias 500 | web/frontend/src/components/LiveCam.vue, App.vue, stores/auth.js |
| v0.3.2 | 提速：bulk_latest 61点S3并发 + 聚合接口5min TTL(SF_AGG_TTL)；前端swr.js四页接入（切页0ms）；**修坐标精度bug**（详情页缓存从未命中） | src/web/cache用法在app.py, web/frontend/src/swr.js, src/web/db.py |
| v0.3.3 | 小白=一句话+行动+"为什么"引导（无图表），高手=五维+图表+课堂全解；昨日回看折叠边缘化 | web/frontend/src/pages/SpotPage.vue |
| 原型 | 设计方向 v4-v7 四个独立可交互 HTML + 索引（**未选定，待用户拍板**） | docs/design-directions.html(索引), design-v4~v7.html |

## 4. 遗留事项（按优先级）

1. **push + PR + 合 master**（§2，防生产回退，机械操作）。
2. **sl75/sl76 上游数据缺失**：连续多日 DataSourceError。排查方向：用该两点坐标直接调 Open-Meteo marine API
   看是否返回空浪场；若是格点问题可微调坐标(±0.02°)或标记 op_status=pending。
3. **设计方向未拍板**：用户在 docs/design-v4~v7.html 四版中选择（层层递进，v4最克制/v7最全），
   选定后按该版功能集实施到 web/frontend（原型含全部交互逻辑与简化算法可参考）。
4. **deploy.sh smoke 的 401 断言已过时**（report 一期公开），跑 smoke 会误报，需改断言。
5. **二期待办**（Fable5 决策，未开工）：微信扫码登录（后端占位路由已 501）、member_lock 开关启用、
   直播从"测试账号解锁"切到会员制。
6. **X-Test-Access 密钥未配置**：SF_TEST_ACCESS_KEY 环境变量还没设，E2E 测试点当前对所有人隐藏
   （包括 E2E 自己）；配置后 E2E 需带头访问。

## 5. 关键运维知识（血泪教训，已固化但要知道为什么）

- **taskdef 永远用 family 级 ARN**：钉 revision 会在下次发版后让 EventBridge 静默 AccessDenied
  （07-27/28 空首页事故根因）。scheduler TF 模块已改，别改回去。
- **发版流程**：`deploy.sh build`（版本号来自 VERSION 文件，双 tag :latest+:vX.Y.Z）→
  `deploy.sh rollback vX.Y.Z`（正向切版也用它，redeploy 只滚 :latest 可能不是你想要的）。
- **deploy.sh 的坑（已修）**：多字节字符旁的 shell 变量必须 `${var}` 花括号；AMI 走 SSM 别名动态解析；
  构建时显式 `env AWS_REGION=ap-northeast-1`。
- **数据一致性**：recommend 新鲜性以 **manifest.succeeded 为唯一裁判**（当日）；刷新哪怕全失败也会
  落 manifest（try/finally）——/status 停在昨天=刷新任务根本没跑，先查 EventBridge/CloudTrail。
- **无推送告警**（用户决策）：/status 页是唯一故障发现渠道，站长应每日一瞥。
- **AWS**：profile=oversea1，业务区=ap-northeast-1（CloudTrail/日志/DynamoDB 全在这，别被 us-east-1 带偏）。
- **合规红线**：cams 直播源为逆向所得（研究用途），/api/cams 必须保持登录后可取，不对匿名公开。

## 6. 文档地图

| 文档 | 用途 |
|------|------|
| docs/implementation-notes.md | 逐日进度 + Deviations（偏离计划的记录，含理由）+ 踩坑 |
| docs/Fable5迭代建议.md / -R2.md | 两轮重构的决策依据（用户逐题确认过的 18 项决策） |
| docs/Fable5实施计划.html | R1 实施计划（已完成） |
| docs/design-directions.html → v4~v7 | 待选设计原型（索引页开始看） |
| CHANGELOG.md | 发版审计链（版本↔commit↔时间↔结果） |
| .kiro/specs/* | 原 spec 体系（引擎/web/校验/部署/浪点，仍有效） |

交接完毕。生产此刻健康，代码此刻领先远程 13 commit——**先 push，再做别的**。

---

## 7. 交接后更新（Kiro，2026-08-05 17:45 GMT+8）

> 原文保留不改；本节记录交接之后发生的变化与**对原文的更正**。

### 已闭环

- **§2 未合并代码 → 已合并**：分支已 push，**PR #37 合并 master**（merge commit `7e9f481`，
  保留 12 提交以便 tag 锚定）。原文"全部未 push / 你 review 后点 merge 即可"已过期，且当时 PR
  实为 `CONFLICTING`（master #36 Leaflet 与分支各自动过 `web/frontend/package.json`；
  分支侧为严格超集，取分支版=并集后解掉）。"从 master 构建会回退生产"的风险已消除。
- **审计链补齐**：git tag `v0.3.0`~`v0.3.3` 已打并推送。
  ⚠️ **更正 CHANGELOG**：v0.3.0 条目原记 commit `8415a7b` 有误——其树内 `VERSION=0.2.1`
  （`deploy.sh` 从脏工作树构建，`changelog_add` 记的是当时 HEAD，而 v0.3.0 提交 12:47 才产生）。
  正确锚点为 `0372fd7`，tag 已按此打。v0.3.1~v0.3.3 各行自洽。
- **§4.4 deploy.sh smoke 401 断言 → 已修**：改为公开面 200×4（report/recommend/catalog/status）
  + **合规红线 `/api/cams` 匿名必须 401**（保留一条真安全断言而非删除）。对生产实跑 6/6 绿。
- **§4.2 sl75/sl76 → 已修，根因与原文猜测不同**：**不是上游海洋格点无数据**，而是
  **源快照坐标损坏**——两点 `lat=110.363232`（>90 非法，实为经度值），58 点中恰这 2 点异常，
  Open-Meteo 直接返回 `Latitude must be in range of -90 to 90°`。
  真正的洞是**导入路径 `build_registry_rows` 绕过了用户 CRUD 必过的 `spots_model.validate_coord`**。
  处置：① 代码护栏（非法坐标→隔离出刷新池但保留目录可见，+5 单测）；
  ② 生产坐标按同 beach_group 兄弟点修正（sl75 `18.652,110.279` / sl76 `18.532,110.112`，
  重算 `dedup_key`，加 `coord_source` 标注推断来源，旧值备份 `docs/ops-backup/`）。
  验证：`refresh_cli retry` → manifest **60/60 · failed=[]**，两点详情报告 6 日数据正常。
- **goal 三件套**：`north_star.md` / `roadmap.md` / `tasks.md` 已重写为**以本文档为唯一事实来源**
  （旧内容是已完成的「甲·Vue 重建」，会误导后来者）。待办清单在 `tasks.md`（H0~H3）。

### 新发现（尚未修，已进 tasks.md）

- **sl82 Canggu 产出空报告**：坐标正确（-8.661,115.133 = 巴厘岛），但 WAM025 在格点
  `-8.75/115.25` 返回 48 时点**全空** → 报告 `days: 0`。**这才是真正的"上游格点无数据"**。
  已探明邻近格点 `-8.75/115.0` 数据完整（1.74m），经度微调到 ≈`115.05` 即可。
- **契约洞（连带暴露）**：manifest 把"写出了 latest.json"就算 `succeeded`，**即使 `days=0`**
  → 会出现 60/60 全绿但某点实际不可用（`coverage` 里才看得出 pool 37 / fresh 36）。
  建议刷新成功判定加 `days > 0`。
- **注册表 3 组重复坐标**（4dp 相同）：`sl49/sl93`、`sl54/sl84`、`sl2/sl58` →
  `find_registry_by_coord` 取首个匹配，坐标→slug 解析有歧义（同族于 v0.3.2 那个缓存 bug）。
  另注 `sl84 Kirra`（澳洲）坐标为 `22.60,114.91`（广东境内），疑与 `sl54` 数据串行。
- **`/api/status` 有 300s 聚合缓存**（`SF_AGG_TTL`，`_agg_cache`）：刚触发刷新后立刻看 `/status`
  会读到旧 manifest，**不是故障**，等一个 TTL 窗口即反映真值（排障时别被误导）。

### 数据健康收口 loop（2026-08-05 18:30~19:15，分支 `feat/data-health-r3`）

命题：**绿灯必须等于可用**。起因是修完 sl75/sl76 后刷新报 60/60 全绿，但 `coverage`
仍是 pool 37 / fresh 36 —— 有点在"成功"里其实不可用。

已做（代码在分支，未上生产）：

| 项 | 内容 |
|----|------|
| R1 | `refresh_spots` 加 `days > 0` 判定：产出空报告不再计 ok，记 `skipped: empty_report(...)` 且**不覆盖上一版缓存**（沿用 validate 失败策略）。失败原因经 `failed_detail` 贯通到 `/api/status` 与前端 |
| R2 | `/status` 自查两类坏数据：`coord_invalid`（导入护栏标记）+ 4dp 重复坐标。**重复按同滩/跨滩分级**——生产 3 组里 2 组是同一 `beach_group` 的多机位（合理），只 `sl54/sl84` 是真异常；不分级则 2/3 是误报，告警会被无视 |
| R3 | `find_registry_by_coord` 多命中不再取迭代首个（**DynamoDB scan 顺序不保证稳定** → 解析结果会在两次调用间漂移 → 缓存键翻转 → 详情页可能显示另一个浪点的报告）。改为共享 `db.pick_registry_match`：slug 字典序最小 + 告警，两 store 语义一致 |
| R4.0 | **修掉一个死代码 bug**：需求 1.5 的「浪高优先 WAM、缺则回退 best_match」从未生效——`best` 请求的 hourly 没要 `wave_height/direction/period`。修好后 `sl82 Canggu` 用真实 best_match 数据救回（3 天 ×24 点，1.36m / Tm 12.9s），**不需要改坐标** |
| R4.0b | 溯源可见：`dataSource` 输出到日卡，详情页提示「浪高取自 best_match 备用模型，Tp 留空不估算」。`source` 字段此前只定义+赋值、下游从不消费，静默换源与「可信度一等公民」冲突 |
| R4.1 | `tools/probe_grid_health.py`（stdlib、只读、可接 cron）。生产 58 点实跑：`ok_wam 55` · `ok_fallback 1` · `dead 2` |
| R2.7 | **坐标分量串行探测**（新一类）：多点共享同一高精度(≥6 位小数) lat 或 lon、跨区域即 suspect |

**本轮最重要的发现**：`sl85 Currumbin`（澳洲黄金海岸）的 lat 取自 `sl60 南燕湾`(海南)、
lon 取自 `sl49 西涌`(广东)——**两个分量来自不同的国内点**，组合坐标因而唯一。
该坐标落在南海且有完整浪场数据，所以它一直在**为澳洲浪点静默产出"看起来很合理"的
错误预报**。这不是缺数据，是确信地给错数据；此前的坐标范围校验、4dp 重复检测、
空报告判定三道全都发现不了。

**两个 dead 点性质不同，处置也不同**：
- `sl97 SURFPARK` 在**北京**(39.894,116.598)，人工浪池 → 海洋预报天生无意义，
  应做治理标记（移出海洋刷新池），**不是改坐标**；
- `sl71 海螺湾` 声称浙江、坐标在广西/广东内陆，经度与 `sl57` 完全相同 → 上游串行。

**上生产后的预期变化（正确行为，不是回归）**：`/status` 的 `failed` 会出现
`sl97`/`sl71`（原因 `empty_report`），60/60 变约 58/60。它们本来就不可用，
以前被算成绿的。Canggu 则会转为 `ok`（标 `dataSource=best_match(fallback)`）。

**验证**：pytest **293 → 329** · vue_spa E2E **26 → 32** · schema 契约门绿 · build 989ms。

**🔒 待人工确认（loop 未执行）**：见 `tasks.md` 末节——四个浪点的坐标串行修正
（`sl84`/`sl85`/`sl71` 需**权威**坐标，不宜再推断；`sl97` 应治理标记）、
`SF_TEST_ACCESS_KEY` 配置、本轮代码上生产、测试账号重建。

### v4 三屏 UI 落地 loop（2026-08-05 21:00 ~ 08-06，分支 `feat/v4-three-screen-ui`）

把 `docs/design-v4-update1.html`（三屏收敛版）的**「✅ 现成数据可直接做」**那一档落进
`web/frontend`，让线上从普通蓝白 SPA 变成晨报纸感三屏。**后端零改动**（pytest 全程 329 不变，
这个数字本身就是围栏的证据）。E2E `vue_spa.mjs` **32 → 61**。

| 阶段 | 落地物 |
|------|--------|
| S1 | `style.css` 5 行 → **29 + 12 个设计令牌**（纸墨海值逐字取原型）；夜读 `body.night` **只覆盖变量**、不碰组件规则；令牌化 126 处硬编码色（含 `charts.js` 51 处——不改它夜读一切换就露馅） |
| S2 | 晨报决策首页：报头 / verdict 大标题 / `fresh/total` 覆盖计数 / **本周走势 sparkline** / 校准戳链 `/status`。走势用**渐进增强**取数，不阻塞首屏 |
| S3 | 小白模式：**最佳窗口倒计时**（`src/countdown.js` 纯函数，三态双侧边界钉死）+ **通勤倒推**（窗口起点 − 车程 − 装备 15min，存 localStorage） |
| S4 | 高手模式：**风向罗盘**（`charts.compass`，判定全走 `windKind`，罗盘内零阈值代码）+ **m/ft 单位切换**（`src/units.js` 单一真源） |

**本轮抓到的 4 个真问题**（比 UI 本身值钱）：

1. 🔴 **SWR 键即契约** —— 首页用 `report|<slug>` 存裸 report，而 `SpotPage` 同键存
   `{ rep, hist, bias, hasLive }` 包装对象 → 首页先跑写入后，**详情页整页白**。
   已改独立键 `trend|<slug>`，并把「同键必须同形状」写进 `swr.js` 顶部。
2. 🔴 **浪点朝向是全站单一常量** —— `/api/report` 的 `spotFacingDeg` 对全国每个浪点都返回
   **157°**（源头 `config/thresholds.yaml: spot_facing_deg`，后端风向评分同源）。注册表另有
   逐点 `facing`（110/135/157/160）与 `facing_calibrated` 标记，但生产 58 点 **calibrated 全 false**
   且引擎未采用。离岸/向岸是一等参数，却按一个全国常量判定：黄金海岸目录记 135° vs 分析 157°，
   差 22°，够把 cross↔offshore 推翻。**本轮没偷偷换源**（前端改用目录值会与后端「侧岸(ENE)」
   文案分叉，且目录值本身也未校准），改为在罗盘上诚实标注
   「＊分析口径，未逐点校准（目录另记该点约 N°，引擎暂未采用）」。
3. 🟡 **倒计时可读性** —— 最佳日常在数天后，原样会显示「114小时 18分 9秒」。≥48h 改「4天 18小时」。
   这类问题断言测不出，只有看真数据截图才发现。
4. 🟡 **两个自引入视觉缺陷**（截图实测发现，非断言）：报头右侧链接被右上固定 🌙/👤 压住；
   走势峰值标注贴顶被卡片裁掉。→ 页面顶部内容需留 96px 右边距避让固定按钮。

**验收手法（后续沿用）**：本地无 S3 缓存桶 → 首页会显示「0/0 暂无新鲜评分」，是环境假象。
想用真数据验前端：本地 `SF_SPA_DIST=.../dist` 起 uvicorn + Playwright `page.route` 用 `fetch`
取生产响应再 `fulfill`（**不能** `route.continue({url})` 改写跨协议）。倒计时这类时间相关逻辑
用 `addInitScript` 冻结 `Date` 钉边界；注意 Playwright **后注册的 route 优先**，兜底 `**/api/**`
必须先注册，否则会盖掉所有具体 mock。

**🔒 留给用户**：本轮 UI 上生产；合并 PR；让引擎按逐点 `facing` 计算并真正校准朝向；
🟡 档后端补 `sunrise`/`sunset`/`sst`/`moonPhase`（引擎已有值、`render._day_to_dict` 未透出）
→ 可解锁首光标记 / 水温穿着 / 潮历月相。

#### v0.5.0 已上生产（2026-08-06 09:04 GMT+8）

PR #44 合并（`27a5279`）→ VERSION 0.5.0 → 镜像双 tag → taskdef **:23 → :24** → canary **66/0** → smoke 6/6。

**核对链条**（不是看到 200 就宣布成功）：ECR `v0.5.0` digest `sha256:9a4b3cab…` ↔ 运行中容器 digest
**逐字符相同**；生产 CSS 含 `--halo`/`--ch-facearc`（本轮最后一个提交才加的令牌）↔ 新前端确已换。

**两个排查陷阱，下次直接避开**：
1. **别用本地 dist 的 chunk hash 去猜生产资源路径** —— SPA 代码分割，页面文案在
   `HomePage-*.js`/`SpotPage-*.js`/`countdown-*.js` 里，入口 chunk 本来就没有；而且镜像内
   `npm install` 解析的依赖版本与本地锁定状态不同 → **同样的源码、不同的 chunk 名**
   （生产 `HomePage-BEyfHnSx` vs 本地 `Dme5WaQE`）。我照本地 hash 请求得到 404，一度误判成
   「线上服的是旧包」。正确做法：从生产入口 JS 里读真实分块名，或直接验 CSS 令牌。
2. **金丝雀失败会自动回滚** —— 先手动对生产跑一遍 `vue_spa.mjs`（无副作用）确认绿了，
   再执行 `deploy.sh canary`。否则脚手架问题会把一个健康版本回滚掉（v0.4.0 前踩过）。

**`deploy.sh` 的一个隐含前提**：它没有 CloudFront 失效步骤。当前分发 `DefaultTTL=0`/`MinTTL=0`
（实测首页 `X-Cache: Miss from cloudfront` 直接回源）所以无碍；**若将来给静态资源加长 TTL，
必须补 `create-invalidation`**，否则切版后会继续服旧 HTML。

**生产真数据实地验证了两条「缺值不编造」路径**（第一次在真缺数据的浪点上跑到）：
Canggu 走 best_match 备用模型 → 首页 chips 只有 2 个（无 `峰周期`，Tp 按约定留空不估算）；
罗盘只画 12/18 两支箭，06 时无风向数据就不画并明写「晨 06 时无风向数据，未作判定」。
