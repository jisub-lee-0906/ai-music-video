from pathlib import Path

import pytest

from ai_mv.core.stages.media_resolver import resolve_audio_path, resolve_clip_paths


def test_resolve_clip_paths_raises_on_missing(tmp_path: Path):
    cfg = {"integrations": {"comfyui_output_dir": str(tmp_path / "out")}}
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    with pytest.raises(RuntimeError):
        resolve_clip_paths(["missing.mp4"], cfg, run_dir)


def test_resolve_audio_path_raises_on_missing(tmp_path: Path):
    cfg = {"integrations": {"comfyui_output_dir": str(tmp_path / "out")}}
    with pytest.raises(Exception):
        resolve_audio_path("missing.wav", cfg)
