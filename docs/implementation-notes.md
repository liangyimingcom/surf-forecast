# Implementation Notes — 页面重规划（Fable5 计划）

计划文档：`docs/Fable5实施计划.html`（决策依据：`docs/Fable5迭代建议.md`）

**执行约定**：遇到边缘情况迫使偏离计划时，选**保守选项**（改动面最小、可逆性最高），
记录在下方 Deviations，然后继续推进，不停下等确认。每阶段完成在 Progress 记一行验收结果。

## Progress

| 日期 | 阶段 | 结果 |
|------|------|------|
| 2026-07-27 | 计划制定 | 八项决策确认，实施计划与本文件建立。未开工。 |
| 2026-07-27 | R0 摸底 | 结构注入点定位：#gate(462)/demoAuth(1003)/surf2026/SAMPLE_NEWS(1257)·CARPOOL(1308)·ADS(1333)/ANNOUNCEMENTS(2232) 待删；后端 catalog_scores(app.py:206) 需登录=伪门禁；recommend 数据源=评分缓存。 |
| 2026-07-27 | R0.2 降级态根因 | **每日刷新未覆盖全部浪点**：S3 latest.json 分布 07-27仅3点/07-25共47点(两天前)/6点无缓存(52<58)。首屏 recommend 现只能拿两天前分→冲浪预报失效。结论：刷新覆盖修复属 deployment-and-ops/EventBridge(真基建·G门)，与前端重建解耦；recommend 必须只排当日新鲜点+显式降级(degraded:bool 设计已预埋)。缓存管线本身健康(02:00 GMT+8 跑过)，问题在覆盖预算而非管线死。 |
| 2026-07-27 | P1 后端契约 | recommend/regions公开(只排新鲜点·诚实降级) + render_json动态checklist/disclaimer(清青岛硬编码) + flags会员锁+member_gate + 微信占位501 + User可空字段 + report.schema同步。pytest→264。 |
| 2026-07-27 | P2 脚手架+build | Vite+Vue3+Router+Pinia(web/frontend) + 后端SF_SPA_DIST门控服build/+SPA回退 + Dockerfile Node stage + charts.js忠实移植+ChartBox.vue(零依赖SVG)。 |
| 2026-07-27 | P3 目录页 | SpotsPage(区域/搜索/评分徽标/收藏/仅直播) + catalog/scores改公开(Fable5§2.2)。Leaflet地图待补。 |
| 2026-07-27 | P4 详情页 | report/history改member_gate分层 + SpotPage(日期条/日卡五维/ChartBox三图/物理/行动/小白高手模式/回看自评/偏差校准) + 直播占位(守cams合规红线,不暴露逆向流)。 |
| 2026-07-27 | P5 首页 | HomePage决策助手(首访引导+一屏答案+亚军≤2+三渐进入口+降级态显式)。 |
| 2026-07-27 | P6 会员锁占位 | App loadFlags + LockBadge(就位开关控,一期隐藏) + 微信占位弹层。真拦截在后端member_gate。 |
| 2026-07-27 | P7/P8 | Vue站干净(旧HTML P9兜底/归档) + 新E2E vue_spa.mjs 19/19(抓修P5 computed未import bug)=切/前置门。 |
| 2026-07-27 | P9 切换+冻结 | Dockerfile默认服Vue(SF_SPA_DIST,单HTML兜底) + self-iterate冻结ADR-9/稳定后重定义ADR-10。 |
| 2026-07-27 | P10 收尾 | pytest 267 · Vue E2E 19/0 · 冻结单HTML E2E 50/0(双前端并存) · 文档回写。剩 G门真部署 v0.2.0。 |
| 2026-07-28 | R2·P0 根因确认 | **真根因 = IAM 钉死 taskdef revision**：scheduler 角色只授权 `task-definition/surf-forecast-dev:5(:*)`，deploy.sh 发版 register 到 :15 后，EventBridge 02:00/14:00 RunTask 全部 AccessDenied（CloudTrail 07-27 14:00 与 07-28 02:00 两条铁证）→ 任务根本没跑，非限流/超时/预算。07-27 12:48 的 58 点覆盖是人工 RunTask。次因：refresh_cli exit-0-if-any-ok 掩盖部分失败；旧日志确有零星 `skipped: error(DataSourceError)`（sl75/sl76/sl53），限流是次要风险非主因。**已热修**：IAM policy 与两个 schedule 改 family 级 ARN（不钉 revision），TF scheduler 模块同步修复；已手动 RunTask 补今日全量。 |
| 2026-07-28 | R2·P1 治理 | governance.py（parse_op_status/beach_group 5组11点/is_test）+ seed/spots.create 接入 + tools/migrate_governance.py 生产迁移 61/61 行（名称后缀→op_status 字段，E2E石老人/流清河/测试点 is_test=true）。 |
| 2026-07-28 | R2·P2 manifest | refresh.py build_manifest/load_manifest/missing_from_manifest（retry 同日合并=补齐语义）+ refresh_cli 重写（main/retry 双模式，try/finally 必落 manifest）+ TF scheduler 加 06:00 retry 档（断链哨兵，manifest 缺失退化全量）。已 targeted apply，3 个 schedule 在线且全部 family 级 ARN。 |
| 2026-07-28 | R2·P3 过滤+状态页 | recommend 三道过滤（is_test→非open→beach_group 每滩留最高分；coverage 分母=可推荐池；manifest 在场时 succeeded 集为新鲜唯一裁判）+ /api/status + StatusPage.vue（/status 路由，首页降级横幅+页脚入口）+ SpotsPage op_status 徽标。catalog 默认滤测试点，X-Test-Access+SF_TEST_ACCESS_KEY 才可见。 |
| 2026-07-28 | R2·P4 验收 | pytest 288（+21：治理16/状态5）全绿；Vue E2E 22/22（+3 状态页）0 JS 错；修 test_recommend 钉死日期时间炸弹（改动态今日）。版本 0.2.1→0.3.0。 |
| 2026-07-28 | R2·G 生产部署验收 | v0.3.0 上线（taskdef:16 钉不可变 tag，`redeploy` 只滚 :15 旧镜像的坑→用 rollback 子命令正向切版）。**生产实测全绿**：目录 58 点无 E2E 泄漏、op_status 37open/14pending/7maintenance、5 组 beach_group、名称干净化+徽标；retry 刷新 258s 落首个 manifest（58/60，sl75/sl76 上游数据缺失）；首页广东一屏答案「周三·黄金海岸 8.8」+2 亚军；/status 页覆盖率+区域可用性+运行记录渲染正常；0 JS 错。遗留：sl75/76 持续失败原因待查；deploy.sh smoke 的 401 断言已过时（report 一期公开）。 |

