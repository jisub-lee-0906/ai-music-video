from __future__ import annotations

import subprocess
from pathlib import Path


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
    },
    "limits": {
        "timeout_seconds": 0,
        "ltx_timeout_seconds": 0,
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
        "interrupt_comfy_before_start": True,
        "clear_comfy_queue_before_start": True,
    },
    "review": {
        "max_rerender_targets": 3,
        "quality_findings_path": "",
        "audio_review_rubric_path": "",
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
    return cfg


def apply_defaults(config: dict) -> None:
    _deep_fill(config, DEFAULT_CONFIG)
    integrations = config.get("integrations")
    if isinstance(integrations, dict) and not str(integrations.get("comfyui_base_url") or "").strip():
        integrations["comfyui_base_url"] = _default_comfyui_base_url()


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


def _default_comfyui_base_url() -> str:
    gateway = _wsl_windows_gateway_host()
    host = gateway or "127.0.0.1"
    return f"http://{host}:8000"


def _wsl_windows_gateway_host() -> str | None:
    if not _is_wsl():
        return None
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return None
    for line in result.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) >= 3 and parts[0] == "default" and parts[1] == "via":
            return parts[2].strip()
    return None


def _is_wsl() -> bool:
    try:
        version = Path('/proc/version')
        if version.exists() and 'microsoft' in version.read_text(encoding='utf-8', errors='ignore').lower():
            return True
    except Exception:
        pass
    return Path('/proc/sys/fs/binfmt_misc/WSLInterop').exists()
