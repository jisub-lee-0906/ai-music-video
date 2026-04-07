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
    assert out["render"]["wan_size"] == "768x432"
    assert out["language"] == "ko"


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

    assert cfg["prompt"] == "Director audio brief"
    assert cfg["genre"] == "k-pop synth pop"
    assert cfg["voice"] == "solo female, airy and emotional"
    assert cfg["visual_concept"] == "Realistic cinematic city-night breakup video."
    assert cfg["locations"] == ["dim retro diner", "wet city street at night"]
    assert cfg["props"] == ["worn notebook", "coffee mug"]
    assert cfg["anchor_subject"] == "pretty young Korean female idol in her 20s"


def _director_brief_yaml() -> str:
    return (
        "prompt: Director audio brief\n"
        "genre: k-pop synth pop\n"
        "voice: solo female, airy and emotional\n"
        "language: ko\n"
        "visual_concept: Realistic cinematic city-night breakup video.\n"
        "locations:\n"
        "  - dim retro diner\n"
        "  - wet city street at night\n"
        "props:\n"
        "  - worn notebook\n"
        "  - coffee mug\n"
        "anchor_subject: pretty young Korean female idol in her 20s\n"
        "anchor_hair: long dark hair with soft volume\n"
        "anchor_top: fitted knit top with a short polished outer layer\n"
        "anchor_bottom: short skirt or slim premium denim bottom\n"
        "anchor_shoes: premium everyday sneakers\n"
        "anchor_pose: full-body standing pose, slight side angle, both hands visible, shoes fully visible\n"
        "anchor_background: plain neutral studio background, no props, no environmental elements\n"
    )
