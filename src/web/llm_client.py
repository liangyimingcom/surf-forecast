# -*- coding: utf-8 -*-
"""
llm_client.py — <llm-gateway> 网关轻客户端（OpenAI 兼容，stdlib urllib）。

env：SF_LLM_URL(网关基址) / SF_LLM_KEY(Secrets 注入) / SF_LLM_MODEL。
未配置 key → is_configured()=False（调用方直接降级模板，本地/测试零依赖）。
chat() 失败/超时抛 LLMError（调用方降级）。反注入：system 与 user(data) 分段由调用方组织。
"""
from __future__ import annotations

import json
import os
import urllib.request

DEFAULT_MODEL = "bedrock-claude-sonnet-4-6"


class LLMError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(os.getenv("SF_LLM_KEY") and os.getenv("SF_LLM_URL"))


def chat(messages: list, timeout: float = 12.0, max_tokens: int = 512) -> str:
    """OpenAI 兼容 /v1/chat/completions；返回 choices[0].message.content。未配置/失败抛 LLMError。"""
    url = os.getenv("SF_LLM_URL")
    key = os.getenv("SF_LLM_KEY")
    model = os.getenv("SF_LLM_MODEL", DEFAULT_MODEL)
    if not (url and key):
        raise LLMError("LLM 未配置(SF_LLM_URL/SF_LLM_KEY)")
    body = json.dumps({"model": model, "messages": messages,
                       "max_tokens": max_tokens, "temperature": 0.3}).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/v1/chat/completions", data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001
        raise LLMError("网关调用失败: %r" % e) from e
