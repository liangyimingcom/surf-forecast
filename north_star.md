# North Star — 石老人 × surf-forecast 形态C整合（统一后端 + 58浪点 + 直播）

## 业务目标
按 `docs/石老人整合方案-formC.md`，用 skill `surf-forecast-codelens-dev` 方法论，把石老人「实时浪报」的产品形态（全国 58+ 浪点 + 真实摄像头直播 + 实时列表 + 社区）**整合进 surf-forecast 统一后端**：
- **预报一律由 surf-forecast 引擎自算**（Open-Meteo），弃用石老人预报值。
- **真实摄像头直播作为核心保留**（HLS，前端 hls.js 直连上游）。
- 复用 surf-forecast 深度评分/离岸风质/双周期/昨日回看作为增强。
- 部署前后 E2E、自动部署到生产（研究目的）、headless Chrome 截图 + 3 份文档。

## 方法论（surf-forecast × CodeLens）
每个功能：① codelens explain_code/find_symbol 摸底 → ② get_impact/find_affected_tests 算爆炸半径 → ③ find_route/search 守红线 → ④ 改 spec → ⑤ 实现 → ⑥ pytest 子集+Playwright E2E → ⑦ 截图 → ⑧ 文档。
CodeLens MCP: https://d1t9q5qxrql3xj.cloudfront.net/mcp/ package liangyimingcom/surf-forecast。

## 成功判据（DoD）
1. **58+ 浪点导入注册表**：坐标 + `live_src` + `facing`（默认估算+标"待校准"），写 DynamoDB 过 float→Decimal。
2. **预报统一引擎自算**：58 浪点全部走 `/api/report`，DATA CONTRACT 含 wdeg/双周期/数字字段。
3. **直播**：`/api/cams` 直播源目录（只读）+ 前端 hls.js 直播弹层，视频流前端直连上游（不经后端代理）。
4. **列表升级**：多浪点列表 + 地区筛选（广东/海南/福建/广西/浙江/山东/其他/国外）+ 引擎综合评分，复用已有收藏/搜索/地图。
5. **详情融合**：引擎评分/离岸风质/双周期/物理叙事 + 直播入口。
6. **昨日回看**接入多浪点。
7. **不改引擎内核**（physics/scoring/validate）；新增在 web 层 + 注册表导入 + `/api/cams`。
8. **测试**：pytest 从 118 增长且全绿；**部署前 + 部署后**都跑 Playwright E2E 全绿 + 0 JS 报错。
9. **自动部署**：`AWS_PROFILE=oversea1 ./deploy.sh test→frontend→smoke` + CloudFront 端到端复核。
10. **截图 + 3 文档**：功能介绍 / 交互操作指南 / 教学教程（引用截图）。

## 红线（务必遵守）
- 全程 GMT+8；DATA CONTRACT 每日含 wdeg，图表字段为数字；预报区与历史区日期互斥。
- DynamoDB 写入必过 float→Decimal（`src/web/db.py::_to_decimal`）；**不改引擎内核**。
- 受保护接口全 401；`/api/cams` 鉴权策略明确（直播建议会员/口令门禁，非完全公开）。
- ALB SG 永不含 0.0.0.0/0；`terraform apply` 禁 -auto-approve；纯 web+数据变更不跑 apply，需基建变更则停下发 blocker 等人工审批。
- slug 不可变作缓存键；附加式不破坏现有 MVP/生产；pytest 118 基线勿倒退。
- **合规**：石老人逆向部分仅研究用途；直播/坐标托管加访问控制 + 来源/研究免责；不复刻登录态/支付/社区写入，社区用示例。

## AWS
profile `oversea1`，账号 `153705321444`，region `ap-northeast-1`。CloudFront `d2hmhl7n8yga53`。

## 约束
- 本地开发 .venv python3.12；pytest 基线 118。前端=单 HTML `web/浪报MVP.html`。
- 本地起后端：`SF_FRONTEND=web/浪报MVP.html PYTHONPATH=src uvicorn web.app:app --host 127.0.0.1 --port 8848`。
- 停止循环：创建 `/Users/yiming/Downloads/all_the_meshclaw/surf-forecast/surf-forecast-kiro-v2/STOP_LOOP`。
- 方案详版：`docs/石老人整合方案-formC.md`。
