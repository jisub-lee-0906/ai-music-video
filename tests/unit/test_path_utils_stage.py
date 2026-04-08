from pathlib import Path

import pytest

from ai_mv.core.contracts.errors import MediaValidationError
from ai_mv.utils.path_utils import resolve_generated_file, stage_image_for_comfy


def test_stage_image_for_comfy_copies_into_input_dir(tmp_path):
    src = tmp_path / "frame.png"
    src.write_bytes(b"png")
    cfg = _config(tmp_path)
    rel = stage_image_for_comfy(cfg, str(src))
    assert rel == "frame.png"
    assert (tmp_path / "input" / "frame.png").read_bytes() == b"png"


def test_stage_image_for_comfy_raises_on_missing_source(tmp_path):
    cfg = _config(tmp_path)
    with pytest.raises(MediaValidationError):
        stage_image_for_comfy(cfg, "missing.png")


def test_stage_image_for_comfy_accepts_existing_input_file(tmp_path):
    cfg = _config(tmp_path)
    src = tmp_path / "input" / "frame.png"
    src.write_bytes(b"png")
    rel = stage_image_for_comfy(cfg, str(src))
    assert rel == "frame.png"
    assert src.read_bytes() == b"png"


def test_stage_image_for_comfy_rejects_parent_escape(tmp_path):
    cfg = _config(tmp_path)
    src = tmp_path / "output" / "frame.png"
    src.write_bytes(b"png")
    with pytest.raises(MediaValidationError, match="escapes comfy input dir"):
        stage_image_for_comfy(cfg, "../frame.png")


def test_resolve_generated_file_reads_from_comfy_output(tmp_path):
    cfg = _config(tmp_path)
    src = tmp_path / "output" / "audio.wav"
    src.write_bytes(b"wav")
    path = resolve_generated_file(cfg, "audio.wav", {".wav"}, "audio")
    assert path == src.resolve()


def _config(tmp_path: Path) -> dict:
    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    out.mkdir()
    return {
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8000",
            "comfyui_input_dir": str(inp),
            "comfyui_output_dir": str(out),
        }
    }
