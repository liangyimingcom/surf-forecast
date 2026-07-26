# North Star — surf-report-web 韧性与契约（阶段3 缓存容错 + 0.2 契约 schema）

## 目标
让会员视图**在 Open-Meteo 故障时不白屏、可缓存加速**，并把前后端数据契约固化为**单一来源**。
聚焦 surf-report-web spec 的：**0.2**(report.schema.json 契约) + **3.2**(故障降级不白屏) + **3.1**(cache.py TTL) + **3.3**(test_cache)。

## 排序（你的原则：最可能调整的决策在前，机械/测试垫底；红线逻辑测试随层）
1. **0.2 数据契约**（最可能调整）：抽 DAYS/HISTORY/REPORT 形状为 `web/report.schema.json`（含 wdeg/tp2/tideEvents 数字字段），前后端单一真相源。
2. **3.2 用户可见**：Open-Meteo 取数失败时后端降级、前端**不白屏**（友好态/回退上一版），保留校准时间戳诚实。
3. **3.1 内部**：cache.py TTL（预报短 TTL / 历史长缓存），由 `SF_CACHE_BUCKET` 特性开关控制。
4. **3.3 测试**：test_cache（TTL 边界/降级路径）；红线逻辑（TTL 命中/过期、降级触发）**边界双侧钉死随层编织**，不推迟。

## DoD
- pytest 全绿（新增 test_cache）+ 冻结 E2E 64/0 + 0 JS 报错；schema 与实际 render_json 字段一致（校验脚本）。
- 故障降级：模拟 Open-Meteo 失败 → 前端有内容（回退/友好态），非白屏、非 NaN 图表。
- 全程 GMT+8；据实勾选。

## 红线
- **单一驱动器**：auto-nudge 唯一，禁 task_run；与每日 triage cron/自迭代不并发写同文件。
- **DATA CONTRACT**：render_json 每日含 wdeg 数字数组；图表字段(times/windows/tideEvents/hs/wind/gust)为数字；预报区与历史区日期互斥；全程 GMT+8。
- **冷点炸弹教训**：缓存/TTL **绝不把"可见性"耦合到成本开关**（可见性用 list_listed_registry 类，不受 refresh_enabled 影响）。
- float→Decimal(`_to_decimal`) 写 DynamoDB；`/api/*` 全 401；ALB SG 禁 0.0.0.0/0；terraform 禁 -auto-approve。
- 每轮改前用 skill surf-forecast-codelens-dev 摸底(explain_code/find_symbol)+爆炸半径(get_impact/find_affected_tests)+守红线(find_route)；pytest/E2E 零倒退。
- **真部署留生产写操作门 G**（build+redeploy+canary+tag+CHANGELOG）等人工确认。

## 范围外
4.1/5.3 保存浪点 CRUD（归 custom-spots）；阶段6 Vite 组件化；阶段7 安全上线；自迭代 meta 工作。

## 停止
0.2/3.2/3.1/3.3 本地完成 + 全绿、仅剩生产写门时创建 STOP：
`/Users/yiming/.meshclaw/workspace-surf-forecast/.stop-chat-3-1783779532`
