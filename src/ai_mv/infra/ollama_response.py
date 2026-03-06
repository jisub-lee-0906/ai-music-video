from __future__ import annotations

import json

from jsonschema import ValidationError, validate

from ai_mv.core.contracts.errors import OllamaRequestError


def parse_structured_response(body: dict, schema: dict) -> dict:
    data = _decode_response_json(body)
    _validate_schema(data, schema)
    return data


def ensure_model_available(body: dict, model: str) -> None:
    models = _model_names(body)
    if model not in models:
        raise OllamaRequestError(f"configured Ollama model missing: {model}")


def _decode_response_json(body: dict) -> dict:
    if not isinstance(body, dict):
        raise OllamaRequestError("Ollama response body must be a dict")
    text = str(body.get("response", "")).strip()
    if not text:
        raise OllamaRequestError("Ollama response missing structured payload")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OllamaRequestError(f"Ollama returned invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise OllamaRequestError("Ollama structured payload must be a JSON object")
    return data


def _validate_schema(data: dict, schema: dict) -> None:
    try:
        validate(instance=data, schema=schema)
    except ValidationError as exc:
        path = ".".join(str(x) for x in exc.absolute_path)
        loc = f" at {path}" if path else ""
        raise OllamaRequestError(f"Ollama schema validation failed{loc}: {exc.message}") from exc


def _model_names(body: dict) -> set[str]:
    if not isinstance(body, dict):
        raise OllamaRequestError("Ollama tags response must be a dict")
    raw = body.get("models", [])
    if not isinstance(raw, list):
        raise OllamaRequestError("Ollama tags response models must be a list")
    out: set[str] = set()
    for row in raw:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        if name:
            out.add(name)
    return out
