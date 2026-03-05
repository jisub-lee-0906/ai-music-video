from __future__ import annotations

import json
import time
from typing import Any

import requests

from ai_mv.core.contracts.errors import ComfyRequestError
from ai_mv.infra.http_retry import with_retry


def ping_comfy(base_url: str) -> bool:
    try:
        return requests.get(f"{base_url.rstrip('/')}/history", timeout=3).status_code < 500
    except Exception:
        return False


def submit_workflow(base_url: str, workflow: dict[str, Any], timeout: int) -> dict:
    queued = with_retry(lambda: _queue_prompt(base_url, workflow, timeout))
    prompt_id = str(queued.get("prompt_id", ""))
    if not prompt_id:
        return queued
    history = wait_history(base_url, prompt_id, timeout)
    return {"prompt_id": prompt_id, "history": history, "files": extract_files(history)}


def wait_history(base_url: str, prompt_id: str, timeout: int) -> dict[str, Any]:
    start = time.time()
    url = f"{base_url.rstrip('/')}/history/{prompt_id}"
    while True:
        data = with_retry(lambda: _get_json(url, timeout))
        record = data.get(prompt_id, {}) if isinstance(data, dict) else {}
        if record:
            return record
        if time.time() - start > timeout:
            raise TimeoutError(f"ComfyUI history timeout: {prompt_id}")
        time.sleep(1.0)


def extract_files(history: dict[str, Any]) -> list[str]:
    outputs = history.get("outputs", {})
    files: list[str] = []
    for _, node_out in outputs.items():
        if not isinstance(node_out, dict):
            continue
        files += _collect_file_entries(node_out.get("images", []))
        files += _collect_file_entries(node_out.get("gifs", []))
        files += _collect_file_entries(node_out.get("audio", []))
    return files


def _queue_prompt(base_url: str, workflow: dict[str, Any], timeout: int) -> dict:
    url = f"{base_url.rstrip('/')}/prompt"
    res = requests.post(url, json={"prompt": workflow}, timeout=timeout)
    if res.status_code >= 400:
        raise ComfyRequestError(f"Comfy prompt failed: {res.status_code} {_safe_response_body(res)}")
    return res.json()


def _safe_response_body(res: requests.Response) -> str:
    try:
        return json.dumps(res.json(), ensure_ascii=False)
    except Exception:
        return (res.text or "").strip()[:800]


def _collect_file_entries(items: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for item in items or []:
        name = str(item.get("filename", ""))
        folder = str(item.get("subfolder", "")).strip("/\\")
        if name:
            out.append(f"{folder}/{name}" if folder else name)
    return out


def _get_json(url: str, timeout: int) -> dict[str, Any]:
    res = requests.get(url, timeout=timeout)
    res.raise_for_status()
    data = res.json()
    return data if isinstance(data, dict) else {}

