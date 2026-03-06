from __future__ import annotations

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
    if parsed.hostname not in LOCAL_HOSTS:
        raise ComfyRequestError("comfyui_base_url must point to localhost")


def _require_dir(name: str, raw: str) -> Path:
    path = Path(raw.strip())
    if not raw.strip():
        raise ComfyRequestError(f"integrations.{name} is required")
    if not path.exists() or not path.is_dir():
        raise ComfyRequestError(f"integrations.{name} must be an existing directory")
    return path.resolve()
