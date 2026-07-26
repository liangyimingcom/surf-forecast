# North Star — 前端体验提速（切换浪点秒开 · 大胆缓存）

## 目标
大幅降低"切换浪点/读取"的延迟：**已访问浪点秒开、首次并行加载、缓存激进**。
决策前提：**可接受稍旧数据**（本就每日刷新 02:00/14:00 + 页面显 GMT+8 校准时间戳=诚实）。
方案 = 方向甲(前端并行+客户端缓存+预取) + 方向乙(后端 TTL memo + 缓存覆盖)；**丙 CDN 暂缓**(cookie 鉴权有串用户风险)。

## 范围
- **P1 前端并行**：`loadLive` 把 /api/report 与 /api/report/history 由**串行改并行**（Promise.all）。
- **P2 客户端缓存**：REPORT/HISTORY 会话内内存缓存（键=lat,lon,days,spot）；**切回已访问浪点秒开**；缓存内容仍带校准时间戳（诚实，不伪装实时）。
- **P3 预取**（可选）：收藏/相邻浪点后台预取，切换即命中。
- **P4 后端 TTL**：部署开 `SF_REPORT_TTL`/`SF_HISTORY_TTL`（W3 已实现的进程内 memo），TTL 窗口内跳过 S3+解析。
- **P5 缓存覆盖**：确认 58 个上架浪点全有 `latest.json`（补刷新覆盖），消灭"实算数秒"慢点。

## DoD
- 切回已访问浪点**近乎瞬时**（客户端命中，无网络等待）；首次加载两请求并行（非串行）。
- pytest 不倒退；冻结 E2E **64/0** + 新增"并行/秒切"断言；0 JS 报错。
- 数据诚实：缓存展示仍显 GMT+8 校准时间戳（不伪装实时）；降级 banner 仍生效。
- 全程 GMT+8。

## 红线
- **数据诚实**：缓存/稍旧数据必须显真实校准时间戳，绝不标为"实时"。
- **冷点炸弹**：任何缓存**不碰可见性**（目录/直播用 list_listed_registry，与提速缓存解耦）。
- **单一驱动器**（禁 task_run）；与每日 triage cron/其他 goal 不并发写同文件。
- DATA CONTRACT(wdeg/数字图表/预报历史互斥)、float→Decimal、全401、SG禁0.0.0.0/0、terraform禁-auto-approve。
- 每轮 codelens-dev 摸底+爆炸半径+守红线；**真部署留生产写操作门 G**。

## 范围外
CDN 缓存 /api（鉴权风险，另议）；Vite 组件化（不解决性能）；改引擎算法。

## 停止
P1-P5 本地完成+全绿、仅剩 G 门时创建 STOP：
`/Users/yiming/.meshclaw/workspace-surf-forecast/.stop-chat-3-1783779532`
