from __future__ import annotations


DEFAULT_CONFIG: dict = {
    "audio": {
        "lyrics": "",
        "song_title": "",
        "song_description": "",
        "target_duration_sec": 160,
        "keyscale": "",
        "seed": 31,
        "quality": "V0",
        "tags": [],
    },
    "profile": "",
    "style": {"guidance": ""},
    "video": {"target": "1920x1080@24"},
    "render": {
        "tti_size": "1024x576",
        "uso_size": "1024x576",
        "wan_size": "640x360",
        "wan_max_clip_sec": 5.0,
        "wan_planner_batch_size": 20,
        "uso_planner_batch_size": 4,
    },
    "limits": {
        "max_retries_per_shot": 1,
        "timeout_seconds": 900,
    },
    "integrations": {
        "comfyui_base_url": "http://127.0.0.1:8188",
        "comfyui_input_dir": "",
        "comfyui_output_dir": "",
        "ollama_base_url": "http://127.0.0.1:11434",
        "ollama_model": "qwen3:14b",
        "ollama_timeout_json_sec": 60,
        "ollama_timeout_structured_sec": 300,
        "comfy_retry_attempts": 1,
        "ollama_num_gpu": 0,
        "ollama_keep_alive": "0s",
        "ollama_retry_attempts": 1,
        "workflows_dir": "workflows",
        "strict_remote": True,
    },
    "runtime": {
        "bootstrap_missing_inputs": True,
        "template_hash_lock": False,
        "template_hashes": {},
    },
}


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
