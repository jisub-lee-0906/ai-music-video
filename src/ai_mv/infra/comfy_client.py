from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests

from ai_mv.infra.http_retry import with_retry
from ai_mv.infra.timeout_policy import resolve_timeout


def ping_comfy(base_url: str) -> bool:
    try:
        return requests.get(f"{base_url.rstrip('/')}/history", timeout=3).status_code < 500
    except Exception:
        return False


def run_workflow(config: dict, workflow_name: str, bindings: dict[str, Any]) -> dict:
    base = config.get("integrations", {}).get("workflows_dir", "workflows")
    wf_path = Path(base) / workflow_name
    workflow = json.loads(wf_path.read_text(encoding="utf-8"))
    patched = patch_workflow(workflow, bindings)
    return submit(config, patched)


def submit(config: dict, workflow: dict[str, Any]) -> dict:
    base_url = config.get("integrations", {}).get("comfyui_base_url", "")
    timeout = resolve_timeout(config)
    strict = bool(config.get("integrations", {}).get("strict_remote", False))
    if not strict:
        return {"prompt_id": "mock", "mock": True}

    def _queue() -> dict:
        res = requests.post(f"{base_url.rstrip('/')}/prompt", json={"prompt": workflow}, timeout=timeout)
        res.raise_for_status()
        return res.json()

    queued = with_retry(_queue)
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


def _collect_file_entries(items: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for item in items or []:
        name = str(item.get("filename", ""))
        if name:
            out.append(name)
    return out


def _get_json(url: str, timeout: int) -> dict[str, Any]:
    res = requests.get(url, timeout=timeout)
    res.raise_for_status()
    data = res.json()
    return data if isinstance(data, dict) else {}


def patch_workflow(workflow: dict[str, Any], bindings: dict[str, Any]) -> dict[str, Any]:
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        cls = str(node.get("class_type", ""))
        inputs = node.get("inputs", {})
        _patch_common(cls, inputs, bindings)
        _patch_text_nodes(cls, node, inputs, bindings)
    return workflow


def _patch_common(cls: str, inputs: dict, b: dict[str, Any]) -> None:
    if cls in {"KSampler", "KSamplerAdvanced"} and "shot.seed" in b:
        if "seed" in inputs:
            inputs["seed"] = int(b["shot.seed"])
        if "noise_seed" in inputs:
            inputs["noise_seed"] = int(b["shot.seed"]) + 17
    if cls == "EmptySD3LatentImage":
        if "video.width" in b:
            inputs["width"] = int(b["video.width"])
        if "video.height" in b:
            inputs["height"] = int(b["video.height"])
    if cls == "CreateVideo" and "video.fps" in b:
        inputs["fps"] = int(b["video.fps"])


def _patch_text_nodes(cls: str, node: dict, inputs: dict, b: dict[str, Any]) -> None:
    if cls == "CLIPTextEncodeFlux":
        inputs["clip_l"] = b.get("shot.prompt", inputs.get("clip_l", ""))
        inputs["t5xxl"] = b.get("shot.prompt", inputs.get("t5xxl", ""))
    if cls == "CLIPTextEncode":
        title = str(node.get("_meta", {}).get("title", "")).lower()
        if "negative" in title:
            inputs["text"] = b.get("shot.negative_prompt", inputs.get("text", ""))
        else:
            inputs["text"] = b.get("shot.prompt", inputs.get("text", ""))
    if cls == "LoadImage" and "image" in inputs:
        cur = str(inputs["image"]).lower()
        if "start_image" in cur:
            inputs["image"] = b.get("shot.start_image", inputs["image"])
        elif "end_image" in cur:
            inputs["image"] = b.get("shot.end_image", inputs["image"])
        elif "shot.reference_image" in b:
            inputs["image"] = b["shot.reference_image"]