## Deviations

> 格式：日期 / 触发情况 / 计划原文 / 实际做法（保守选项）/ 理由

- 2026-07-28 / R2·P0 根因与决策7前提不符 / 计划原文：「分片 Lambda 自链：每次只算一批(~10点)…每片都在 15min 内」（R2 §0.1 决策7，基于"载体是 Lambda、15min 超时是根因"的假设）/ 实际做法（保守）：**保留现有 ECS Fargate 单任务串行跑**，不迁 Lambda 不分片；只修真根因（IAM 钉死 revision → family 级 ARN）+ 落实 R2 的 manifest 契约与 06:00 补跑哨兵 / 理由：实测载体是 Fargate 无时长上限，58 点串行全量已被 07-27 人工触发验证可行；R2 §5 P0 明文要求"修复方案必须对症"，Lambda 分片属于对不存在的超时问题做的重构，改动面大于收益。决策9（逐点写+manifest）与决策10（补跑哨兵）不受影响，照做。
- 2026-07-27（补记，R2 §4 要求）/ 直播入口行为 / 计划原文（Fable5 一期决策8）：「一期全公开，锁仅占位：显示角标但不真拦截」/ 实际做法：详情页直播入口显示「登录后可看（二期开放）」，实际未提供播放 / 理由：cams 上游为逆向所得公开流（研究用途红线），不宜向匿名公众直接暴露播放地址；保守选择先占位。待二期会员制上线后经 member_gate 提供。

## v0.3.1 直播解锁（测试期，2026-07-28）

