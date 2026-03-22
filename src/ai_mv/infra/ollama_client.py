from __future__ import annotations

import json
from typing import Any

import requests


def generate_text(config: dict, prompt: str, *, system: str = "", options: dict[str, Any] | None = None) -> str:
    integrations = config.get("integrations", {}) if isinstance(config, dict) else {}
    base_url = str(integrations.get("ollama_base_url", "http://127.0.0.1:11434")).strip()
    model = str(integrations.get("ollama_lyrics_model", "qwen3:latest")).strip()
    if not base_url:
        raise RuntimeError("ollama base url is missing")
    if not model:
        raise RuntimeError("ollama lyrics model is missing")
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    if system.strip():
        payload["system"] = system.strip()
    if isinstance(options, dict) and options:
        payload["options"] = options
    try:
        res = requests.post(url, json=payload)
    except requests.RequestException as exc:
        raise RuntimeError(f"ollama request failed: {exc}") from exc
    if res.status_code >= 400:
        body = _safe_body(res)
        raise RuntimeError(f"ollama request failed: {res.status_code} {body}".strip())
    try:
        data = res.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError("ollama response was not valid json") from exc
    text = str(data.get("response", "")).strip()
    if not text:
        raise RuntimeError("ollama response was empty")
    return _strip_code_fence(text)


def _safe_body(res: requests.Response) -> str:
    try:
        return str(res.text).strip()
    except Exception:
        return ""


def _strip_code_fence(text: str) -> str:
    stripped = str(text).strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped
