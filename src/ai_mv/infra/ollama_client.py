from __future__ import annotations

import requests

from ai_mv.core.contracts.errors import OllamaRequestError
from ai_mv.infra.http_retry import with_retry
from ai_mv.infra.ollama_response import ensure_model_available, parse_structured_response


def ping_ollama(base_url: str) -> bool:
    try:
        _tags_response(base_url, timeout=3)
        return True
    except Exception:
        return False


def generate_structured(config: dict, prompt: str, schema: dict) -> dict:
    integ = config["integrations"]
    base = str(integ["ollama_base_url"]).rstrip("/")
    model = str(integ["ollama_model"])
    timeout = int(integ["ollama_timeout_structured_sec"])
    payload = _payload(config, model, prompt, schema)

    attempts = _ollama_retry_attempts(config)
    body = with_retry(lambda: _generate_response(base, payload, timeout), attempts=attempts)
    return parse_structured_response(body, schema)


def assert_ollama_ready(config: dict) -> None:
    integ = config["integrations"]
    base = str(integ["ollama_base_url"]).rstrip("/")
    model = str(integ["ollama_model"]).strip()
    if not model:
        raise OllamaRequestError("integrations.ollama_model is required")
    ensure_model_available(_tags_response(base, timeout=3), model)


def _payload(config: dict, model: str, prompt: str, fmt: str | dict) -> dict:
    integ = config["integrations"]
    num_gpu = int(integ["ollama_num_gpu"])
    keep_alive = str(integ["ollama_keep_alive"])
    return {
        "model": model,
        "prompt": prompt,
        "format": fmt,
        "stream": False,
        "keep_alive": keep_alive,
        "options": {"num_gpu": num_gpu},
    }


def _generate_response(base: str, payload: dict, timeout: int) -> dict:
    res = requests.post(f"{base}/api/generate", json=payload, timeout=timeout)
    if res.status_code >= 400:
        raise OllamaRequestError(f"Ollama generate failed: {res.status_code}")
    body = res.json()
    if not isinstance(body, dict):
        raise OllamaRequestError("Ollama generate response must be a dict")
    return body


def _tags_response(base_url: str, timeout: int) -> dict:
    res = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
    if res.status_code != 200:
        raise OllamaRequestError(f"Ollama tags failed: {res.status_code}")
    body = res.json()
    if not isinstance(body, dict):
        raise OllamaRequestError("Ollama tags response must be a dict")
    return body


def _ollama_retry_attempts(config: dict) -> int:
    integ = config.get("integrations", {}) if isinstance(config, dict) else {}
    raw = integ.get("ollama_retry_attempts", 1) if isinstance(integ, dict) else 1
    try:
        n = int(raw)
    except Exception:
        return 1
    return max(1, n)
