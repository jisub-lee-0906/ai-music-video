from pathlib import Path

import pytest

from ai_mv.core.contracts.errors import ComfyRequestError
from ai_mv.infra.comfy_local import validate_local_comfy_config


def test_validate_local_comfy_config_accepts_local_dirs(tmp_path):
    cfg = _config(tmp_path)
    validate_local_comfy_config(cfg)


def test_validate_local_comfy_config_rejects_remote_host(tmp_path):
    cfg = _config(tmp_path)
    cfg["integrations"]["comfyui_base_url"] = "http://192.168.0.10:8188"
    with pytest.raises(ComfyRequestError):
        validate_local_comfy_config(cfg)


def _config(tmp_path: Path) -> dict:
    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    out.mkdir()
    return {
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8188",
            "comfyui_input_dir": str(inp),
            "comfyui_output_dir": str(out),
        }
    }
