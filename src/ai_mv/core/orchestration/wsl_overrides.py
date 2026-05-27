from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def apply_wsl_runtime_overrides(config: dict) -> dict:
    if not isinstance(config, dict) or not _is_wsl():
        return config
    integrations = config.get("integrations")
    if not isinstance(integrations, dict):
        return config

    base_url = str(integrations.get("comfyui_base_url") or "").strip()
    gateway = (
        os.getenv("AI_MV_COMFY_HOST")
        or _wsl_windows_gateway_host()
        or ""
    ).strip()
    explicit_base_url = str(os.getenv("AI_MV_COMFY_BASE_URL") or "").strip()
    if explicit_base_url and _needs_wsl_base_url_override(base_url):
        integrations["comfyui_base_url"] = explicit_base_url
    elif gateway and _needs_wsl_base_url_override(base_url):
        integrations["comfyui_base_url"] = f"http://{gateway}:8000"

    explicit_input = str(os.getenv("AI_MV_COMFY_INPUT_DIR") or _default_wsl_comfy_input_dir() or "").strip()
    explicit_output = str(os.getenv("AI_MV_COMFY_OUTPUT_DIR") or _default_wsl_comfy_output_dir() or "").strip()
    explicit_codex = str(os.getenv("AI_MV_CODEX_BIN") or _default_wsl_codex_bin() or "").strip()

    if explicit_input and _needs_wsl_path_override(str(integrations.get("comfyui_input_dir") or "")):
        integrations["comfyui_input_dir"] = explicit_input
    if explicit_output and _needs_wsl_path_override(str(integrations.get("comfyui_output_dir") or "")):
        integrations["comfyui_output_dir"] = explicit_output
    if explicit_codex and _needs_wsl_codex_override(str(integrations.get("codex_cli_path") or "")):
        integrations["codex_cli_path"] = explicit_codex

    if _smoke_mode_enabled():
        _apply_smoke_mode_overrides(config)

    return config


def _apply_smoke_mode_overrides(config: dict) -> None:
    audio = config.get("audio") if isinstance(config.get("audio"), dict) else {}
    planning = config.get("planning") if isinstance(config.get("planning"), dict) else {}

    min_sec = _env_int("AI_MV_SMOKE_AUDIO_MIN_SEC", default=15)
    max_sec = _env_int("AI_MV_SMOKE_AUDIO_MAX_SEC", default=20)
    if max_sec < min_sec:
        max_sec = min_sec

    audio["target_duration_min_sec"] = min_sec
    audio["target_duration_max_sec"] = max_sec
    planning["enable_ia2v"] = True

    config["audio"] = audio
    config["planning"] = planning


def _smoke_mode_enabled() -> bool:
    return str(os.getenv("AI_MV_WSL_SMOKE_MODE") or "").strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = str(os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    return value if value > 0 else default


def _needs_wsl_base_url_override(raw: str) -> bool:
    if not raw.strip():
        return True
    parsed = urlparse(raw.strip())
    host = (parsed.hostname or "").strip().lower()
    return host in _LOCAL_HOSTS


def _needs_wsl_path_override(raw: str) -> bool:
    value = raw.strip()
    if not value:
        return True
    return _is_windows_path(value)


def _needs_wsl_codex_override(raw: str) -> bool:
    value = raw.strip()
    if not value:
        return True
    return _is_windows_path(value) or value.lower().endswith((".cmd", ".bat"))


def _is_windows_path(raw: str) -> bool:
    value = raw.strip()
    if len(value) >= 3 and value[1] == ":" and value[2] in {"/", "\\"}:
        return True
    return value.startswith("\\\\")


def _default_wsl_comfy_input_dir() -> str | None:
    win_default = Path(r"C:\Users\Desktop\Documents\ComfyUI\input")
    if win_default.is_dir():
        return str(win_default)
    return _discover_wsl_comfy_dir("input")



def _default_wsl_comfy_output_dir() -> str | None:
    win_default = Path(r"C:\Users\Desktop\Documents\ComfyUI\output")
    if win_default.is_dir():
        return str(win_default)
    return _discover_wsl_comfy_dir("output")



def _discover_wsl_comfy_dir(kind: str, users_root: Path | None = None) -> str | None:
    root = users_root or Path("/mnt/c/Users")
    if not root.is_dir():
        return None
    normalized_kind = str(kind).strip().lower()
    if normalized_kind not in {"input", "output"}:
        return None
    for user_dir in sorted((path for path in root.iterdir() if path.is_dir()), key=lambda path: path.name.lower()):
        candidate = user_dir / "Documents" / "ComfyUI" / normalized_kind
        try:
            if candidate.is_dir():
                return str(candidate)
        except (OSError, PermissionError):
            continue
    return None



def _default_wsl_codex_bin() -> str | None:
    home_fallback = str((Path.home() / ".hermes" / "node" / "bin" / "codex")).strip()
    for raw in (
        os.getenv("AI_MV_CODEX_BIN"),
        shutil.which("codex"),
        home_fallback,
    ):
        candidate = str(raw or "").strip()
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None



def _wsl_windows_gateway_host() -> str | None:
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
        version = Path("/proc/version")
        if version.exists() and "microsoft" in version.read_text(encoding="utf-8", errors="ignore").lower():
            return True
    except Exception:
        pass
    return Path("/proc/sys/fs/binfmt_misc/WSLInterop").exists()
