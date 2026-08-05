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
