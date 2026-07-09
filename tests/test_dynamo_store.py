"""DynamoDBStore 单测 —— moto 离线模拟，验证持久化接口与 InMemoryStore 等价（D4）。"""

import boto3
import pytest
from moto import mock_aws

from web import auth, db

PREFIX = "surf-forecast-test"


@pytest.fixture
def ddb_store():
    with mock_aws():
        res = boto3.resource("dynamodb", region_name="ap-northeast-1")
        res.create_table(
            TableName=f"{PREFIX}-users",
            KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST")
        res.create_table(
            TableName=f"{PREFIX}-sessions",
            KeySchema=[{"AttributeName": "token", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "token", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST")
        res.create_table(
            TableName=f"{PREFIX}-accuracy_votes",
            KeySchema=[{"AttributeName": "email", "KeyType": "HASH"},
                       {"AttributeName": "voteId", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"},
                                  {"AttributeName": "voteId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST")
        yield db.DynamoDBStore(PREFIX, resource=res)


def test_user_roundtrip_persists(ddb_store):
    user = {"userId": "u1", "email": "a@b.com",
            "passwordHash": auth.hash_password("secret123"), "level": "free"}
    ddb_store.put_user(user)
    got = ddb_store.get_user("a@b.com")
    assert got["email"] == "a@b.com"
    assert auth.verify_password(got["passwordHash"], "secret123")
    assert ddb_store.get_user("missing@b.com") is None


def test_session_roundtrip(ddb_store):
    ddb_store.put_session("tok123", "a@b.com")
    assert ddb_store.get_session_email("tok123") == "a@b.com"
    ddb_store.delete_session("tok123")
    assert ddb_store.get_session_email("tok123") is None


def test_votes_query_by_email_filter_spot(ddb_store):
    ddb_store.add_vote({"email": "a@b.com", "spot": "山东头", "date": "2026-06-20", "kind": "accurate"})
    ddb_store.add_vote({"email": "a@b.com", "spot": "别处", "date": "2026-06-20", "kind": "optimistic"})
    rows = ddb_store.votes_for("a@b.com", "山东头")
    assert len(rows) == 1 and rows[0]["kind"] == "accurate"


def test_auth_flow_on_dynamo(ddb_store):
    # 用 DynamoDBStore 跑完整注册→登录→会话校验，证明可替换 InMemoryStore
    auth.register(ddb_store, "x@b.com", "secret123")
    token = auth.login(ddb_store, "x@b.com", "secret123")
    assert ddb_store.get_session_email(token) == "x@b.com"
