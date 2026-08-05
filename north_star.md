# North Star — 以交接文档为唯一事实来源

> **权威入口：[`docs/HANDOFF-to-kiro.md`](docs/HANDOFF-to-kiro.md)**（2026-08-05 交接）。
> 本文件不再复述现状/时间线/运维知识——那些只在交接文档里维护一份，避免两处漂移。
> 本文件只回答三件事：**当前目标是什么 · 什么不可妥协 · 下一步在哪里看**。
>
> 历史：本文件在 2026-07-27 曾是「甲·忠实整体重建（Vite+Vue3）」的作战文档，该目标已于
> v0.2.0~v0.2.1 完成上线；R2 数据健康与 v0.3.x 于 2026-07-28 完成并已合入 master
> （PR #37，tag v0.3.0~v0.3.3）。旧内容已归档到 git 历史，不在此保留。

## 一句话目标（当前）

生产 **v0.3.3** 已稳定运行、数据管线无人值守一周；下一阶段的目标是
**在用户从 `docs/design-directions.html`（v4~v7 四版原型）中拍板一版之后，把该版功能集实施进
`web/frontend`**——在此之前不做大改，只清遗留、守数据诚实。

**拍板前的默认动作**：只做遗留清理与稳定性工作（见 `tasks.md`），不新增产品面。

## 不可妥协（红线，任何目标都不得违反）

1. **数据诚实**：陈旧/缺失一律显式降级（`degraded` + `fresh/total`），绝不用旧分冒充当日分。
2. **新鲜性唯一裁判 = 当日 `manifest.succeeded`**；刷新全失败也会落 manifest（try/finally），
   `/status` 停在昨天 ⇒ 刷新任务根本没跑，先查 EventBridge/CloudTrail。
3. **taskdef 永远用 family 级 ARN**：钉 revision 会在下次发版后让 EventBridge 静默 AccessDenied
   （07-27/28 空首页事故根因）。scheduler TF 模块已改，别改回去。
4. **合规**：`/api/cams` 直播源为逆向所得（研究用途），必须保持登录后可取，**不对匿名公开**；
   `deploy.sh smoke` 已把这条钉成断言。
5. **冷点炸弹**：公开「可见性」绝不耦合成本/刷新开关；冷点回收只回收 `source=="user"` 自建点。
6. **生产写操作需人工确认**：真部署 / 回滚 / terraform apply / 改生产数据，一律先说明再执行。
7. **单驱动**：同一时间只有一个驱动器在改这个仓库（loop 或人，不并行）。

## 下一步看哪里

| 想知道 | 看 |
|--------|-----|
| 现状 / 时间线 / 运维血泪 / 文档地图 | `docs/HANDOFF-to-kiro.md`（先读这个） |
| 待办与优先级 | `tasks.md`（本目录，映射交接文档 §4） |
| 阶段划分与验收 | `roadmap.md`（本目录） |
| 逐日进度与偏离记录 | `docs/implementation-notes.md` |
| 决策依据（18 项已确认决策） | `docs/Fable5迭代建议.md` / `-R2.md` |
| 待选设计原型 | `docs/design-directions.html` → v4~v7 |
| 发版审计链 | `CHANGELOG.md` + git tag `v0.1.1`~`v0.3.3` |
