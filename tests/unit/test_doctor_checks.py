from pathlib import Path

import pytest

from ai_mv.core.contracts.errors import PipelineError
from ai_mv.core.workflow_names import WORKFLOW_FILES
from ai_mv.infra.doctor_checks import assert_runtime_ready


def test_assert_runtime_ready_accepts_valid_setup(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    monkeypatch.setattr("ai_mv.infra.doctor_checks.shutil.which", lambda name: f"C:/bin/{name}.exe")
    monkeypatch.setattr("ai_mv.infra.doctor_checks.assert_ollama_ready", lambda _cfg: None)
    assert_runtime_ready(cfg)


def test_assert_runtime_ready_requires_ffmpeg(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    monkeypatch.setattr("ai_mv.infra.doctor_checks.shutil.which", lambda _name: None)
    monkeypatch.setattr("ai_mv.infra.doctor_checks.assert_ollama_ready", lambda _cfg: None)
    with pytest.raises(PipelineError, match="ffmpeg is required"):
        assert_runtime_ready(cfg)


def test_assert_runtime_ready_requires_workflows(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    monkeypatch.setattr("ai_mv.infra.doctor_checks.shutil.which", lambda name: f"C:/bin/{name}.exe")
    monkeypatch.setattr("ai_mv.infra.doctor_checks.assert_ollama_ready", lambda _cfg: None)
    (tmp_path / "workflows" / WORKFLOW_FILES[0]).unlink()
    with pytest.raises(PipelineError, match="missing workflow template"):
        assert_runtime_ready(cfg)


def test_assert_runtime_ready_requires_ollama_model(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    monkeypatch.setattr("ai_mv.infra.doctor_checks.shutil.which", lambda name: f"C:/bin/{name}.exe")
    monkeypatch.setattr(
        "ai_mv.infra.doctor_checks.assert_ollama_ready",
        lambda _cfg: (_ for _ in ()).throw(RuntimeError("ollama lyrics model is missing: qwen3.5:latest")),
    )
    with pytest.raises(PipelineError, match="ollama lyrics model is missing"):
        assert_runtime_ready(cfg)


def _config(tmp_path: Path) -> dict:
    inp = tmp_path / "input"
    out = tmp_path / "output"
    wf = tmp_path / "workflows"
    inp.mkdir()
    out.mkdir()
    wf.mkdir()
    for name in WORKFLOW_FILES:
        (wf / name).write_text("{}", encoding="utf-8")
    return {
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8188",
            "comfyui_input_dir": str(inp),
            "comfyui_output_dir": str(out),
            "ollama_base_url": "http://127.0.0.1:11434",
            "ollama_lyrics_model": "qwen3.5:latest",
            "workflows_dir": str(wf),
        }
    }
