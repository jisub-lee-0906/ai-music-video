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
    prompt_id = str(queued["prompt_id"])
    history = wait_history(base_url, prompt_id, timeout)
    _raise_if_execution_error(history, prompt_id)
    return {"prompt_id": prompt_id, "history": history, "files": extract_files(history)}


def wait_history(base_url: str, prompt_id: str, timeout: int) -> dict[str, Any]:
    start = time.time()
    url = f"{base_url.rstrip('/')}/history/{prompt_id}"
    sleep_sec = 0.4
    max_sleep_sec = 2.0
    while True:
        data = with_retry(lambda: _get_json(url, timeout))
        record = data[prompt_id] if isinstance(data, dict) and prompt_id in data else {}
        if record:
            return record
        elapsed = time.time() - start
        if elapsed > timeout:
            raise TimeoutError(f"ComfyUI history timeout: {prompt_id}")
        remaining = max(0.0, timeout - elapsed)
        time.sleep(min(sleep_sec, remaining))
        sleep_sec = min(max_sleep_sec, sleep_sec * 1.2)


def extract_files(history: dict[str, Any]) -> list[str]:
    outputs = history["outputs"]
    files: list[str] = []
    for _, node_out in outputs.items():
        if not isinstance(node_out, dict):
            continue
        files += _collect_file_entries(node_out["images"] if "images" in node_out else [])
        files += _collect_file_entries(node_out["gifs"] if "gifs" in node_out else [])
        files += _collect_file_entries(node_out["videos"] if "videos" in node_out else [])
        files += _collect_file_entries(node_out["files"] if "files" in node_out else [])
        files += _collect_file_entries(node_out["audio"] if "audio" in node_out else [])
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
    for item in items:
        name = str(item["filename"])
        folder = str(item["subfolder"]).strip("/\\") if "subfolder" in item else ""
        out.append(f"{folder}/{name}" if folder else name)
    return out


def _get_json(url: str, timeout: int) -> dict[str, Any]:
    res = requests.get(url, timeout=timeout)
    res.raise_for_status()
    data = res.json()
    if not isinstance(data, dict):
        raise ComfyRequestError("Comfy history response is not a dict")
    return data


def _raise_if_execution_error(history: dict[str, Any], prompt_id: str) -> None:
    status = history["status"] if isinstance(history, dict) and "status" in history else {}
    if not isinstance(status, dict):
        return
    if str(status.get("status_str", "")).lower() != "error":
        return
    messages = status["messages"] if "messages" in status and isinstance(status["messages"], list) else []
    for msg in reversed(messages):
        if not isinstance(msg, list) or len(msg) < 2:
            continue
        if str(msg[0]) != "execution_error" or not isinstance(msg[1], dict):
            continue
        node_id = str(msg[1].get("node_id", ""))
        node_type = str(msg[1].get("node_type", ""))
        exc = str(msg[1].get("exception_message", "unknown error")).strip()
        raise ComfyRequestError(f"Comfy execution_error prompt_id={prompt_id} node={node_id}/{node_type}: {exc}")
    raise ComfyRequestError(f"Comfy execution_error prompt_id={prompt_id}")
