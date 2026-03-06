import pytest

import ai_mv.infra.ollama_client as ollama_client
from ai_mv.core.contracts.errors import OllamaRequestError


def test_assert_ollama_ready_requires_model(monkeypatch):
    monkeypatch.setattr(ollama_client, "_tags_response", lambda *_args, **_kwargs: {"models": [{"name": "qwen3:14b"}]})
    cfg = {"integrations": {"ollama_base_url": "http://127.0.0.1:11434", "ollama_model": "missing"}}
    with pytest.raises(OllamaRequestError, match="configured Ollama model missing"):
        ollama_client.assert_ollama_ready(cfg)


def test_generate_structured_validates_schema(monkeypatch):
    monkeypatch.setattr(
        ollama_client,
        "_generate_response",
        lambda *_args, **_kwargs: {"response": '{"shots":[{"shot_id":"S001"}]}'},
    )
    cfg = {"integrations": _integ()}
    schema = {
        "type": "object",
        "required": ["shots"],
        "properties": {
            "shots": {
                "type": "array",
                "items": {"type": "object", "required": ["shot_id", "seed"], "properties": {"shot_id": {"type": "string"}, "seed": {"type": "integer"}}},
            }
        },
    }
    with pytest.raises(OllamaRequestError, match="schema validation failed"):
        ollama_client.generate_structured(cfg, "p", schema)


def test_generate_structured_rejects_invalid_json(monkeypatch):
    monkeypatch.setattr(ollama_client, "_generate_response", lambda *_args, **_kwargs: {"response": "{oops"})
    cfg = {"integrations": _integ()}
    with pytest.raises(OllamaRequestError, match="invalid JSON"):
        ollama_client.generate_structured(cfg, "p", {"type": "object"})


def test_generate_structured_does_not_retry_schema_failure(monkeypatch):
    calls = {"n": 0}

    def _fake_generate(*_args, **_kwargs):
        calls["n"] += 1
        return {"response": '{"shots":[{"shot_id":"S001"}]}'}

    monkeypatch.setattr(ollama_client, "_generate_response", _fake_generate)
    cfg = {"integrations": {**_integ(), "ollama_retry_attempts": 3}}
    schema = {
        "type": "object",
        "required": ["shots"],
        "properties": {
            "shots": {
                "type": "array",
                "items": {"type": "object", "required": ["shot_id", "seed"], "properties": {"shot_id": {"type": "string"}, "seed": {"type": "integer"}}},
            }
        },
    }
    with pytest.raises(OllamaRequestError, match="schema validation failed"):
        ollama_client.generate_structured(cfg, "p", schema)
    assert calls["n"] == 1


def _integ() -> dict:
    return {
        "ollama_base_url": "http://127.0.0.1:11434",
        "ollama_model": "qwen3:14b",
        "ollama_timeout_structured_sec": 10,
        "ollama_num_gpu": 0,
        "ollama_keep_alive": "0s",
        "ollama_retry_attempts": 1,
    }
