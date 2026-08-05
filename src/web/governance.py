"""R2 目录治理纯函数 —— status / beach_group / is_test（Fable5迭代建议-R2 §1.1）。

三字段语义（决策2/6/8）：
- op_status: open | maintenance | pending。运营状态；现状藏在 name/city 字符串后缀
  （「（维护中）」「(待开放)」），迁移解析成字段后展示名还原干净。
  注：registry 已有 status=active|inactive（上下架），语义不同，故新字段名用 op_status。
- beach_group: 同一片海滩多机位的归并键（平铺+分组键，不建 Beach 实体·决策8）；
  推荐层每组只留最高分一条，目录页保留分列（用户找直播机位需要）。
- is_test: E2E 测试点。生产接口默认过滤；E2E 带 X-Test-Access 密钥可见（决策6，单环境）。
"""
from __future__ import annotations

import re

# 状态后缀：全角/半角括号皆有（快照数据两种都出现）
_STATUS_PAT = re.compile(r"[（(]\s*(维护中|待开放)\s*[)）]")

_STATUS_MAP = {"维护中": "maintenance", "待开放": "pending"}

# 同滩多机位人工标注（一次性，R2 §1.1；按"同一片可冲的海滩"判断）
BEACH_GROUPS: dict[str, str] = {
    "sl2": "shizidao", "sl58": "shizidao",          # 狮子岛全景 / 狮子岛-右
    "sl54": "honghaiwan", "sl61": "honghaiwan",     # 虹海湾山海里 / 虹海湾久乐
    "sl93": "xichong", "sl49": "xichong",           # 西涌 / 西涌-全景
    "sl57": "shimeiwan", "sl91": "shimeiwan", "sl75": "shimeiwan",  # 石梅湾 艾美/大石头/九里
    "sl39": "fuliwan", "sl76": "fuliwan",           # 富力湾 / 富力湾全景
}

# 测试点名称前缀（E2E 冻结套件经 POST /api/spots 创建，名称以此开头）
_TEST_NAME_PAT = re.compile(r"^\s*(E2E|e2e|测试)")


def parse_op_status(name: str | None, city: str | None) -> tuple[str, str, str]:
    """从 name/city 解析运营状态。返回 (clean_name, clean_city, op_status)。

    状态后缀可能出现在 city（主流）或 name（如「SURFPARK （待开放）」）。
    city 整体就是状态标记时清空（「（维护中）」不是城市）。
    """
    op = "open"
    n, c = (name or ""), (city or "")

    def _strip(s: str) -> str:
        nonlocal op
        m = _STATUS_PAT.search(s)
        if m:
            op = _STATUS_MAP.get(m.group(1), op)
            s = _STATUS_PAT.sub("", s)
        return s.strip()

    c = _strip(c)
    n = _strip(n)
    return n, c, op


def is_test_name(name: str | None) -> bool:
    """E2E/测试点名称判定（创建时打 is_test，迁移时补标存量）。"""
    return bool(_TEST_NAME_PAT.match(name or ""))


def annotate_row(row: dict) -> dict:
    """就地补齐治理三字段（幂等）。用于迁移与种子灌入。

    幂等关键：重跑时名称已干净化、解析不到后缀，此时**保留已有 op_status**
    （否则二次迁移会把 maintenance/pending 静默重置回 open）。"""
    name, city, op = parse_op_status(row.get("spot"), row.get("city"))
    row["spot"] = name or row.get("spot")
    row["city"] = city
    if op != "open" or not row.get("op_status"):
        row["op_status"] = op
    row["beach_group"] = BEACH_GROUPS.get(row.get("slug") or "")
    row["is_test"] = bool(row.get("is_test")) or is_test_name(row.get("spot"))
    return row


def visible_rows(rows: list[dict], include_test: bool = False) -> list[dict]:
    """公开可见集：默认剔除 is_test（决策6 生产内标记过滤）。"""
    if include_test:
        return list(rows)
    return [r for r in rows if not r.get("is_test")]


def recommendable_rows(rows: list[dict]) -> list[dict]:
    """推荐候选池（R2 §1.3 前两道过滤）：剔 is_test → 剔非 open。
    op_status 缺失视为 open（未迁移的老行不误伤）。coverage 分母即本池大小。"""
    out = []
    for r in rows:
        if r.get("is_test"):
            continue
        if (r.get("op_status") or "open") != "open":
            continue
        out.append(r)
    return out


def dedup_by_beach(scored: list[dict]) -> list[dict]:
    """第三道过滤：每 beach_group 只留最高分一条（入参需已按分数降序）。
    无分组键的点不归并。"""
    seen: set[str] = set()
    out = []
    for s in scored:
        g = s.get("beach_group")
        if g:
            if g in seen:
                continue
            seen.add(g)
        out.append(s)
    return out


# ============================================================
# R2 数据健康探测器（纯函数，无 I/O）——供 /api/status 与运维巡检脚本共用。
#
# 存在理由：本项目「无推送告警，/status 是唯一故障发现渠道」（R2 决策5）。
# 若某类坏数据只能靠人肉翻 DynamoDB/S3 才看得见，那这个渠道就是失效的。
# ============================================================

