from __future__ import annotations

import json
import time
from typing import Any

import requests

from ai_mv.core.contracts.errors import ComfyRequestError, WorkflowValidationError
from ai_mv.infra.http_retry import with_retry
from ai_mv.infra.timeout_policy import resolve_timeout
from ai_mv.utils.path_utils import resolve_project_path


def ping_comfy(base_url: str) -> bool:
    try:
        return requests.get(f"{base_url.rstrip('/')}/history", timeout=3).status_code < 500
    except Exception:
        return False


def run_workflow(
    config: dict,
    workflow_name: str,
    bindings: dict[str, Any],
    required: dict[str, list[str]] | None = None,
) -> dict:
    base = config.get("integrations", {}).get("workflows_dir", "workflows")
    wf_path = resolve_project_path(base) / workflow_name
    workflow = json.loads(wf_path.read_text(encoding="utf-8"))
    if required:
        preflight_workflow(workflow, required)
    patched = patch_workflow(workflow, bindings)
    return submit(config, patched)


def submit(config: dict, workflow: dict[str, Any]) -> dict:
    base_url = config.get("integrations", {}).get("comfyui_base_url", "")
    timeout = resolve_timeout(config)
    strict = bool(config.get("integrations", {}).get("strict_remote", False))
    if not strict:
        return {"prompt_id": "mock", "mock": True}

    def _queue() -> dict:
        return _queue_prompt(base_url, workflow, timeout)

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


def _queue_prompt(base_url: str, workflow: dict[str, Any], timeout: int) -> dict:
    url = f"{base_url.rstrip('/')}/prompt"
    res = requests.post(url, json={"prompt": workflow}, timeout=timeout)
    if res.status_code >= 400:
        body = _safe_response_body(res)
        raise ComfyRequestError(f"Comfy prompt failed: {res.status_code} {body}")
    return res.json()


def _safe_response_body(res: requests.Response) -> str:
    try:
        return json.dumps(res.json(), ensure_ascii=False)
    except Exception:
        return (res.text or "").strip()[:800]


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
        folder = str(item.get("subfolder", "")).strip("/\\")
        if name:
            out.append(f"{folder}/{name}" if folder else name)
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
        _patch_audio_nodes(cls, inputs, bindings)
        _patch_common(cls, inputs, bindings)
        _patch_text_nodes(cls, node, inputs, bindings)
    return workflow


def _patch_audio_nodes(cls: str, inputs: dict, b: dict[str, Any]) -> None:
    if cls == "TextEncodeAceStepAudio1.5":
        _set_if_key(inputs, "tags", b, "audio.tags")
        _set_if_key(inputs, "lyrics", b, "audio.lyrics")
        _set_if_key(inputs, "seed", b, "audio.seed", int)
        _set_if_key(inputs, "bpm", b, "audio.bpm", int)
        _set_if_key(inputs, "duration", b, "audio.duration", int)
    if cls == "EmptyAceStep1.5LatentAudio":
        _set_if_key(inputs, "seconds", b, "audio.duration", int)
    if cls == "SaveAudioMP3":
        _set_if_key(inputs, "filename_prefix", b, "audio.filename_prefix")
        _set_if_key(inputs, "quality", b, "audio.quality")
    if cls == "KSampler":
        _set_if_key(inputs, "seed", b, "audio.seed", int)


def _patch_common(cls: str, inputs: dict, b: dict[str, Any]) -> None:
    if cls in {"KSampler", "KSamplerAdvanced"} and "shot.seed" in b:
        if "seed" in inputs:
            inputs["seed"] = int(b["shot.seed"])
        if "noise_seed" in inputs:
            inputs["noise_seed"] = int(b["shot.seed"]) + 17
    if cls in {"KSampler", "KSamplerAdvanced"} and "shot.steps" in b and "steps" in inputs:
        inputs["steps"] = int(b["shot.steps"])
    if cls in {"EmptySD3LatentImage", "WanFirstLastFrameToVideo"}:
        if "video.width" in b:
            inputs["width"] = int(b["video.width"])
        if "video.height" in b:
            inputs["height"] = int(b["video.height"])
    if cls == "WanFirstLastFrameToVideo" and "shot.length_frames" in b:
        inputs["length"] = int(b["shot.length_frames"])
    if cls == "CreateVideo" and "video.fps" in b:
        inputs["fps"] = int(b["video.fps"])
    if cls == "SaveImage" and "image.filename_prefix" in b:
        inputs["filename_prefix"] = str(b["image.filename_prefix"])
    if cls == "SaveVideo" and "video.filename_prefix" in b:
        inputs["filename_prefix"] = str(b["video.filename_prefix"])


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


def preflight_workflow(workflow: dict[str, Any], required: dict[str, list[str]]) -> None:
    for class_type, keys in (required or {}).items():
        node = _first_node_by_class(workflow, class_type)
        if not node:
            raise WorkflowValidationError(f"missing class_type: {class_type}")
        inputs = node.get("inputs", {}) if isinstance(node, dict) else {}
        missing = [k for k in keys if k not in inputs]
        if missing:
            raise WorkflowValidationError(f"missing inputs in {class_type}: {missing}")


def _first_node_by_class(workflow: dict[str, Any], class_type: str) -> dict | None:
    for node in workflow.values():
        if isinstance(node, dict) and node.get("class_type") == class_type:
            return node
    return None


def _set_if_key(inputs: dict, inp_key: str, bindings: dict, bind_key: str, cast=None) -> None:
    if bind_key not in bindings or inp_key not in inputs:
        return
    value = bindings[bind_key]
    inputs[inp_key] = cast(value) if cast else value