- 方案：**账号密码登录解锁**（用户选定）。/api/auth/me 公开登录态；App.vue 👤 = 真登录弹层（注明二期换微信后下线）；LiveCam.vue hls.js 动态 import，点播放才拉流，前端直连上游（合规红线不动：/api/cams 仍登录后可取）。
- 测试账号：tester@surf.local（密码在 /tmp/sf_test_account.txt，仅本机）。
- 顺手修复：匿名 /api/accuracy/bias 500（空 email 打 DynamoDB Key 条件 → 匿名直接返回 insufficient）。
- 生产实测：匿名见占位条→登录🟢→播放器→黄金海岸实时画面 1920×1080 播放中，0 JS 错误。

## 部署踩坑（R2 发布途中，已修）

- deploy.sh 多字节陷阱：`$ver`/`$stamp` 紧跟全角括号，非 UTF-8 locale 下 bash 把多字节字符并进变量名 → unbound variable。已全量加花括号（perl 一次性处理 4 处）。
- AMI 钉死失效：`ami-05bfa8036543cdeb3` 已随 AL2023 滚动下线 → InvalidAMIID。deploy.sh 改为 SSM 别名 `/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64` 动态解析。
- 构建机 region 漂移：AMI 变量在脚本头部展开，若外部 AWS_REGION 被覆盖为 us-east-1 会去错区起 EC2。构建时显式 `env AWS_REGION=ap-northeast-1`。

## Open Questions（不阻塞开工）

- Vue 3 vs React：计划采用 Vue 3，可逆，P2 开工前最终确认。
- 匿名态 `/api/accuracy/vote` 去重策略（设备指纹 vs 放任）：P1 实现时定，默认放任（保守）。
- 更新日志入口最终位置（页脚 vs 详情页底）：视觉稿阶段定，默认页脚（保守）。

## v0.3.2 切页提速（2026-07-28）

- 服务端：`bulk_latest` 61 点 S3 并发读 + 聚合接口 5min TTL（SF_AGG_TTL，键含 test_access 维度）。scores 2.25s→0.55s、recommend 3.2s→0.53s、status 1.85s→0.49s（余下 ~0.5s 为跨洋 RTT）。
- 前端：swr.js（stale-while-revalidate，内存+sessionStorage 5min）接入四页——切页秒出旧数据后台静默刷新，「加载中…」仅首次出现。实测回访 home 0.04s / spots 0.03s / detail 1.3s。
- **顺手揪出存量 bug**：DynamoDB `find_registry_by_coord` 用 round(入参,4) 与库中 6 位小数原值做精确相等 → seeded 点永远匹配不上 → slug 解析失败 → **详情页 S3 缓存从未命中**，每次实时调 Open-Meteo 现算（首访 5.9s 的真凶）。修为两侧同 round(4) 比较后 detail 首访 5.9s→1.3s，calibratedAt 回到刷新时刻（缓存命中实证）。
| 2026-08-05 | 交接 | 交接给 Kiro：docs/HANDOFF-to-kiro.md（现状/13个未push commit/遗留/运维知识/文档地图）。生产 v0.3.3 无人值守一周健康（主跑58/60·补跑哨兵正常·7区域推荐可用）。设计原型 v4-v7 待用户拍板。 |

## 2026-08-05 · R1 绿灯必须等于可用（数据健康收口 loop cycle 1）

- **R0** 起手：分支 `feat/data-health-r3`（off master `5a19026`），基线 pytest 293。
  修正 goal 里的停止信号路径（实际由 auto-nudge 指定为
  `surf-forecast/.stop-chat-3-1783779532`，非 `STOP_LOOP`）。
- **R1.1** `refresh.refresh_spots`：`writer.put` 前加 `days > 0` 判定。空报告 →
  `skipped: empty_report(upstream grid all-null)` + `continue`，**不覆盖上一版缓存**
  （沿用 validate 失败的 R5.4 策略，避免空报告冲掉好数据）。
- **R1.2** `status.build_status`：`failed` 保持 slug 列表（前端 `join('、')` 契约不破），
  新增 `failed_detail = {slug: 原因}`；`StatusPage.vue` 加 `.faillist` 渲染「slug — 原因」。
  原因本来就存在 manifest 里，是 status 层把它丢了。
