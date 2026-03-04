from __future__ import annotations

import json

import requests

from ai_mv.infra.http_retry import with_retry


def ping_ollama(base_url: str) -> bool:
    try:
        return requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=3).status_code < 500
    except Exception:
        return False


def generate_json(config: dict, prompt: str) -> dict:
    integ = config.get("integrations", {})
    base = integ.get("ollama_base_url", "http://127.0.0.1:11434").rstrip("/")
    model = integ.get("ollama_model", "qwen2.5:14b-instruct")
    strict = bool(integ.get("strict_remote", False))
    if not strict:
        return {"mock": True, "prompt": prompt[:80]}

    def _call() -> dict:
        res = requests.post(
            f"{base}/api/generate",
            json={"model": model, "prompt": prompt, "format": "json", "stream": False},
            timeout=30,
        )
        res.raise_for_status()
        text = res.json().get("response", "{}")
        return json.loads(text)

    return with_retry(_call)


def generate_structured(config: dict, prompt: str, schema: dict) -> dict:
    integ = config.get("integrations", {})
    base = integ.get("ollama_base_url", "http://127.0.0.1:11434").rstrip("/")
    model = integ.get("ollama_model", "qwen2.5:14b-instruct")
    strict = bool(integ.get("strict_remote", False))
    if not strict:
        return {"mock": True, "prompt": prompt[:80], "schema": True}

    def _call() -> dict:
        res = requests.post(
            f"{base}/api/generate",
            json={"model": model, "prompt": prompt, "format": schema, "stream": False},
            timeout=45,
        )
        res.raise_for_status()
        text = res.json().get("response", "{}")
        return json.loads(text)

    return with_retry(_call)
