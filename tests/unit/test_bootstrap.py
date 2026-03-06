from pathlib import Path

from ai_mv.core.orchestration.transitions import bootstrap_config


def test_bootstrap_keeps_existing_audio_and_style(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = {
        "profile": "",
        "integrations": {"workflows_dir": str(Path("workflows"))},
        "audio": {
            "lyrics": "manual lyrics",
            "song_title": "manual title",
            "song_description": "manual description",
            "target_duration_sec": 160,
            "keywords": [],
        },
        "style": {"guidance": "manual guidance"},
        "video": {"target": "1920x1080@24"},
        "render": {"tti_size": "1024x576", "uso_size": "1024x576", "wan_size": "640x360"},
        "runtime": {"template_hash_lock": False, "template_hashes": {}},
    }
    (tmp_path / "workflows").mkdir()
    for name in _wf_names():
        (tmp_path / "workflows" / name).write_text("{}", encoding="utf-8")
    run_dir = tmp_path / "artifacts" / "runs_state" / "x"
    run_dir.mkdir(parents=True)
    out = bootstrap_config(cfg, run_dir)
    assert out["audio"]["lyrics"] == "manual lyrics"
    assert out["style"]["guidance"] == "manual guidance"


def test_bootstrap_applies_defaults_for_sparse_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = {
        "integrations": {"workflows_dir": str(Path("workflows"))},
        "runtime": {"template_hash_lock": False, "template_hashes": {}},
    }
    (tmp_path / "workflows").mkdir()
    for name in _wf_names():
        (tmp_path / "workflows" / name).write_text("{}", encoding="utf-8")
    run_dir = tmp_path / "artifacts" / "runs_state" / "y"
    run_dir.mkdir(parents=True)
    out = bootstrap_config(cfg, run_dir)
    assert out["video"]["target"] == "1920x1080@24"
    assert out["render"]["wan_size"] == "640x360"
    assert int(out["limits"]["timeout_seconds"]) == 900
    assert "audio" in out and "quality" in out["audio"]


def _wf_names() -> list[str]:
    return [
        "audio_ace_step_1_5_tta.api.json",
        "image_flux1_dev_tti.api.json",
        "image_flux1_dev_uso.api.json",
        "video_wan_2_2_flf2v.api.json",
    ]
