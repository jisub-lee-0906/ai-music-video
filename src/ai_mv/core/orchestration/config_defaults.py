from __future__ import annotations


DEFAULT_CONFIG: dict = {
    "audio": {
        "quality": "V0",
        "language": "ja",
        "beats_per_bar": 4,
        "target_duration_min_sec": 150,
        "target_duration_max_sec": 180,
    },
    "concept_text": "Japanese 80s city pop night drive, neon coast, bittersweet summer romance",
    "video": {"target": "1920x1080@24"},
    "render": {
        "qwen_size": "1024x1024",
        "ltx_i2v_size": "1280x720",
        "ltx_ia2v_size": "1280x720",
        "ltx_flf2v_size": "1280x720",
        "ltx_fps": 24,
        "ltx_default_shot_sec": 4.0,
        "qwen_negative": "",
        "ltx_negative": "pc game, console game, video game, cartoon, childish, ugly",
    },
    "limits": {
        "timeout_seconds": 0,
        "ltx_timeout_seconds": 0,
    },
    "integrations": {
        "comfyui_base_url": "http://127.0.0.1:8000",
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
    "review": {
        "max_rerender_targets": 3,
    },
    "planning": {
        "enable_ia2v": False,
        "enable_flf2v": False,
        "max_shot_sec": 8.0,
        "max_ia2v_shots": 2,
        "ia2v_min_sec": 4.0,
        "ia2v_max_sec": 8.0,
        "max_flf2v_shots": 1,
        "flf2v_min_sec": 3.0,
        "flf2v_max_sec": 6.0,
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
