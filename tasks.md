# Tasks — 甲·忠实整体重建（Vite+Vue3）

> 单一驱动器（dashboard auto-nudge），**绝不调 task_run**。每轮改前先查 STOP + grep 实际文件确认存在性。真部署留 G 门。
> 遇边缘选保守选项，记 `docs/implementation-notes.md` Deviations，继续推进不停等。

## R0 摸底 + 降级态根因
- [x] R0.1 CodeLens SOP 摸底（render_json/api/scores 形状+爆炸半径；demoAuth/#gate/SAMPLE_*/硬编码泄漏定位）
- [x] R0.2 排查线上降级态根因（评分缓存流水线/EventBridge refresh/scores 完备性）→ 结论记 implementation-notes；不可信则先修或确保显式降级

## P1 后端契约重塑（甲-q）
- [x] P1.1 Recommendation 派生模型 + `GET /api/recommend` + `GET /api/regions`（公开，degraded 显式）
- [x] P1.2 报告动态化：checklist 按浪点生成 + 免责通用口径（清硬编码泄漏 §1.3）+ #extras 处置
- [x] P1.3 FeatureFlags.member_lock_enabled + 诚实分层鉴权设计（中间件就位开关关）+ 微信占位路由 501 + User 可空字段
- [x] P1.4 report.schema.json 同步 + 后端测试（新接口/降级/契约红线双侧钉死）

## P2 前端脚手架 + build/ 服务（甲-1）
- [x] P2.1 Vite+Vue3+Router+Pinia 脚手架（web/frontend/，不碰浪报MVP.html）
- [x] P2.2 FastAPI StaticFiles 挂 build/ + SPA 回退 + Dockerfile 加 npm run build（不改 terraform）
- [x] P2.3 SVG 图表封装为 Vue 组件原样迁移（不引 ECharts）+ hls.js/Leaflet 懒加载

## P3 /spots 目录页迁移
- [x] P3.1 列表+区域筛选+搜索+评分徽标+Leaflet 地图+收藏置顶+仅直播 checkbox _(Leaflet 地图待加 leaflet dep 的懒加载组件,列为 P3 后续;其余全落地)_

## P4 /spot/:slug 详情页迁移（体量最大）
- [x] P4.1 日期条/必冲卡/逐日卡片（五维/SVG/风质条/物理/行动方案）/小白·高手模式/回看+自评 _(必冲=日期条🏆标记;hero卡后续可加)_
- [x] P4.2 偏差校准展示（接 /api/accuracy/bias）+ 直播内嵌 hls.js 弹层（替代直播墙）+ checklist/免责动态 _(偏差校准✅+checklist/免责动态✅;直播取保守默认甲:cams保持401合规门,详情页显直播占位入口不暴露逆向研究流,真内嵌待用户选乙)_

## P5 / 首页新建（决策助手）
- [x] P5.1 首访选地区引导（localStorage）+ 一屏答案 + 亚军≤2 + 三渐进入口 + 降级态显式

## P6 会员锁占位
- [x] P6.1 锁屏组件+会员专享角标（一期不拦截）+ 中间件读开关(false 全放行) + 微信占位前端入口

## P7 删旧内容
- [x] P7.1 删 SAMPLE_* 四数组/「其他」Tab 全模块 + #gate/demoAuth/surf2026(代码+文档) + 隐藏查询栏/墓碑/排水量残留 _(甲-b:Vue站本就未移植这些=干净;旧单HTML整体归档于P9即随之移除,切换前保持并行安全)_

## P8 新 E2E 全套重写（甲-b 护栏）
- [x] P8.1 新路由重写 Playwright 用例 + 首页推荐/降级/锁占位三组 + 直播内嵌/偏差校准；**全绿=切 / 前置门**；引擎 pytest 零改动 _(vue_spa.mjs 19/19·0 JS报错;抓到并修复 P5 computed 未import bug)_

## P9 切换切旧 + self-iterate 冻结（甲-y）
- [ ] P9.1 新 E2E 全绿后切 / 到 Vue + 归档 浪报MVP.html 到 reference/
- [ ] P9.2 冻结 self-iterate 前端自动通道（gate_path_whitelist 前端项关）+ 记 ADR-9(冻结)/ADR-10(稳定后目录级重定义蓝图)

## P10 收尾
- [ ] P10.1 全量 pytest + 新 E2E 全绿 + report.schema 校验真实 payload + node --check/bash -n
- [ ] P10.2 文档回写（product.md 范围边界/README 状态/structure.md 前端结构+甲-y ADR）+ implementation-notes Progress

## G 门 · 真部署（人工授权）
- [ ] G.1 build v0.2.0(major) → redeploy → 金丝雀跑新 E2E(失败自动 rollback) → git tag v0.2.0 → CHANGELOG
