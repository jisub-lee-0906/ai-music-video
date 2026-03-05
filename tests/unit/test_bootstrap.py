from pathlib import Path

from ai_mv.core.orchestration.transitions import bootstrap_config


def test_bootstrap_creates_lyrics_and_style(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = {
        "integrations": {"strict_remote": False, "workflows_dir": str(Path("workflows"))},
        "audio": {"lyrics_file": "lyrics.txt"},
        "video": {"target": "1920x1080@24"},
        "render": {"tti_size": "1024x576", "uso_size": "1024x576", "wan_size": "640x360"},
        "runtime": {"template_hash_lock": False, "bootstrap_missing_inputs": True},
        "consistency": {"reference_images": []},
    }
    (tmp_path / "workflows").mkdir()
    for name in _wf_names():
        (tmp_path / "workflows" / name).write_text("{}", encoding="utf-8")
    run_dir = tmp_path / "artifacts" / "runs_state" / "x"
    run_dir.mkdir(parents=True)
    out = bootstrap_config(cfg, run_dir)
    assert Path(out["audio"]["lyrics_file"]).exists()
    assert out["consistency"]["reference_images"]
    assert (run_dir / "run_style.json").exists()


def _wf_names() -> list[str]:
    return [
        "audio_ace_step_1_5_tta.api.json",
        "image_flux1_dev_tti.api.json",
        "image_flux1_dev_uso.api.json",
        "video_wan_2_2_flf2v.api.json",
    ]
