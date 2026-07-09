"""浪点模型纯函数 —— custom-spots R1.2（slug / 去重键 / 区域·朝向推断）。

纯函数无 AWS 依赖，可单测。红线：slug 全局唯一且稳定（作缓存键前缀，不可漂移）。
"""

from __future__ import annotations

import re
import unicodedata

# 黄海近似范围（已标定 thresholds）：约 34–41°N, 119–126°E，浪点默认朝向 SSE≈157°
HUANGHAI_BBOX = (34.0, 41.0, 119.0, 126.0)  # (lat_min, lat_max, lon_min, lon_max)
HUANGHAI_FACING_DEG = 157
DEFAULT_FACING_DEG = 180  # 未标定海域缺省（向南），用户可覆盖


def slugify(name: str) -> str:
    """名称 → ASCII slug（小写、连字符）。中文/非 ASCII 被剥离后若为空，返回 ""。

    调用方在 slug 为空或冲突时应退化为 geo_slug（保证全局唯一稳定）。
    """
    norm = unicodedata.normalize("NFKD", name)
    ascii_only = norm.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only).strip("-").lower()
    return s


def geo_slug(lat: float, lon: float) -> str:
    """坐标编码 slug：geo-{lat4}-{lon4}（负号转 n），全局唯一且稳定。"""
    def enc(v: float) -> str:
        return f"{abs(round(v, 4)):.4f}".replace(".", "") if v >= 0 else \
               "n" + f"{abs(round(v, 4)):.4f}".replace(".", "")
    return f"geo-{enc(lat)}-{enc(lon)}"


def make_slug(name: str, lat: float, lon: float, existing: set[str] | None = None) -> str:
    """生成稳定唯一 slug：优先 slugify(name)，空或冲突 → geo_slug。

    existing：已占用 slug 集合（全局），用于冲突检测。
    """
    existing = existing or set()
    base = slugify(name)
    if base and base not in existing:
        return base
    geo = geo_slug(lat, lon)
    if geo not in existing:
        return geo
    # 极端冲突：追加短后缀
    i = 2
    while f"{geo}-{i}" in existing:
        i += 1
    return f"{geo}-{i}"


def dedup_key(lat: float, lon: float, facing_deg: float) -> str:
    """去重键：坐标 4 位小数 + 朝向。同键视为同一物理浪点，共享 slug 与缓存。"""
    return f"{round(lat, 4)}:{round(lon, 4)}:{round(facing_deg)}"


def infer_region(lat: float, lon: float) -> str:
    """按坐标推断已标定海域键；不在范围内返回 'uncalibrated'。"""
    lat_min, lat_max, lon_min, lon_max = HUANGHAI_BBOX
    if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
        return "huanghai"
    return "uncalibrated"


def infer_facing(lat: float, lon: float, override: float | None = None) -> float:
    """推断浪点朝向 spot_facing_deg：用户覆盖优先，否则按区域缺省。"""
    if override is not None:
        return float(override)
    if infer_region(lat, lon) == "huanghai":
        return float(HUANGHAI_FACING_DEG)
    return float(DEFAULT_FACING_DEG)


def validate_coord(lat: float, lon: float) -> None:
    """坐标范围校验，非法抛 ValueError。"""
    if not (-90 <= lat <= 90):
        raise ValueError(f"lat 超范围: {lat}")
    if not (-180 <= lon <= 180):
        raise ValueError(f"lon 超范围: {lon}")


def validate_name(name: str) -> str:
    """名称校验 + 转义防 XSS。返回清洗后的名称；非法抛 ValueError。"""
    n = (name or "").strip()
    if not (1 <= len(n) <= 32):
        raise ValueError("名称长度需 1-32")
    # 转义 HTML 特殊字符（前端零信任，存储即清洗）
    n = (n.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
         .replace('"', "&quot;").replace("'", "&#39;"))
    return n
