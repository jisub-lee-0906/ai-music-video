from __future__ import annotations

import json

import requests

from ai_mv.infra.http_retry import with_retry


def ping_ollama(base_url: str) -> bool:
    try:
        return requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=3).status_code < 500
    except Exception:
        return False


def generate_structured(config: dict, prompt: str, schema: dict) -> dict:
    integ = config["integrations"]
    base = str(integ["ollama_base_url"]).rstrip("/")
    model = str(integ["ollama_model"])
    timeout = int(integ["ollama_timeout_structured_sec"])
    def _call() -> dict:
        res = requests.post(
            f"{base}/api/generate",
            json=_payload(config, model, prompt, schema),
            timeout=timeout,
        )
        res.raise_for_status()
        body = res.json()
        text = str(body["response"])
        return json.loads(text)

    attempts = _ollama_retry_attempts(config)
    return with_retry(_call, attempts=attempts)


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


def _ollama_retry_attempts(config: dict) -> int:
    integ = config.get("integrations", {}) if isinstance(config, dict) else {}
    raw = integ.get("ollama_retry_attempts", 1) if isinstance(integ, dict) else 1
    try:
        n = int(raw)
    except Exception:
        return 1
    return max(1, n)
