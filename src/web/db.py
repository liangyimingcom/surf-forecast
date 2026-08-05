"""存储抽象 —— design web §4 / D4。

MVP/测试用内存实现；生产切 DynamoDB（同接口）。表：users / sessions / members / saved_spots / accuracy_votes。
鉴权全后端：session token 服务端存储，httponly cookie 仅携带不可逆 token（前端零信任）。
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# 坐标匹配精度：与 spots_model.dedup_key 及 governance.coord_duplicate_groups 一致。
COORD_NDIGITS = 4


def pick_registry_match(matches: list[dict], lat: float, lon: float) -> Optional[dict]:
    """多行同坐标(4dp)时的**确定性**选取 + 告警。两个 store 共用以保证语义一致。

    为什么需要：注册表里确实存在同 4dp 坐标的多个浪点（2026-08-05 生产实测 3 组，
    其中 `sl54 虹海湾山海里` / `sl84 Kirra` 跨滩跨区=真数据损坏）。旧实现两个 store
    都「取迭代顺序里的第一个」——而 **DynamoDB scan 顺序不保证稳定**，同一坐标可能
    今天解析成 A、明天解析成 B → S3 缓存键跟着翻 → 详情页可能显示另一个浪点的报告。
    与 v0.3.2「坐标精度错位致缓存永不命中」同族，都是坐标解析这一层的坑。

    处置：按 slug 字典序取最小（稳定、可预测、可复现），并告警把歧义暴露出来
    （`/api/status` 的 data_issues.coord_duplicates 会列出 suspect 组）。
    """
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    ordered = sorted(matches, key=lambda r: str(r.get("slug")))
    logger.warning(
        "坐标 (%s, %s) 命中 %d 个注册表浪点 %s —— 存在解析歧义，按 slug 字典序取 %s。"
        "请在 /status 的数据治理待办中核对该组坐标。",
        round(float(lat), COORD_NDIGITS), round(float(lon), COORD_NDIGITS),
        len(ordered), [r.get("slug") for r in ordered], ordered[0].get("slug"),
    )
    return ordered[0]


def _to_decimal(obj):
    """递归把 float → Decimal（DynamoDB boto3 resource 不接受 float）。"""
    from decimal import Decimal
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_decimal(v) for v in obj]
    return obj


class InMemoryStore:
    """线程安全的内存存储（dev/测试）。生产用 DynamoDBStore 替换。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.users: dict[str, dict] = {}      # email -> user
        self.sessions: dict[str, str] = {}    # token -> email
        self.votes: list[dict] = []           # accuracy_votes
        self.spots: dict[str, list] = {}      # email -> [spot,...]
        self.registry: dict[str, dict] = {}   # slug -> registry row (全局去重浪点)
        self.prefs: dict[str, str] = {}       # email -> last_selected slug
        self.feedback: dict[str, dict] = {}   # fid -> 需求/反馈行(status 状态机)

    # —— users ——
    def get_user(self, email: str) -> Optional[dict]:
        with self._lock:
            return self.users.get(email)

    def put_user(self, user: dict) -> None:
        with self._lock:
            self.users[user["email"]] = user

    # —— sessions ——
    def put_session(self, token: str, email: str) -> None:
        with self._lock:
            self.sessions[token] = email

    def get_session_email(self, token: str) -> Optional[str]:
        with self._lock:
            return self.sessions.get(token)

    def delete_session(self, token: str) -> None:
        with self._lock:
            self.sessions.pop(token, None)

    # —— accuracy_votes（feedback spec 用）——
    def add_vote(self, vote: dict) -> None:
        with self._lock:
            self.votes.append(vote)

    def votes_for(self, email: str, spot: str) -> list[dict]:
        with self._lock:
            return [v for v in self.votes if v["email"] == email and v["spot"] == spot]

    # —— saved_spots（custom-spots，PK=email, SK=slug）——
    def put_spot(self, email: str, spot: dict) -> None:
        with self._lock:
            lst = self.spots.setdefault(email, [])
            lst[:] = [s for s in lst if s["slug"] != spot["slug"]] + [spot]

    def list_spots(self, email: str, include_inactive: bool = False) -> list[dict]:
        with self._lock:
            lst = self.spots.get(email, [])
            return [s for s in lst if include_inactive or s.get("status") == "active"]

    def get_spot(self, email: str, slug: str):
        with self._lock:
            for s in self.spots.get(email, []):
                if s["slug"] == slug:
                    return s
            return None

    def soft_delete_spot(self, email: str, slug: str) -> bool:
        with self._lock:
            s = self.get_spot(email, slug)
            if s:
                s["status"] = "inactive"
                return True
            return False

    # —— spot_registry（全局去重浪点，PK=slug）——
    def upsert_registry(self, row: dict) -> None:
        with self._lock:
            self.registry[row["slug"]] = row

    def get_registry(self, slug: str):
        with self._lock:
            return self.registry.get(slug)

    def find_registry_by_dedup(self, dedup_key: str):
        with self._lock:
            for r in self.registry.values():
                if r.get("dedup_key") == dedup_key:
                    return r
            return None

    def find_registry_by_coord(self, lat: float, lon: float):
        # R3：收集**全部**匹配后确定性选取（旧实现取迭代顺序首个 → 同坐标多点时不可预测）。
        with self._lock:
            matches = [
                r for r in self.registry.values()
                if (r.get("status") == "active"
                    and round(r["lat"], COORD_NDIGITS) == round(lat, COORD_NDIGITS)
                    and round(r["lon"], COORD_NDIGITS) == round(lon, COORD_NDIGITS))
            ]
        return pick_registry_match(matches, lat, lon)

    def list_active_registry(self) -> list[dict]:
        with self._lock:
            return [r for r in self.registry.values()
                    if r.get("status") == "active" and r.get("refresh_enabled")]

    def list_listed_registry(self) -> list[dict]:
        """公开目录/直播可见集：仅 status=active（**不**要求 refresh_enabled）。
        与 list_active_registry(刷新/回收用)解耦——冷点回收关掉 refresh_enabled 时，
        浪点仍在目录/直播中可见（预报按点实时兜底）。"""
        with self._lock:
            return [r for r in self.registry.values() if r.get("status") == "active"]

    def incr_ref(self, slug: str, delta: int = 1) -> None:
        with self._lock:
            r = self.registry.get(slug)
            if r:
                r["ref_count"] = max(0, r.get("ref_count", 0) + delta)
                if r["ref_count"] == 0:
                    r["status"] = "inactive"

    def set_refresh_enabled(self, slug: str, enabled: bool) -> None:
        with self._lock:
            r = self.registry.get(slug)
            if r:
                r["refresh_enabled"] = enabled

    def set_last_selected(self, email: str, slug: str) -> None:
        with self._lock:
            self.prefs[email] = slug

    def get_last_selected(self, email: str):
        with self._lock:
            return self.prefs.get(email)

    # —— feedback / 需求库（status 状态机）——
    def add_feedback(self, row: dict) -> dict:
        with self._lock:
            self.feedback[row["id"]] = dict(row)
            return self.feedback[row["id"]]

    def list_feedback(self, status: str | None = None) -> list[dict]:
        with self._lock:
            rows = list(self.feedback.values())
        return [r for r in rows if status is None or r.get("status") == status]

    def set_feedback_status(self, fid: str, status: str) -> None:
        with self._lock:
            r = self.feedback.get(fid)
            if r:
                r["status"] = status

    def find_feedback_by_claim(self, claim: str) -> dict | None:
        with self._lock:
            for r in self.feedback.values():
                if r.get("claim_code") == claim:
                    return r
        return None


