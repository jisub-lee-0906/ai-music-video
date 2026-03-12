from __future__ import annotations


DEFAULT_CONFIG: dict = {
    "audio": {
        "target_duration_sec": 200,
        "quality": "V0",
        "planner_attempts": 1,
        "language": "en",
    },
    "profile": "",
    "video": {"target": "1920x1080@24"},
    "render": {
        "tti_size": "1024x1024",
        "uso_size": "1024x1024",
        "wan_size": "640x640",
        "wan_max_clip_sec": 5.0,
        "wan_planner_batch_size": 20,
        "uso_planner_batch_size": 4,
        "strict_prompt_id_match": True,
    },
    "limits": {
        "timeout_seconds": 900,
    },
    "integrations": {
        "comfyui_base_url": "http://127.0.0.1:8188",
        "comfyui_input_dir": r"C:\Users\Desktop\Documents\ComfyUI\input",
        "comfyui_output_dir": r"C:\Users\Desktop\Documents\ComfyUI\output",
        "codex_cli_path": "",
        "codex_model": "gpt-5.4",
        "codex_timeout_structured_sec": 600,
        "workflows_dir": "workflows",
    },
    "runtime": {
        "template_hash_lock": False,
        "template_hashes": {},
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