def coord_invalid_rows(rows: list[dict]) -> list[dict]:
    """带 `coord_invalid` 标记的行 → [{slug, spot, why}]（slug 升序）。

    标记由 seed 导入护栏打上（源快照坐标越界时隔离出刷新池但保留目录可见）。
    生产当前应为空——它是**未来复发的探测器**，不是当下故障清单。
    """
    out = [{"slug": r.get("slug"), "spot": r.get("spot"),
            "why": str(r.get("coord_invalid"))}
           for r in rows if r.get("coord_invalid")]
    return sorted(out, key=lambda x: str(x["slug"]))


def coord_duplicate_groups(rows: list[dict], ndigits: int = 4) -> list[dict]:
    """坐标重复分组 → [{coord, slugs, spots, severity, beach_groups, regions}]，
    只返回同坐标 ≥2 个浪点的组，按 coord 升序。

    精度取 4 位小数，**与 `spots_model.dedup_key` 及 `find_registry_by_coord`
    的比较精度一致**——正是这个精度上的重复会让「坐标 → slug」解析出现歧义
    （`find_registry_by_coord` 取首个匹配），与 v0.3.2「S3 报告缓存从未命中」同族。

    **分级（避免狼来了）**：并非所有同坐标都是坏数据——
      - `expected`：同一个非空 `beach_group`，即同一片海滩的不同机位/视角
        （实例：`sl49 西涌-全景`/`sl93 西涌`、`sl2 狮子岛全景`/`sl58 狮子岛-右`）。
      - `suspect`：跨 beach_group 或跨区域 → 真异常
        （实例：`sl84 Kirra` 在澳洲，却与广东 `sl54 虹海湾山海里` 同坐标）。
    消费方应只把 `suspect` 当故障上报，否则 3 组里 2 组是误报，告警会被无视。
    """
    buckets: dict[tuple[float, float], list[dict]] = {}
    for r in rows:
        lat, lon = r.get("lat"), r.get("lon")
        if lat is None or lon is None:
            continue
        try:
            key = (round(float(lat), ndigits), round(float(lon), ndigits))
        except (TypeError, ValueError):
            continue
        buckets.setdefault(key, []).append(r)
    out = []
    for (lat, lon), group in buckets.items():
        if len(group) < 2:
            continue
        g = sorted(group, key=lambda r: str(r.get("slug")))
        beaches = {r.get("beach_group") for r in g}
        regions = {r.get("region_cn") for r in g}
        same_beach = len(beaches) == 1 and all(beaches)
        out.append({
            "coord": f"{lat},{lon}",
            "slugs": [r.get("slug") for r in g],
            "spots": [r.get("spot") for r in g],
            "severity": "expected" if same_beach else "suspect",
            "beach_groups": sorted(str(b) for b in beaches),
            "regions": sorted(str(x) for x in regions),
        })
    return sorted(out, key=lambda x: x["coord"])



def coord_component_collisions(rows: list[dict], min_decimals: int = 6) -> list[dict]:
    """**逐字段串行**探测：多个浪点共享同一个高精度坐标分量（lat 或 lon）。

    为什么需要它（4dp 重复探测器抓不到的一类）：
    高精度浮点值（≥6 位小数）在两个真实浪点间巧合相同是物理上不可能的，只可能是
    上游数据串行。而串行**可以只发生在一个分量上** —— 此时组合坐标是唯一的，
    `coord_duplicate_groups` 完全看不见。

    2026-08-05 生产实测抓到 3 例，其中 1 例是任何其他检查都发现不了的：
      - `sl84 Kirra`(国外) 整套借用 `sl54 虹海湾山海里`(广东) 的 lat+lon
      - `sl85 Currumbin`(国外) 的 lat 取自 `sl60 南燕湾`(海南)、lon 取自 `sl49 西涌`(广东)
        —— 两个分量来自**不同**的国内点；坐标落在南海且有浪场数据，
        于是为一个澳洲浪点静默产出"看起来很合理"的错误预报（最坏的一种失败）
      - `sl71 海螺湾`(浙江) 借用 `sl57 石梅湾-艾美`(海南) 的 lon

    分级同 `coord_duplicate_groups`：
      - `expected`：全组同一个非空 `region_cn`（同片海域的多机位，共享坐标属正常）
      - `suspect`：跨区域 → 真串行
    """
    out = []
    for comp in ("lat", "lon"):
        buckets: dict[str, list[dict]] = {}
        for r in rows:
            v = r.get(comp)
            if v is None:
                continue
            s = str(v)
            frac = s.split(".")[-1] if "." in s else ""
            if len(frac) < min_decimals:      # 低精度值巧合相同是可能的，跳过
                continue
            buckets.setdefault(s, []).append(r)
        for value, group in buckets.items():
            if len(group) < 2:
                continue
            g = sorted(group, key=lambda r: str(r.get("slug")))
            regions = {r.get("region_cn") for r in g}
            same_region = len(regions) == 1 and all(regions)
            out.append({
                "component": comp,
                "value": value,
                "slugs": [r.get("slug") for r in g],
                "spots": [r.get("spot") for r in g],
                "regions": sorted(str(x) for x in regions),
                "severity": "expected" if same_region else "suspect",
            })
    return sorted(out, key=lambda x: (x["component"], x["value"]))
