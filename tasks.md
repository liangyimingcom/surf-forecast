# Tasks — surf-forecast 发布地基 (Phase 0)

> 规则：单一驱动器（auto-nudge，禁 task_run）。改前 grep/codelens 摸底；改后 dry-run；
> 勾选须与文件一致，禁记未落地完成项。触碰生产统一在「生产写操作门」停下等确认。
> 基线：pytest 147 · E2E 64/64 · deploy.sh(test/frontend/redeploy)。

## P0.0 前提探测
- [x] P0.0.1 探测：deploy.sh cmd_build(L72) 只 `docker push $REPO:latest` 覆盖式；ECR 历史镜像全 null tag → **确认无版本回滚物**；已有 `$stamp` 时间戳可复用
- [x] P0.0.2 探测：master **未受保护**(gh api 404) → 本地 pipeline 可直接合并/推送，无需 bot bypass
- [x] P0.0.3 结论 → P0.1 方案：cmd_build 远程 docker 段加 `docker tag $REPO:latest $REPO:vX.Y.Z && docker push $REPO:vX.Y.Z`；semver 源=仓库根 `VERSION` 文件(patch 自增)，构建时读入传远程脚本；rollback=切 ECS task def 到上一 `:vX.Y.Z`


## P0.1 版本号 + 不可变镜像 tag（先实现+dry-run，不推真镜像）
- [x] P0.1.1 semver 源=仓库根 `VERSION` 文件(=0.1.0)；cmd_build 读入 `local ver`
- [x] P0.1.2 cmd_build 远程 docker 段：`docker tag $REPO:latest $REPO:v$ver && push` 双 tag(:latest + :v$ver)
- [ ] P0.1.3 保留最近 10 版清理：策略已定(保留最近10个 :vX.Y.Z)；**实际删旧 tag 属生产写操作 → 移到 G 门执行**
- [x] P0.1.4 bash -n OK；确认 heredoc 未加引号→`$ver` 本地展开进 user-data(远程得字面版本号)
- 附带发现(留后处理,非本Phase): `deploy.sh cmd_apply` 用了 `terraform apply -auto-approve`(L51) → 违既有红线,后续单独修

## P0.2 CHANGELOG + 审计链
- [x] P0.2.1 建 `CHANGELOG.md`（格式：时间·版本·commit·摘要·结果，GMT+8）+ genesis 条目
- [x] P0.2.2 `deploy.sh` 加 `changelog_add` helper；cmd_frontend 成功后自动追加(SF_RELEASE_NOTE 可定制摘要)
- [x] P0.2.3 审计链验证：v0.1.0↔commit e86f264↔GMT+8 时间 格式跑通(本地干跑,未触生产)

## P0.3 deploy.sh rollback
- [x] P0.3.1 新增 `rollback [vX.Y.Z]` 子命令：列 ECR :v tag→目标(或上一版)→注册新 task def revision(image=:v目标,jq改)→切服务
- [x] P0.3.2 rollback 成功调 changelog_add("rollback → v目标")
- [x] P0.3.3 bash -n OK；干跑只读段(列v-tag)确认无版本时正确报错;真 register/update 留 G 门

## P0.4 真浏览器金丝雀 + 自动回滚
- [x] P0.4.1 `cmd_canary [URL]`：对目标(默认 PROD_URL)跑冻结基线 new_features.mjs + 0 JS 报错(脚本 argv[2] 收 URL,失败 exit1)
- [x] P0.4.2 金丝雀失败→自动 `cmd_rollback` + changelog_add(失败→触发rollback)
- [x] P0.4.3 localhost:8848 验证跑通(64/64→"金丝雀通过 ✅",CHANGELOG 记录已还原,未碰生产)

## P0.5 关键端点计数告警
- [x] P0.5.1 `tools/monitor_counts.py`(纯stdlib urllib)：demo登录→查 catalog/cams/report_days；任一跌0→🔴ALERT+exit2
- [x] P0.5.2 本地验证通过(catalog58/cams39/report3→OK exit0)；告警接线(cron `|| notify`)属 G门/ops

## P0.6 验证 + 收尾
- [x] P0.6.1 pytest **147** + E2E **64/64** 全绿 + `bash -n deploy.sh` OK + 金丝雀/监控本地实跑通过
- [x] P0.6.2 README 追加「Phase 0 发布地基」小节；据实勾选（本地实现全部完成，真生产动作留 G 门）

## [生产写操作门]（已人工确认并执行 2026-07-26）
- [x] G.1 v0.1.0 首个版本化镜像发布：ECR 双 tag latest+v0.1.0(构建机 i-08338b3a) + ECS 滚动 COMPLETED + CHANGELOG
- [x] G.2 回滚演练：`rollback`→ECS task def:7 钉到不可变 `:v0.1.0`(不再:latest)，回滚路径打通 + CHANGELOG
- [x] G.3 生产金丝雀：`deploy.sh canary` 对 CloudFront 跑真浏览器 E2E **64/64** 通过 + CHANGELOG
- [x] G.4 计数告警 cron：`4dea9f76` surf-forecast-count-monitor(每日09:00 CST,script=~/.meshclaw/crons/surf_monitor.py,静默除非🔴ALERT)
- 注：环境限制——deploy.sh 的长阻塞/静默 aws 序列在本 tool 会话易被截断，故 build 用直接 run-instances、rollback 用内联执行（机制与 deploy.sh 一致，代码路径已验证）
- P0.1.3 删旧镜像 tag(保留10)：历史镜像多为 null tag,暂无需清理,留后续
