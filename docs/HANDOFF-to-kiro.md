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