_store: InMemoryStore | None = None


class DynamoDBStore:
    """生产存储 —— DynamoDB（同 InMemoryStore 接口，键设计见 storage 模块）。

    表：{prefix}-users(PK email) / {prefix}-sessions(PK token,TTL) /
        {prefix}-accuracy_votes(PK email, SK voteId) / {prefix}-saved_spots(PK email, SK spotId)。
    """

    def __init__(self, prefix: str, resource=None):
        import boto3
        self.prefix = prefix
        ddb = resource or boto3.resource("dynamodb")
        self.users = ddb.Table(f"{prefix}-users")
        self.sessions = ddb.Table(f"{prefix}-sessions")
        self.votes = ddb.Table(f"{prefix}-accuracy_votes")
        self.spots_t = ddb.Table(f"{prefix}-saved_spots")
        self.registry_t = ddb.Table(f"{prefix}-spot_registry")
        self.feedback_t = ddb.Table(f"{prefix}-feedback")

    def get_user(self, email):
        r = self.users.get_item(Key={"email": email})
        return r.get("Item")

    def put_user(self, user):
        self.users.put_item(Item=_to_decimal(user))

    def put_session(self, token, email):
        import time
        self.sessions.put_item(Item={
            "token": token, "email": email,
            "expiresAt": int(time.time()) + 12 * 3600,  # TTL 12h
        })

    def get_session_email(self, token):
        r = self.sessions.get_item(Key={"token": token})
        item = r.get("Item")
        return item.get("email") if item else None

    def delete_session(self, token):
        self.sessions.delete_item(Key={"token": token})

    def add_vote(self, vote):
        import uuid
        item = dict(vote)
        item.setdefault("voteId", f"{vote['date']}#{uuid.uuid4().hex[:8]}")
        self.votes.put_item(Item=_to_decimal(item))

    def votes_for(self, email, spot):
        from boto3.dynamodb.conditions import Key
        r = self.votes.query(KeyConditionExpression=Key("email").eq(email))
        return [v for v in r.get("Items", []) if v.get("spot") == spot]

    # —— saved_spots（PK=email, SK=slug）——
    def put_spot(self, email, spot):
        item = dict(spot)
        item["email"] = email
        self.spots_t.put_item(Item=_to_decimal(item))

    def list_spots(self, email, include_inactive=False):
        from boto3.dynamodb.conditions import Key
        r = self.spots_t.query(KeyConditionExpression=Key("email").eq(email))
        items = r.get("Items", [])
        return items if include_inactive else [s for s in items if s.get("status") == "active"]

    def get_spot(self, email, slug):
        r = self.spots_t.get_item(Key={"email": email, "slug": slug})
        return r.get("Item")

    def soft_delete_spot(self, email, slug):
        self.spots_t.update_item(
            Key={"email": email, "slug": slug},
            UpdateExpression="SET #s = :v",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":v": "inactive"},
        )
        return True

    # —— spot_registry（PK=slug）——
    def upsert_registry(self, row):
        self.registry_t.put_item(Item=_to_decimal(row))

    def get_registry(self, slug):
        r = self.registry_t.get_item(Key={"slug": slug})
        return r.get("Item")

    def find_registry_by_dedup(self, dedup_key):
        from boto3.dynamodb.conditions import Attr
        r = self.registry_t.scan(FilterExpression=Attr("dedup_key").eq(dedup_key))
        items = r.get("Items", [])
        return items[0] if items else None

    def find_registry_by_coord(self, lat, lon):
        # 坐标匹配必须两侧同精度 round 后比较（与 InMemoryStore 语义一致）。
        # 旧实现用 round(入参,4) 与库中 6 位小数原值做 DynamoDB 精确相等 →
        # seeded 点(6位小数)永远匹配不上 → slug 解析失败 → S3 缓存永不命中 →
        # 每次详情页实时调 Open-Meteo 现算 ~5s（v0.3.2 提速实测揪出）。
        from boto3.dynamodb.conditions import Attr
        r = self.registry_t.scan(FilterExpression=Attr("status").eq("active"))
        items = r.get("Items", [])
        while r.get("LastEvaluatedKey"):
            r = self.registry_t.scan(FilterExpression=Attr("status").eq("active"),
                                     ExclusiveStartKey=r["LastEvaluatedKey"])
            items.extend(r.get("Items", []))
        matches: list[dict] = []
        for row in items:
            try:
                if (round(float(row["lat"]), COORD_NDIGITS) == round(lat, COORD_NDIGITS)
                        and round(float(row["lon"]), COORD_NDIGITS) == round(lon, COORD_NDIGITS)):
                    matches.append(row)
            except (TypeError, ValueError, KeyError):
                continue
        # R3：**DynamoDB scan 顺序不保证稳定**——取首个会让同坐标多点的解析结果在两次
        # 调用间漂移（缓存键跟着翻）。收全部匹配后走共享的确定性选取 + 告警。
        return pick_registry_match(matches, lat, lon)

    def list_active_registry(self):
        from boto3.dynamodb.conditions import Attr
        r = self.registry_t.scan(
            FilterExpression=Attr("status").eq("active") & Attr("refresh_enabled").eq(True))
        return r.get("Items", [])

    def list_listed_registry(self):
        """公开目录/直播可见集：仅 status=active（不要求 refresh_enabled）。
        与刷新/回收解耦——冷点回收关 refresh_enabled 后浪点仍在目录/直播可见。"""
        from boto3.dynamodb.conditions import Attr
        items, resp = [], self.registry_t.scan(FilterExpression=Attr("status").eq("active"))
        items.extend(resp.get("Items", []))
        while resp.get("LastEvaluatedKey"):
            resp = self.registry_t.scan(
                FilterExpression=Attr("status").eq("active"),
                ExclusiveStartKey=resp["LastEvaluatedKey"])
            items.extend(resp.get("Items", []))
        return items

    def incr_ref(self, slug, delta=1):
        row = self.get_registry(slug)
        if not row:
            return
        new = max(0, int(row.get("ref_count", 0)) + delta)
        status = "inactive" if new == 0 else row.get("status", "active")
        self.registry_t.update_item(
            Key={"slug": slug},
            UpdateExpression="SET ref_count = :c, #s = :st",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":c": new, ":st": status},
        )

    def set_refresh_enabled(self, slug, enabled):
        self.registry_t.update_item(
            Key={"slug": slug},
            UpdateExpression="SET refresh_enabled = :v",
            ExpressionAttributeValues={":v": bool(enabled)},
        )

    def set_last_selected(self, email, slug):
        self.users.update_item(
            Key={"email": email},
            UpdateExpression="SET last_selected = :v",
            ExpressionAttributeValues={":v": slug},
        )

    def get_last_selected(self, email):
        u = self.get_user(email)
        return (u or {}).get("last_selected")

    # —— feedback / 需求库（status 状态机，TTL 仅清 new/rejected）——
    def _fb_ttl(self, status: str):
        import time
        return int(time.time()) + 14 * 86400 if status in ("new", "rejected") else None

    def add_feedback(self, row: dict) -> dict:
        item = dict(row)
        ttl = self._fb_ttl(item.get("status", "new"))
        if ttl is not None:
            item["expiresAt"] = ttl
        self.feedback_t.put_item(Item=_to_decimal(item))
        return item

    def list_feedback(self, status: str | None = None) -> list[dict]:
        from boto3.dynamodb.conditions import Attr
        kw = {"FilterExpression": Attr("status").eq(status)} if status else {}
        items, resp = [], self.feedback_t.scan(**kw)
        items.extend(resp.get("Items", []))
        while resp.get("LastEvaluatedKey"):
            resp = self.feedback_t.scan(ExclusiveStartKey=resp["LastEvaluatedKey"], **kw)
            items.extend(resp.get("Items", []))
        return items

    def set_feedback_status(self, fid: str, status: str) -> None:
        # 采纳/进行中/已发 → 去掉 TTL（绝不被 TTL 误删）；new/rejected → 保留/重设 TTL
        ttl = self._fb_ttl(status)
        if ttl is None:
            self.feedback_t.update_item(
                Key={"id": fid},
                UpdateExpression="SET #s = :st REMOVE expiresAt",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":st": status})
        else:
            self.feedback_t.update_item(
                Key={"id": fid},
                UpdateExpression="SET #s = :st, expiresAt = :e",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":st": status, ":e": ttl})

    def find_feedback_by_claim(self, claim: str):
        from boto3.dynamodb.conditions import Attr
        r = self.feedback_t.scan(FilterExpression=Attr("claim_code").eq(claim))
        items = r.get("Items", [])
        return items[0] if items else None


def get_store():
    """按环境选存储：SF_STORE=dynamo + SF_TABLE_PREFIX → DynamoDB；否则内存（dev/测试）。"""
    global _store
    import os
    if os.getenv("SF_STORE") == "dynamo":
        prefix = os.getenv("SF_TABLE_PREFIX", "surf-forecast-dev")
        return DynamoDBStore(prefix)
    if _store is None:
        _store = InMemoryStore()
        # P1.3 形态C：本地/测试可用 SF_SEED_SPOTS 指向快照，一次性灌入 58 浪点注册表
        seed_path = os.getenv("SF_SEED_SPOTS")
        if seed_path and os.path.exists(seed_path):
            try:
                from . import seed as _seed
                n = _seed.seed_from_file(_store, seed_path)
                print(f"[seed] 注册表灌入 {n} 浪点 ← {seed_path}")
            except Exception as e:  # noqa: BLE001
                print(f"[seed] 灌入失败(忽略): {e}")
    return _store


def reset_store() -> None:
    """测试用：清空内存单例。"""
    global _store
    _store = InMemoryStore()
