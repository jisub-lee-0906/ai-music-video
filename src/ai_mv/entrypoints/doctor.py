from __future__ import annotations

from ai_mv.core.state.state_store import load_config
from ai_mv.infra.comfy_client import ping_comfy
from ai_mv.infra.doctor_checks import assert_runtime_ready
from ai_mv.infra.ollama_client import assert_ollama_ready, ping_ollama


def run_doctor(config_path: str) -> int:
    cfg = load_config(config_path)
    assert_runtime_ready(cfg)
    assert_ollama_ready(cfg)
    comfy_ok = ping_comfy(cfg["integrations"]["comfyui_base_url"])
    ollama_ok = ping_ollama(cfg["integrations"]["ollama_base_url"])
    print(f"comfyui={comfy_ok} ollama={ollama_ok}")
    return 0 if comfy_ok and ollama_ok else 1
