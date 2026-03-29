from pathlib import Path

import ai_mv.core.orchestration.bootstrap_guard as bootstrap_guard
from ai_mv.core.orchestration.transitions import bootstrap_config
from ai_mv.core.workflow_names import WORKFLOW_FILES


def test_bootstrap_applies_defaults_for_sparse_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        bootstrap_guard,
        "resolve_project_path",
        lambda rel: tmp_path / rel.replace("/", "\\"),
    )
    cfg = {
        "brief": "director",
        "integrations": {"workflows_dir": str(Path("workflows"))},
        "runtime": {"template_hash_lock": False, "template_hashes": {}},
    }
    (tmp_path / "workflows").mkdir()
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles" / "director.yaml").write_text(_director_brief_yaml(), encoding="utf-8")
    for name in WORKFLOW_FILES:
        (tmp_path / "workflows" / name).write_text("{}", encoding="utf-8")
    out = bootstrap_config(cfg, tmp_path / "artifacts")
    assert out["video"]["target"] == "1920x1080@24"
    assert out["render"]["wan_size"] == "896x512"
    assert out["audio"]["language"] == "ko"


def test_apply_director_brief_merges_example_style_input(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        bootstrap_guard,
        "resolve_project_path",
        lambda rel: tmp_path / rel.replace("/", "\\"),
    )
    cfg = {
        "brief": "director",
        "integrations": {"workflows_dir": str(Path("workflows"))},
        "video": {"target": "1920x1080@24"},
        "render": {"tti_size": "1024x576", "ref_size": "1024x576", "wan_size": "896x504"},
        "runtime": {"template_hash_lock": False, "template_hashes": {}},
    }
    (tmp_path / "profiles").mkdir(parents=True)
    (tmp_path / "profiles" / "director.yaml").write_text(_director_brief_yaml(), encoding="utf-8")

    bootstrap_guard.apply_director_brief(cfg)

    assert cfg["audio"]["brief"] == "Director audio brief"
    assert cfg["character"]["identity_core"] == "Korean female idol"
    assert cfg["director"]["target_style"] == "cinematic live-action music video"


def _director_brief_yaml() -> str:
    return (
        "audio:\n"
        "  language: ko\n"
        "  brief: Director audio brief\n"
        "  hook_brief: Director hook brief\n"
        "visual:\n"
        "  brief: Director visual brief\n"
        "  negative: Avoid drift\n"
        "mv:\n"
        "  story_world: One connected night block\n"
        "  action_vocabulary: Threshold turns and reflected motion\n"
        "  payoff_style: Motif system peak\n"
        "  outro_feel: lingering after-image\n"
        "  avoid: random spectacle\n"
        "character:\n"
        "  identity_core: Korean female idol\n"
        "director:\n"
        "  target_style: cinematic live-action music video\n"
        "  world_core: layered city night\n"
        "  camera_bias: readable cinematic framing\n"
        "  lighting_bias: directional sign glow\n"
        "  motion_bias: stable cinematic movement\n"
    )
