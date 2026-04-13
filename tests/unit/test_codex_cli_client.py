import json
from pathlib import Path

import pytest

import ai_mv.infra.codex_cli_client as codex_cli_client
from ai_mv.core.contracts.errors import CodexCliRequestError


def test_assert_codex_ready_requires_login(monkeypatch):
    monkeypatch.setattr(codex_cli_client, "_login_status", lambda *_args, **_kwargs: "Logged out")
    with pytest.raises(CodexCliRequestError, match="not logged in"):
        codex_cli_client.assert_codex_ready({"integrations": {}})


def test_ping_codex_uses_passed_config(monkeypatch):
    seen = {}

    def _fake_parts(config):
        seen["config"] = config
        return ["codex"]

    monkeypatch.setattr(codex_cli_client, "_codex_command_parts", _fake_parts)
    monkeypatch.setattr(codex_cli_client, "_login_status", lambda *_args, **_kwargs: "Logged in")
    cfg = {"integrations": {"codex_cli_path": "C:/tools/codex.cmd"}}
    assert codex_cli_client.ping_codex(cfg) is True
    assert seen["config"] == cfg


def test_generate_structured_validates_schema(monkeypatch):
    monkeypatch.setattr(codex_cli_client, "_run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        codex_cli_client,
        "_load_output",
        lambda *_args, **_kwargs: {"shots": [{"shot_id": "S001"}]},
    )
    schema = {
        "type": "object",
        "required": ["shots"],
        "properties": {
            "shots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["shot_id", "seed"],
                    "properties": {"shot_id": {"type": "string"}, "seed": {"type": "integer"}},
                },
            }
        },
    }
    with pytest.raises(CodexCliRequestError, match="schema validation failed"):
        codex_cli_client.generate_structured({"integrations": {}}, "p", schema)


def test_load_output_rejects_invalid_json(tmp_path: Path):
    path = tmp_path / "output.json"
    path.write_text("{oops", encoding="utf-8")
    with pytest.raises(CodexCliRequestError, match="invalid JSON"):
        codex_cli_client._load_output(path)


def test_generate_structured_runs_once_on_schema_failure(monkeypatch):
    calls = {"n": 0}

    def _fake_run(*_args, **_kwargs):
        calls["n"] += 1

    def _fake_load(*_args, **_kwargs):
        return {"shots": [{"shot_id": "S001"}]}

    monkeypatch.setattr(codex_cli_client, "_run", _fake_run)
    monkeypatch.setattr(codex_cli_client, "_load_output", _fake_load)
    cfg = {"integrations": {}}
    schema = {
        "type": "object",
        "required": ["shots"],
        "properties": {
            "shots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["shot_id", "seed"],
                    "properties": {"shot_id": {"type": "string"}, "seed": {"type": "integer"}},
                },
            }
        },
    }
    with pytest.raises(CodexCliRequestError, match="schema validation failed"):
        codex_cli_client.generate_structured(cfg, "p", schema)
    assert calls["n"] == 1


def test_strict_schema_adds_additional_properties_false():
    raw = {
        "type": "object",
        "properties": {
            "inner": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
            }
        },
    }
    strict = codex_cli_client._strict_schema(raw)
    assert strict["additionalProperties"] is False
    assert strict["properties"]["inner"]["additionalProperties"] is False


def test_load_output_accepts_valid_json(tmp_path: Path):
    path = tmp_path / "output.json"
    data = {"ok": True}
    path.write_text(json.dumps(data), encoding="utf-8")
    out = codex_cli_client._load_output(path)
    assert out == data
