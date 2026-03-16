from __future__ import annotations

import json
import time
from typing import Any

import requests

from ai_mv.core.contracts.errors import ComfyRequestError


class RecoverableComfyError(ComfyRequestError):
    pass


def ping_comfy(base_url: str) -> bool:
    try:
        res = requests.get(f"{base_url.rstrip('/')}/history", timeout=3)
        if res.status_code != 200:
            return False
        return isinstance(res.json(), dict)
    except Exception:
        return False


def submit_workflow(base_url: str, workflow: dict[str, Any], timeout: int) -> dict:
    queued = _queue_prompt(base_url, workflow, timeout)
    prompt_id = _prompt_id_from_queue(queued)
    try:
        history = wait_history(base_url, prompt_id, timeout)
        _raise_if_execution_error(history, prompt_id)
        files = extract_files(history)
    except ComfyRequestError as exc:
        raise type(exc)(f"prompt_id={prompt_id}: {exc}") from exc
    except TimeoutError as exc:
        raise TimeoutError(f"Comfy workflow timed out: prompt_id={prompt_id}: {exc}") from exc
    return {"prompt_id": prompt_id, "history": history, "files": files}


def wait_history(
    base_url: str,
    prompt_id: str,
    timeout: int,
    max_transient_errors: int = 8,
) -> dict[str, Any]:
    start = time.time()
    url = f"{base_url.rstrip('/')}/history/{prompt_id}"
    sleep_sec = 0.4
    max_sleep_sec = 2.0
    transient_errors = 0
    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            raise TimeoutError(f"ComfyUI history timeout: {prompt_id}")
        remaining = max(0.0, timeout - elapsed)
        try:
            data = _safe_history_get(url, min(remaining, 10.0), prompt_id)
            transient_errors = 0
        except RecoverableComfyError as exc:
            transient_errors += 1
            if transient_errors > max_transient_errors:
                raise RecoverableComfyError(
                    f"Comfy history polling unstable after {max_transient_errors} retries: "
                    f"prompt_id={prompt_id}: {exc}"
                ) from exc
            backoff = min(2 ** transient_errors, 15)
            time.sleep(min(backoff, max(0.0, timeout - (time.time() - start))))
            continue
        record = data[prompt_id] if isinstance(data, dict) and prompt_id in data else {}
        if record:
            return record
        remaining = max(0.0, timeout - (time.time() - start))
        time.sleep(min(sleep_sec, remaining))
        sleep_sec = min(max_sleep_sec, sleep_sec * 1.2)


def extract_files(history: dict[str, Any]) -> list[str]:
    outputs = history.get("outputs")
    if not isinstance(outputs, dict) or not outputs:
        raise ComfyRequestError("Comfy history outputs missing")
    files: list[str] = []
    for _, node_out in outputs.items():
        if not isinstance(node_out, dict):
            continue
        files += _collect_file_entries(node_out.get("images", []))
        files += _collect_file_entries(node_out.get("gifs", []))
        files += _collect_file_entries(node_out.get("videos", []))
        files += _collect_file_entries(node_out.get("files", []))
        files += _collect_file_entries(node_out.get("audio", []))
    if not files:
        raise ComfyRequestError("Comfy workflow produced no files")
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
        if not isinstance(item, dict) or "filename" not in item:
            raise ComfyRequestError("Comfy output item missing filename")
        name = str(item["filename"])
        folder = str(item["subfolder"]).strip("/\\") if "subfolder" in item else ""
        out.append(f"{folder}/{name}" if folder else name)
    return out


def _prompt_id_from_queue(queued: dict[str, Any]) -> str:
    prompt_id = str(queued.get("prompt_id", "")).strip()
    if not prompt_id:
        raise ComfyRequestError("Comfy queue response missing prompt_id")
    return prompt_id


def _safe_history_get(url: str, timeout: float, prompt_id: str) -> dict[str, Any]:
    try:
        return _get_json(url, timeout)
    except (requests.RequestException, TimeoutError) as exc:
        raise RecoverableComfyError(f"Comfy history transient failure: prompt_id={prompt_id}: {exc}") from exc
    except Exception as exc:
        raise ComfyRequestError(f"Comfy history request failed: {prompt_id}: {exc}") from exc


def _get_json(url: str, timeout: float) -> dict[str, Any]:
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
