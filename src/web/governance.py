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
