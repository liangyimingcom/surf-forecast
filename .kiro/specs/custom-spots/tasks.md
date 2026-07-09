# Tasks — Custom Spots（浪点自定义与管理，v2 新增）

> Kiro 约定：一次一个任务，完成勾 [x]，标注满足的需求/验收(C)。
> 前置：surf-report-web 鉴权/会话已上线；deployment-and-ops refresh_spots + S3 缓存已上线；引擎 build_context/render_json 含 wdeg 已上线。
> 红线：slug 不可变（缓存键稳定）；同坐标全局去重；validate 守门；全程 GMT+8；鉴权全后端。

## 阶段 1：数据层与注册表（纯代码，无 AWS 副作用）
- [x] 1.1 db.py 补 saved_spots 访问：put_spot/list_spots(by email)/get_spot/update_spot/soft_delete _(C2)_
- [x] 1.2 新增 spot_registry 模型与访问：upsert/list_active/incr_ref/decr_ref/set_refresh_enabled _(C5)_
- [x] 1.3 slug 生成器：slugify(name) 冲突退化 geo-{lat4}-{lon4}，全局唯一稳定 _(C1)_
- [ ] 1.4 去重键：round(lat,4)+round(lon,4)+facing；region/facing 推断函数（继承区域缺省） _(C5,C6)_
- [ ] 1.5 test_spot_models（slug 稳定/去重键/区域推断） + moto 表测试 _(C1,C5)_

## 阶段 2：浪点 CRUD API（src/web/spots.py）
- [x] 2.1 spots.py：GET/POST/PATCH/DELETE /api/spots + /select，全部 401 保护 _(C2,C9)_
- [x] 2.2 POST 流程：坐标校验→配额(free=3/paid=20)→名称唯一→去重(registry)→写 saved_spots(+ref_count) _(C1,C2)_
- [x] 2.3 名称/坐标校验与转义（防 XSS/注入；精度≥4 位；范围检查） _(C9)_
- [x] 2.4 PATCH 重命名/改朝向保持 slug 不变；DELETE 软删 status=inactive + ref_count-- _(C2,C8)_
- [x] 2.5 内陆/无数据坐标保存前警告；未标定海域标注 "按黄海近似" _(C6)_
- [x] 2.6 app.py 挂载 spots 路由（仅文档标注，实际接线在实现期）
- [x] 2.7 test_spot_crud + test_spots_auth（CRUD/隔离/配额/401/转义） _(C2,C9)_

## 阶段 3：查询切换与缓存读（deps 扩展）
- [x] 3.1 deps.get_report 扩展：按坐标查 registry 命中→读 {slug}/latest.json；未命中→回退引擎 _(C3,C10)_
- [x] 3.2 /select 记"上次选中" + 更新 last_viewed_at_gmt8（用于冷点回收排序） _(C3)_
- [x] 3.3 test_select_persist + test_custom_contract（自定义点缓存含 wdeg/GMT+8） _(C3,C10)_

## 阶段 4：动态刷新编排（refresh.py 改造）
- [x] 4.1 active_registry_spots(store)：读注册表 active+refresh_enabled，合并 DEFAULT_SPOTS 兜底 _(C5)_
- [x] 4.2 scheduled_refresh：注册表驱动替代硬编码 DEFAULT_SPOTS，复用 refresh_spots 逐点 validate _(C5,C7)_
- [x] 4.3 即时预算：POST /api/spots 未命中去重时触发一次 refresh_spots([new])，新点立即可读 _(C4)_
- [x] 4.4 频率控制：每次调度预算上限 N，超出按 last_viewed 排序冷点降级"按需+短TTL" _(C5)_
- [x] 4.5 冷浪点回收：last_viewed 超 K 天 → refresh_enabled=false（仅按需计算） _(C8)_
- [x] 4.6 test_registry_refresh + test_instant_budget + test_cold_recycle _(C4,C5,C7,C8)_

## 阶段 5：前端浪点管理（浪报MVP.html 附加式扩展）
- [x] 5.1 spotManager：下拉(预设+已保存+➕新增) + 当前浪点高亮 _(C3)_
- [x] 5.2 新增面板：经纬度输入 + 名称 + 朝向(可选) → POST /api/spots → 切换+loadLive _(C1,C3)_
- [x] 5.3 切换：SPOT 重赋值→loadLive(复用实时数据层)→POST /select；记住上次选中 _(C3)_
- [x] 5.4 管理：✏️重命名 / 🗑删除(软删)；未登录/故障回退内嵌示例不白屏 _(C2)_
- [x] 5.5 （阶段 B）嵌入 Leaflet+OSM 地图点选回填坐标 ✅ + 前端重命名按钮(PATCH slug不变) _(C1)_
- [ ] 5.6 JS 语法校验 + 浏览器走查（切换即时加载、当日 GMT+8 实时数据） _(C3,C10)_

## 阶段 6：基础设施（IaC，需 apply 审批）
- [x] 6.1 storage 模块新增 spot_registry DynamoDB 表（on-demand/PITR/PK=slug） _(C5)_
- [x] 6.2 即时预算路径的 IAM：后端任务角色补 RunTask 或同步预算权限 _(C4)_
- [x] 6.3 terraform validate + plan 摘要（apply 暂停审批，遵守 apply 红线）

## 依赖
```
1.x(数据层) ──> 2.x(CRUD API) ──> 3.x(查询切换) ──┐
                      └──> 4.x(动态刷新) ──────────┼──> 5.x(前端) ──> 6.x(IaC apply)
                                                   引擎/缓存/调度为外部前置
```

## 完成定义
会员可经纬度/地图自定义命名浪点并多点管理（CRUD+配额+隔离）；切换即时加载（缓存命中<500ms）；新建触发即时预算立即可用；动态注册表驱动每日刷新且按坐标去重控调用量；冷点暂停刷新、删除软删保留历史；自定义点与默认点同口径含 wdeg、全程 GMT+8、离岸判定按该点朝向；全部接口 401 保护且输入转义。
> 红线：slug 不可变、validate 守门、读写解耦、数据诚实（未标定海域标注）继续强制。
