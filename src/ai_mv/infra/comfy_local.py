from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from ai_mv.core.contracts.errors import ComfyRequestError

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def validate_local_comfy_config(config: dict) -> None:
    integ = _integrations(config)
    _validate_local_base_url(str(integ["comfyui_base_url"]))
    _require_dir("comfyui_input_dir", str(integ["comfyui_input_dir"]))
    _require_dir("comfyui_output_dir", str(integ["comfyui_output_dir"]))


def comfy_input_dir(config: dict) -> Path:
    return _require_dir("comfyui_input_dir", str(_integrations(config)["comfyui_input_dir"]))


def comfy_output_dir(config: dict) -> Path:
    return _require_dir("comfyui_output_dir", str(_integrations(config)["comfyui_output_dir"]))


def _integrations(config: dict) -> dict:
    integ = config.get("integrations")
    if not isinstance(integ, dict):
        raise ComfyRequestError("integrations config is required")
    return integ


def _validate_local_base_url(raw: str) -> None:
    url = raw.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ComfyRequestError("comfyui_base_url must use http or https")
    if parsed.hostname not in _allowed_comfy_hosts():
        raise ComfyRequestError("comfyui_base_url must point to localhost or the WSL Windows host")


def _allowed_comfy_hosts() -> set[str]:
    hosts = set(LOCAL_HOSTS)
    configured_host = str(os.getenv("AI_MV_COMFY_HOST") or "").strip()
    if configured_host:
        hosts.add(configured_host)
    gateway = _wsl_windows_gateway_host()
    if gateway:
        hosts.add(gateway)
    return hosts


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


def _require_dir(name: str, raw: str) -> Path:
    path = Path(raw.strip())
    if not raw.strip():
        raise ComfyRequestError(f"integrations.{name} is required")
    if not path.exists() or not path.is_dir():
        raise ComfyRequestError(f"integrations.{name} must be an existing directory")
    return path.resolve()
