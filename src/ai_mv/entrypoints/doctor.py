from __future__ import annotations

from ai_mv.core.orchestration.config_loader import load_config
from ai_mv.infra.comfy_client import ping_comfy
from ai_mv.infra.codex_cli_client import assert_codex_ready, ping_codex
from ai_mv.infra.doctor_checks import assert_runtime_ready


def run_doctor(config_path: str | None = None) -> int:
    cfg = load_config(config_path)
    assert_runtime_ready(cfg)
    assert_codex_ready(cfg)
    comfy_ok = ping_comfy(cfg["integrations"]["comfyui_base_url"])
    codex_ok = ping_codex()
    print(f"comfyui={comfy_ok} codex={codex_ok}")
    return 0 if comfy_ok and codex_ok else 1
