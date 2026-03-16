from pathlib import Path

import ai_mv.core.orchestration.bootstrap_guard as bootstrap_guard
from ai_mv.core.orchestration.transitions import bootstrap_config
from ai_mv.core.workflow_names import WORKFLOW_FILES


def test_bootstrap_applies_profile_audio_and_style(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        bootstrap_guard,
        "resolve_project_path",
        lambda rel: tmp_path / rel.replace("/", "\\"),
    )
    cfg = {
        "profile": "city",
        "integrations": {"workflows_dir": str(Path("workflows"))},
        "video": {"target": "1920x1080@24"},
        "render": {"tti_size": "1024x1024", "wan_size": "640x640"},
        "runtime": {"template_hash_lock": False, "template_hashes": {}},
    }
    (tmp_path / "workflows").mkdir()
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir(parents=True)
    (profile_dir / "city.yaml").write_text(_profile_yaml(), encoding="utf-8")
    for name in _wf_names():
        (tmp_path / "workflows" / name).write_text("{}", encoding="utf-8")
    run_dir = tmp_path / "artifacts" / "runs_state" / "x"
    run_dir.mkdir(parents=True)
    out = bootstrap_config(cfg, run_dir)
    assert out["audio"]["tags"] == ["city pop", "female vocal"]
    assert out["audio"]["brief"] == "City-pop briefing"
    assert out["visual"]["brief"] == "Night city visual briefing"


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
    assert out["render"]["wan_size"] == "896x512"
    assert int(out["limits"]["timeout_seconds"]) == 900
    assert "audio" in out and "quality" in out["audio"]
    assert out["audio"]["language"] == "en"


def _wf_names() -> list[str]:
    return list(WORKFLOW_FILES)


def _profile_yaml() -> str:
    return (
        "audio:\n"
        "  language: ja\n"
        "  brief: City-pop briefing\n"
        "  hook_brief: Hook briefing\n"
        "  tags:\n"
        "    - city pop\n"
        "    - female vocal\n"
        "visual:\n"
        "  brief: Night city visual briefing\n"
        "  negative: Avoid drift\n"
        "mv:\n"
        "  story_world: One small city night\n"
        "  action_vocabulary: Slow pass, reflection check\n"
        "  payoff_style: Open, resolved return\n"
        "  outro_feel: Final look seals the night\n"
        "  avoid: Random spectacle\n"
    )
