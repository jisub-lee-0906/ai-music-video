from __future__ import annotations

import os


DEFAULT_CONFIG: dict = {
    "audio": {
        "quality": "V0",
        "language": "",
        "beats_per_bar": 4,
        "target_duration_min_sec": 150,
        "target_duration_max_sec": 180,
        "brief": "",
        "hook_brief": "",
    },
    "concept_text": "emotionally resonant night-drive music video concept with a vivid urban atmosphere",
    "video": {"target": "1920x1080@24"},
    "render": {
        "flux2_size": "1280x720",
        "ltx_ia2v_size": "1280x720",
        "ltx_fps": 24,
        "ltx_default_shot_sec": 4.0,
        "ltx_negative": "pc game, console game, video game, cartoon, childish, ugly",
        "cleanup_between_clips": False,
    },
    "limits": {
        "timeout_seconds": 0,
        "ltx_timeout_seconds": 1800,
    },
    "integrations": {
        "comfyui_base_url": None,
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
        "interrupt_comfy_before_start": False,
        "clear_comfy_queue_before_start": False,
    },
    "review": {
        "max_rerender_targets": 3,
        "quality_findings_path": "",
    },
    "planning": {
        "enable_ia2v": True,
        "max_shot_sec": 8.0,
        "max_ia2v_shots": 2,
        "ia2v_min_sec": 4.0,
        "ia2v_max_sec": 8.0,
    },
}


def default_config() -> dict:
    cfg = _clone(DEFAULT_CONFIG)
    cfg["integrations"]["comfyui_base_url"] = _default_comfyui_base_url()
    _apply_runtime_env_overrides(cfg)
    return cfg


def apply_defaults(config: dict) -> None:
    _deep_fill(config, DEFAULT_CONFIG)
    integrations = config.get("integrations")
    if isinstance(integrations, dict) and not str(integrations.get("comfyui_base_url") or "").strip():
        integrations["comfyui_base_url"] = _default_comfyui_base_url()
    _apply_runtime_env_overrides(config)


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


def _apply_runtime_env_overrides(config: dict) -> None:
    runtime = config.get("runtime")
    if isinstance(runtime, dict):
        runtime["interrupt_comfy_before_start"] = _env_bool(
            "AI_MV_INTERRUPT_COMFY_BEFORE_START",
            bool(runtime.get("interrupt_comfy_before_start", False)),
        )
        runtime["clear_comfy_queue_before_start"] = _env_bool(
            "AI_MV_CLEAR_COMFY_QUEUE_BEFORE_START",
            bool(runtime.get("clear_comfy_queue_before_start", False)),
        )
    render = config.get("render")
    if isinstance(render, dict):
        render["cleanup_between_clips"] = _env_bool(
            "AI_MV_CLEANUP_BETWEEN_CLIPS",
            bool(render.get("cleanup_between_clips", False)),
        )


def _env_bool(name: str, default: bool) -> bool:
    raw = str(os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _default_comfyui_base_url() -> str:
    explicit = str(os.getenv("AI_MV_COMFY_BASE_URL") or "").strip()
    if explicit:
        return explicit
    host = str(os.getenv("AI_MV_COMFY_HOST") or "").strip() or "127.0.0.1"
    return f"http://{host}:8000"