- **R1.6（计划外，顺手修）** 测试污染：`/api/status` 走进程内 `_agg_cache`（TTL 300s），
  上个测试的响应会串给下个测试——同 fixture 数据时症状不可见，我加的新用例换了数据才暴露。
  `test_status_api.py` 加 autouse fixture 每例前后 `clear()`。
- **验证**：pytest **293 → 299**；vue_spa E2E **26 → 28**（新增两条断言直接验证失败原因渲染，
  canned status 改为带 `failed_detail` 的失败点，否则该 UI 等于没被测）。
- **预期副作用（正确行为）**：判定上生产后 `sl82 Canggu` 会从 succeeded 掉入 failed，
  `/status` 由 60/60 变 59/60 —— 真实状态浮出水面，不是回归。

## 2026-08-05 · R2 /status 自查静默故障（loop cycle 2）

- **探测器放 `governance.py`**（纯函数、无 I/O），供 `/api/status` 与后续 R4 巡检脚本共用：
  `coord_invalid_rows`（带 `coord_invalid` 标记的行）+ `coord_duplicate_groups`（4dp 同坐标分组，
  精度刻意对齐 `dedup_key` / `find_registry_by_coord` 的比较精度）。
- **关键判断：分级，否则是狼来了。** 拿生产注册表实跑发现 3 组重复里 **2 组是合理的**——
  `sl49 西涌-全景`/`sl93 西涌`、`sl2 狮子岛全景`/`sl58 狮子岛-右` 属同一 `beach_group`，
  是同片海滩的不同机位；只有 `sl54 虹海湾山海里`/`sl84 Kirra` 跨滩跨区（Kirra 在澳洲）
  = 真损坏。若一并报故障，站长很快就会无视这个区块。
  故 `severity: expected|suspect`，`/status` 只上报 suspect，合理组只给一个计数。
- **`data_issues` 探测集用 `visible_rows`**（已剔 `is_test`）——测试点不外泄公开接口（决策6）。
- **验证**：pytest **299 → 310**；vue_spa E2E **28 → 32**（canned status 补 `data_issues`，
  否则新 UI 分支不触发＝没被测）；前端 build 940ms。
- **生产实测（只读）**：`coord_invalid` 空（sl75/sl76 已修，符合预期——它是复发探测器），
  `coord_duplicates` suspect 恰为 `sl54/sl84`。

## 2026-08-05 · R3 坐标解析歧义防护（loop cycle 3）

- **风险重估（比预想严重）**：旧实现两个 store 都「取迭代顺序里的第一个」。
  InMemoryStore 至少受插入顺序决定，而 **DynamoDB scan 顺序不保证稳定** ——
  同一坐标可能今天解析成 sl54、明天解析成 sl84，S3 缓存键随之翻转，
  详情页可能显示**另一个浪点**的报告。不只是噪声，是正确性问题。
- **实现**：新增共享 `db.pick_registry_match(matches, lat, lon)` ——
  无匹配 → None；单命中 → 原样返回；多命中 → 按 slug 字典序取最小 + WARNING
  （文案列出全部候选与实际选中者，并指向 `/status` 的数据治理待办，与 R2 闭环）。
  两个 store 改为「收全部匹配 → 委托该函数」，语义一致由构造保证，不靠两处同步维护。
  精度常量提为 `db.COORD_NDIGITS = 4`，与 `dedup_key` / `coord_duplicate_groups` 对齐。
- **测试** `tests/test_coord_resolution.py` 10 例：含 caplog 验告警内容、
  反序输入同结果（旧实现会翻）、4dp 精度（6 位入库 4 位查得中，防 v0.3.2 复发）、
  **moto 真跑 DynamoDBStore 与 InMemoryStore 选中同一行**。
- **验证**：pytest **310 → 320**。真实重复组实跑告警：
  `坐标 (22.6017, 114.9073) 命中 2 个注册表浪点 ['sl54', 'sl84'] —— 存在解析歧义，
  按 slug 字典序取 sl54。请在 /status 的数据治理待办中核对该组坐标。`
- 注：这只是让行为**可预测且可见**；`sl84 Kirra` 坐标本身的修正属 🔒 G1（生产数据写）。

