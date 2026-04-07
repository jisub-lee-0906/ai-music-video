from __future__ import annotations


DEFAULT_CONFIG: dict = {
    "audio": {
        "quality": "V0",
        "language": "en",
        "beats_per_bar": 4,
    },
    "brief": "",
    "video": {"target": "1920x1080@24"},
    "render": {
        "tti_size": "1280x720",
        "ref_size": "1024x576",
        "wan_size": "768x432",
        "wan_max_clip_sec": 5.0,
        "wan_safe_max_gap_sec": 4.0,
        "wan_max_frames": 40,
        "wan_steps_low": 12,
        "wan_steps_normal": 14,
        "wan_steps_high": 16,
        "wan_planner_batch_size": 20,
        "flux2_ref_planner_batch_size": 4,
        "ref_naturalize": True,
        "wan_naturalize": True,
    },
    "limits": {
        "timeout_seconds": 0,
        "wan_timeout_seconds": 0,
    },
    "integrations": {
        "comfyui_base_url": "http://127.0.0.1:8188",
        "comfyui_input_dir": r"C:\Users\Desktop\Documents\ComfyUI\input",
        "comfyui_output_dir": r"C:\Users\Desktop\Documents\ComfyUI\output",
        "codex_cli_path": "",
        "codex_model": "gpt-5.4-mini",
        "codex_timeout_structured_sec": 0,
        "workflows_dir": "workflows",
    },
    "runtime": {
        "template_hash_lock": False,
        "template_hashes": {},
        "interrupt_comfy_before_start": True,
        "clear_comfy_queue_before_start": True,
    },
}


def default_config() -> dict:
    return _clone(DEFAULT_CONFIG)


def apply_defaults(config: dict) -> None:
    _deep_fill(config, DEFAULT_CONFIG)


def _deep_fill(target: dict, defaults: dict) -> None:
    for key, val in defaults.items():
        if key not in target:
            target[key] = _clone(val)
            continue
        if isinstance(val, dict) and isinstance(target.get(key), dict):
            _deep_fill(target[key], val)


def _clone(value):
    if isinstance(value, dict):
        return {k: _clone(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clone(v) for v in value]
    return value
