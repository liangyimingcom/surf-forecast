# -*- coding: utf-8 -*-
"""L2.3 req_pipeline --llm-coder 单测（LLM/重门全 mock，不触网/不跑真 pytest-E2E）。"""
import importlib.util
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("req_pipeline", os.path.join(_ROOT, "tools", "req_pipeline.py"))
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)


def _req(tmp_path, **extra):
    r = {"id": "llm-1", "status": "accepted", "kind": "improve", "page": "live",
         "auto_eligible": True, "rollbackable": True, "text": "直播文案补充", "accept": "y"}
    r.update(extra)
    f = tmp_path / "r.json"
    f.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    return str(f)


def _neutralize(monkeypatch):
    # 中和重门(不跑真 pytest/E2E/node)、不碰真文件
    monkeypatch.setattr(rp, "run_pytest", lambda: rp.Gate("pytest").passed("mock"))
    monkeypatch.setattr(rp, "run_e2e", lambda: rp.Gate("E2E").passed("mock"))
    monkeypatch.setattr(rp, "run_node_check", lambda: rp.Gate("node").passed("mock"))
    monkeypatch.setattr(rp, "run_schema_check", lambda: rp.Gate("schema").passed("mock"))
    monkeypatch.setattr(rp, "apply_edit", lambda edit, dry=False: (edit["file"], "a", "a", False))


def test_llm_coder_generates_edit_then_gates_ok(monkeypatch, tmp_path):
    _neutralize(monkeypatch)
    monkeypatch.setattr(rp, "_llm_generate_edit",
                        lambda r: {"file": "web/浪报MVP.html", "op": "replace",
                                   "find": "直播流来自公开来源", "replace": "直播流来自公开来源"})
    monkeypatch.setattr(sys, "argv", ["req_pipeline", "--requirement", _req(tmp_path),
                                      "--llm-coder", "--skip-e2e", "--audit-out", str(tmp_path / "a.jsonl")])
    assert rp.main() == 0            # AUTO_OK：LLM 生成 edit 过硬门(仍 draft PR/人工审)


def test_llm_coder_generation_failure_needs_human(monkeypatch, tmp_path):
    _neutralize(monkeypatch)
    def _boom(r):
        raise RuntimeError("网关不通")
    monkeypatch.setattr(rp, "_llm_generate_edit", _boom)
    monkeypatch.setattr(sys, "argv", ["req_pipeline", "--requirement", _req(tmp_path),
                                      "--llm-coder", "--skip-e2e", "--audit-out", str(tmp_path / "a.jsonl")])
    assert rp.main() == 2            # NEEDS_HUMAN


def test_no_edit_without_flag_needs_human(monkeypatch, tmp_path):
    _neutralize(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["req_pipeline", "--requirement", _req(tmp_path),
                                      "--skip-e2e", "--audit-out", str(tmp_path / "a.jsonl")])
    assert rp.main() == 2            # 无 edit 且未开 --llm-coder → 人工


def test_generate_edit_unconfigured_raises(monkeypatch):
    monkeypatch.delenv("SF_LLM_URL", raising=False)
    monkeypatch.delenv("SF_LLM_KEY", raising=False)
    try:
        rp._llm_generate_edit({"text": "x"})
        assert False, "应抛未配置"
    except RuntimeError:
        pass