## 2026-08-05 · R4 偏离：先修回退死代码，而非写巡检脚本（loop cycle 4）

- **Deviation（记录理由）**：计划是写 `tools/probe_grid_health.py` 帮人找可用坐标。
  动手前按惯例核对引擎实际取数参数，发现 `fetch.py` 的「总浪高优先 WAM，缺则回退
  best_match」（需求 1.5）**是死代码**——`best` 请求的 hourly 只要了 swell/wind_wave/
  sea_level/sst，从没要 `wave_height/wave_direction/wave_period`，所以
  `_at(best_h,"wave_height",bi)` 恒为 None。
- **实测**：Canggu 坐标下 WAM025 格点 `-8.75/115.25` 全空，而 best_match 落在
  `-8.625/115.125`（更贴近实际位置）有完整数据 **1.36m / Tm 12.9s**。
  → 修回退比写脚本高一个数量级：**不写生产数据、不猜坐标**就能救回该点。
- **实现**：best 请求补三个回退字段；`_day_to_dict` 输出 `dataSource`（聚合逐点 `source`）；
  详情页在校准时间戳下提示「浪高取自 best_match 备用模型，Tp 仅主模型提供故留空不估算」。
  `source` 字段此前只在 models 定义、fetch 赋值、**下游从不消费** —— 换源却不可见，
  与 tech.md「可信度一等公民」冲突，故一并接通。
- **验证**：pytest **320 → 324**（含"两源皆空仍产不出点"——此时才是真正的上游无数据，
  由 R1 计入 failed；以及"WAM 有数据时不被 best 顶替"）；E2E 32/32；
  真实跑 Canggu → **3 天 × 24 点**，源标记 `best_match(fallback)`。
- **连带影响**：🔒 G1-a「Canggu 坐标微调」很可能不再必要（改标 `[~]`），
  待代码上生产后看 /status 复核。巡检脚本降级为非阻塞的 R4.1。

## 2026-08-05 · R4.1 巡检脚本 + R2.7 坐标分量串行探测（loop cycle 5）

- **R4.1** `tools/probe_grid_health.py`：stdlib、只读、判定与引擎一致（WAM→best_match 回退后
  仍无浪高才算 dead），对 dead 点搜邻近格点给坐标建议；`--source snapshot|store`、exit 2 可接 cron。
- **生产全量实跑（58 点）**：`ok_wam 55` · `ok_fallback 1`(Canggu，被 R4.0 救回) · `dead 2`：
  - `sl97 SURFPARK` 在**北京**(39.894,116.598)，人工浪池 → 海洋预报天生无意义，
    处置应是治理标记而非改坐标；
  - `sl71 海螺湾` 声称浙江、坐标在广西/广东内陆，经度与 `sl57` 完全相同 → 上游串行。
- **R2.7（顺着 dead 点查出来的新探测器）**：`coord_component_collisions` ——
  多点共享同一高精度(≥6 位小数) lat 或 lon，跨 `region_cn` 即 suspect。
  依据：高精度浮点巧合相同物理上不可能；而串行**可只发生在单个分量**，
  此时组合坐标唯一，R2 的 4dp 探测器完全看不见。
- **最恶劣一例（本轮最有价值的发现）**：`sl85 Currumbin`(澳洲) 的 lat 取自 `sl60 南燕湾`(海南)、
  lon 取自 `sl49 西涌`(广东)——两个分量来自不同国内点。坐标落在南海、有浪场数据，
  于是它一直在**为澳洲浪点静默产出"看起来很合理"的错误预报**。这不是缺数据，是确信地给错数据，
  踩数据诚实红线，而此前所有检查（坐标范围、4dp 重复、空报告）都发现不了。
- **验证**：pytest **324 → 329**（含"只串单分量时 4dp 探测器抓不到、本探测器必须抓到"的对照用例）；
  E2E 32/32；build 881ms。
- **连带**：🔒 G1-b 从「3 组重复去歧义」重写为「4 个浪点的坐标串行修正」，
  并注明 sl85 属**正在出错**、sl97 应治理标记而非改坐标；需权威坐标，不宜再推断。
