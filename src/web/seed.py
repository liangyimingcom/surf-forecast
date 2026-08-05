"""P1.3 注册表种子 — 把石老人 58 浪点快照灌入 spot_registry（形态C）。

- build_registry_rows(snapshot): 纯函数，快照 → 注册表行(含 live_src/facing_calibrated)。
- seed_store(store, rows): 逐行 upsert_registry（走 _to_decimal，红线自动守住）。
- 本地(内存 store)由 get_store 在 SF_SEED_SPOTS 指向快照时自动灌入；
  生产(DynamoDB)由 tools/load_registry.py 一次性灌入。
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from . import governance
from . import spots_model as sm

_GMT8 = timezone(timedelta(hours=8))


def _now() -> str:
    return datetime.now(_GMT8).strftime("%Y-%m-%d %H:%M:%S+0800")


def build_registry_rows(snapshot: dict) -> list[dict]:
    """快照 dict → 注册表行列表。仅保留含坐标的浪点；slug 用快照稳定 slug(slN)。"""
    rows = []
    for s in snapshot.get("spots", []):
        lat, lon = s.get("lat"), s.get("lon")
        if lat is None or lon is None:
            continue
        lat, lon = float(lat), float(lon)
        # 护栏(H1.1)：导入路径过去绕过了用户 CRUD 必过的 sm.validate_coord ——
        # 源快照里 sl75/sl76 的 lat=110.363232（>90，实为经度值）因此静默进了注册表，
        # Open-Meteo 每日返回 "Latitude must be in range of -90 to 90°"
        # → 刷新固定 2 点失败(58/60)，一周无人察觉。
        # 处置：**不丢弃**（仍留公开目录可见，守"可见性不耦合刷新开关"红线），
        #       但隔离出刷新池 + 标注原因，让失败变成可见状态而非每日噪声。
        coord_err: str | None = None
        try:
            sm.validate_coord(lat, lon)
        except ValueError as e:
            coord_err = str(e)
        facing = float(s.get("facing", sm.infer_facing(lat, lon)))
        rows.append({
            "slug": s["slug"],                     # 稳定不可变(slN)
            "spot": s.get("name"),
            "lat": lat, "lon": lon,
            "spot_facing_deg": facing,
            "facing_calibrated": bool(s.get("facing_calibrated", False)),
            "region": sm.infer_region(lat, lon),
            "region_cn": s.get("region_cn", "其他"),   # 官方区域(广东/海南/…/国外/其他)
            "city": s.get("city"),
            "days": 6,
            "dedup_key": sm.dedup_key(lat, lon, facing),
            "ref_count": 1,
            "status": "active",
            "refresh_enabled": coord_err is None,   # 非法坐标 → 退出刷新池(目录仍可见)
            "source": "shilaoren",                 # 溯源: 研究用途导入
            "live_src": s.get("live_src"),          # 直播 HLS(形态C)
            "post_url": s.get("post_url"),
            "created_at_gmt8": _now(),
            "last_refresh_at_gmt8": None,
            "last_viewed_at_gmt8": _now(),
        })
        governance.annotate_row(rows[-1])  # R2 治理：op_status/beach_group/is_test + 名称干净化
        if coord_err:                      # 护栏标注放在 annotate_row 之后（否则被覆盖）
            rows[-1]["op_status"] = "pending"
            rows[-1]["coord_invalid"] = coord_err
    return rows


def seed_store(store, rows: list[dict]) -> int:
    """逐行 upsert 到注册表；返回写入条数。已存在同 slug 则覆盖(幂等)。"""
    n = 0
    for row in rows:
        store.upsert_registry(row)
        n += 1
    return n


def seed_from_file(store, path: str) -> int:
    with open(path, "r", encoding="utf-8") as f:
        snap = json.load(f)
    return seed_store(store, build_registry_rows(snap))
