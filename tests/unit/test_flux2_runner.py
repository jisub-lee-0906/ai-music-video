from pathlib import Path

import pytest

from ai_mv.core.contracts.errors import ComfyRequestError
from ai_mv.engines.flux2_image.runner import run_flux2_still


def test_run_flux2_still_recovers_when_comfy_history_outputs_are_missing(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    out = tmp_path / "output" / "prompt_lab" / "flux2_track_a" / "batch-1"
    out.mkdir(parents=True)
    expected = out / "F001_A1_s1001_00001_.png"
    expected.write_bytes(b"png")

    monkeypatch.setattr(
        "ai_mv.engines.flux2_image.runner.run_workflow",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ComfyRequestError("prompt_id=abc: Comfy history outputs missing")),
    )

    image_path = run_flux2_still(
        cfg,
        {
            "shot_id": "F001",
            "positive_prompt": "prompt",
            "filename_prefix": "prompt_lab/flux2_track_a/batch-1/F001_A1_s1001",
            "seed": 1001,
            "flux2_size": "1280x720",
        },
    )

    assert image_path == str(expected.resolve())


def _config(tmp_path: Path) -> dict:
    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    out.mkdir(exist_ok=True)
    return {
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8000",
            "comfyui_input_dir": str(inp),
            "comfyui_output_dir": str(out),
            "workflows_dir": "workflows",
        },
        "render": {"flux2_size": "1280x720"},
        "video": {"target": "1920x1080@24"},
    }
