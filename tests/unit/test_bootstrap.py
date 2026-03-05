from pathlib import Path

from ai_mv.core.orchestration.transitions import bootstrap_config
import ai_mv.core.orchestration.bootstrap_content as content


def test_bootstrap_creates_lyrics_and_style(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(content, "generate_structured", _fake_generate)
    cfg = {
        "profile": "",
        "integrations": {"strict_remote": True, "workflows_dir": str(Path("workflows"))},
        "audio": {
            "lyrics": "",
            "song_title": "",
            "song_description": "",
            "target_duration_sec": 160,
            "keywords": [],
        },
        "style": {"guidance": ""},
        "video": {"target": "1920x1080@24"},
        "render": {"tti_size": "1024x576", "uso_size": "1024x576", "wan_size": "640x360"},
        "runtime": {"template_hash_lock": False, "template_hashes": {}, "bootstrap_missing_inputs": True},
    }
    (tmp_path / "workflows").mkdir()
    for name in _wf_names():
        (tmp_path / "workflows" / name).write_text("{}", encoding="utf-8")
    run_dir = tmp_path / "artifacts" / "runs_state" / "x"
    run_dir.mkdir(parents=True)
    out = bootstrap_config(cfg, run_dir)
    assert str(out["audio"].get("lyrics", "")).strip()
    assert isinstance(out["audio"].get("lyrics_structured", {}), dict)
    assert (run_dir / "run_style.json").exists()


def _fake_generate(_config, prompt, _schema):
    if "lyrics_blocks" in prompt:
        return {
            "title": "t",
            "description": "d",
            "lyrics_blocks": [{"section": "verse", "label": "Verse 1", "lines": ["line 1"]}],
        }
    return {"guidance": "cinematic live action"}


def _wf_names() -> list[str]:
    return [
        "audio_ace_step_1_5_tta.api.json",
        "image_flux1_dev_tti.api.json",
        "image_flux1_dev_uso.api.json",
        "video_wan_2_2_flf2v.api.json",
    ]
