#!/usr/bin/env python3
"""P1 浪点导入 — 从石老人上游拉 58 浪点，产出规整快照 JSON（供 P1.3 写注册表）。

- getCamera/all      → cId/name/city/live_src/post_url + 实时指标
- getNewForecast/{cId}→ latitude/longitude（逐点，一次性快照）
- facing             → 默认按海岸粗估 + needs_calibration=True（离岸风质算法依赖，待校准）

用法: python tools/import_shilaoren_spots.py [out.json]
仅标准库(urllib)。合规: 仅公开只读接口, 研究用途。
"""
import json, sys, time, urllib.request, urllib.error, re

BASE = "https://isurf.c-pan.cn"
HEADERS = {"User-Agent": "Mozilla/5.0 MiniProgramEnv", "Referer": "https://servicewechat.com/"}
OUT = sys.argv[1] if len(sys.argv) > 1 else "reference/data/shilaoren_spots.json"

# 城市/区域 → 粗估浪点朝向(浪从该方向来)。中国海岸多面向 E~SE；默认 135(SE)。待逐点校准。
REGION_FACING = {
    "ShanDong": 157, "QingDao": 157,          # 黄海, SSE
    "HuiZhou": 135, "ShenZhen": 160, "GuangDong": 135,
    "HaiNan": 110, "SanYa": 150, "WanNing": 90,   # 万宁东海岸面 E
    "FuJian": 110, "PingTan": 90,
    "GuangXi": 200, "ZheJiang": 110,
}
def guess_facing(city):
    if not city: return 135
    for k, v in REGION_FACING.items():
        if k.lower() in city.lower(): return v
    return 135

def get(path):
    req = urllib.request.Request(BASE + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

def slugify(cid, name):
    return f"sl{cid}"   # 稳定不可变(基于 cId)，作缓存键

def main():
    # 官方区域: getCategories(ctId→name) + getCamera/{ctId}(成员cId) → cId→region_cn
    cid_region = {}
    try:
        cats = get("/default/getCategories")
        cats = cats.get("data") or cats.get("list") or cats if isinstance(cats, dict) else cats
        for cat in cats:
            ctid, name = cat.get("ctId"), cat.get("category_name")
            try:
                mem = get(f"/default/v2/getCamera/{ctid}")
                mem = mem.get("data") or mem.get("list") or mem if isinstance(mem, dict) else mem
                for m in mem:
                    cid_region[m.get("cId")] = name
            except Exception:
                pass
            time.sleep(0.15)
        print(f"[import] 区域映射: {len(cid_region)} 浪点已归类", file=sys.stderr)
    except Exception as e:
        print(f"[import] 区域映射失败(降级 其他): {e}", file=sys.stderr)

    cams = get("/default/v2/getCamera/all")
    if isinstance(cams, dict):
        cams = cams.get("data") or cams.get("list") or []
    print(f"[import] getCamera/all → {len(cams)} 浪点", file=sys.stderr)
    spots = []
    for i, c in enumerate(cams):
        cid = c.get("cId")
        lat = lon = None
        try:
            fc = get(f"/default/getNewForecast/{cid}")
            data = fc.get("data", fc) if isinstance(fc, dict) else fc
            lat = data.get("latitude") if isinstance(data, dict) else None
            lon = data.get("longitude") if isinstance(data, dict) else None
        except Exception as e:
            print(f"  ! cId={cid} 坐标拉取失败: {e}", file=sys.stderr)
        try:
            lat = float(lat); lon = float(lon)
        except (TypeError, ValueError):
            lat = lon = None
        city = c.get("city") or ""
        spots.append({
            "slug": slugify(cid, c.get("name")),
            "cId": cid,
            "name": c.get("name"),
            "city": city,
            "region_cn": cid_region.get(cid, "其他"),   # 官方区域: 广东/海南/福建/广西/浙江/山东/国外/其他
            "lat": lat, "lon": lon,
            "facing": guess_facing(city),
            "facing_calibrated": False,   # 待校准(离岸风质依赖)
            "live_src": c.get("live_src"),
            "post_url": c.get("post_url"),
            "has_coord": lat is not None and lon is not None,
        })
        time.sleep(0.15)   # 温和限速
        if (i + 1) % 10 == 0:
            print(f"  ... {i+1}/{len(cams)}", file=sys.stderr)
    have = sum(1 for s in spots if s["has_coord"])
    out = {"source": "shilaoren isurf (研究用途)", "generated_at": time.strftime("%Y-%m-%d %H:%M:%S+0800"),
           "count": len(spots), "with_coord": have, "spots": spots}
    import os
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[import] 写入 {OUT}: {len(spots)} 浪点, {have} 含坐标", file=sys.stderr)

if __name__ == "__main__":
    main()
