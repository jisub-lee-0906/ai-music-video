from pathlib import Path

import pytest

from ai_mv.core.contracts.errors import MediaValidationError
from ai_mv.utils.path_utils import resolve_generated_file, stage_audio_for_comfy, stage_image_for_comfy


def test_stage_image_for_comfy_copies_into_input_dir(tmp_path):
    src = tmp_path / "frame.png"
    src.write_bytes(b"png")
    cfg = _config(tmp_path)
    rel = stage_image_for_comfy(cfg, str(src))
    assert rel.endswith("_frame.png")
    assert rel.startswith("_staged/")
    assert (tmp_path / "input" / rel).read_bytes() == b"png"


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


def test_stage_audio_for_comfy_uses_collision_safe_name_for_absolute_path(tmp_path):
    src = tmp_path / "song.wav"
    src.write_bytes(b"wav")
    cfg = _config(tmp_path)
    rel = stage_audio_for_comfy(cfg, str(src))
    assert rel.endswith("_song.wav")
    assert rel.startswith("_staged/")
    assert (tmp_path / "input" / rel).read_bytes() == b"wav"


def test_stage_image_for_comfy_avoids_absolute_basename_collision(tmp_path):
    cfg = _config(tmp_path)
    src_a = tmp_path / "a" / "frame.png"
    src_b = tmp_path / "b" / "frame.png"
    src_a.parent.mkdir()
    src_b.parent.mkdir()
    src_a.write_bytes(b"a")
    src_b.write_bytes(b"b")
    rel_a = stage_image_for_comfy(cfg, str(src_a))
    rel_b = stage_image_for_comfy(cfg, str(src_b))
    assert rel_a != rel_b
    assert (tmp_path / "input" / rel_a).read_bytes() == b"a"
    assert (tmp_path / "input" / rel_b).read_bytes() == b"b"


def test_resolve_generated_file_reads_from_comfy_output(tmp_path):
    cfg = _config(tmp_path)
    src = tmp_path / "output" / "audio.wav"
    src.write_bytes(b"wav")
    path = resolve_generated_file(cfg, "audio.wav", {".wav"}, "audio")
    assert path == src.resolve()


def test_resolve_generated_file_requires_explicit_relative_subpath(tmp_path):
    cfg = _config(tmp_path)
    nested = tmp_path / "output" / "clips" / "audio.wav"
    nested.parent.mkdir()
    nested.write_bytes(b"wav")
    with pytest.raises(MediaValidationError):
        resolve_generated_file(cfg, "audio.wav", {".wav"}, "audio")
    assert resolve_generated_file(cfg, "clips/audio.wav", {".wav"}, "audio") == nested.resolve()


def test_resolve_generated_file_normalizes_windows_style_relative_path(tmp_path):
    cfg = _config(tmp_path)
    nested = tmp_path / "output" / "prompt_lab" / "flux2_track_a" / "batch-1" / "F001_A1_s1001_00001_.png"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"png")

    path = resolve_generated_file(
        cfg,
        r"prompt_lab\flux2_track_a\batch-1/F001_A1_s1001_00001_.png",
        {".png"},
        "image",
    )

    assert path == nested.resolve()


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
