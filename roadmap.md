# Roadmap — surf-forecast UI 交互布局持续优化

依赖链：U0(基线+摸底) → U1..Un(UI 优化批次, 每轮1-2项+配套功能迭代) → V(E2E 全绿) → W(截图) → X(3 文档) → Y(收尾/README) → [可选] Z(部署, 停下等确认)

## U0 — 基线 + 摸底
pytest 145 + E2E 基线确认；codelens/grep 摸清当前 UI 结构与接入点（TAB_OF/showTab/showLiveView/renderCatalog/renderSpotFav/render()）。

## U1..Un — UI 优化批次（每轮单个最高杠杆）
从 north_star「优化方向」挑选，例如：
- 目录卡片布局与评分排序 / 空态提示
- 加载态骨架屏(catalog/live/cams)
- tab & 子视图记忆(localStorage)
- 深色模式切换(持久化)
- 可达性(aria/键盘/焦点)
- 目录卡片直接收藏 + 地图按评分着色
- 移动端触控/滚动优化
每项：grep 确认 → 实现 → node --check → E2E 断言 → pytest 子集不倒退。

## V — E2E 全绿
`web/e2e/new_features.mjs` 扩断言覆盖所有新交互；全绿 + 0 JS 报错（排除资源404/直播流）。

## W — headless Chrome 截图
`web/e2e/shots.mjs` 扩截新界面 → `docs/screenshots/*.png`。

## X — 三份中文文档
功能介绍 / 交互操作指南 / 教学教程（引用截图，含交互流程与代码地图）。

## Y — 收尾
README 更新 + 最终 pytest + E2E 复核 + 验收结论。

## Z — 部署（可选, 高风险）
`AWS_PROFILE=oversea1 ./deploy.sh test→frontend→smoke` + CloudFront 复核。**不在 loop 内自动执行**——到此停下发 blocker 等人工确认。
