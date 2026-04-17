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
        "integrations": {"workflows_dir": str(Path("workflows"))},
        "runtime": {"template_hash_lock": False, "template_hashes": {}},
    }
    (tmp_path / "workflows").mkdir()
    for name in WORKFLOW_FILES:
        (tmp_path / "workflows" / name).write_text("{}", encoding="utf-8")
    out = bootstrap_config(cfg, tmp_path / "artifacts")
    assert out["video"]["target"] == "1920x1080@24"
    assert out["render"]["qwen_size"] == "1280x720"
    assert out["render"]["ltx_i2v_size"] == "1280x720"
    assert out["concept_text"]


def test_apply_input_defaults_sets_generic_default_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        bootstrap_guard,
        "resolve_project_path",
        lambda rel: tmp_path / rel.replace("/", "\\"),
    )
    cfg = {
        "integrations": {"workflows_dir": str(Path("workflows"))},
        "video": {"target": "1920x1080@24"},
        "render": {
            "qwen_size": "1280x720",
            "ltx_i2v_size": "1280x720",
            "ltx_ia2v_size": "1280x720",
            "ltx_flf2v_size": "1280x720",
        },
        "runtime": {"template_hash_lock": False, "template_hashes": {}},
    }

    bootstrap_guard.apply_input_defaults(cfg)

    assert cfg["concept_text"] == bootstrap_guard.DEFAULT_CONCEPT
    assert "city pop" not in cfg["concept_text"].lower()
    assert "prompt" not in cfg
    assert "genre" not in cfg
    assert cfg.get("audio", {}) == {}


def test_apply_input_defaults_preserves_explicit_audio_language(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        bootstrap_guard,
        "resolve_project_path",
        lambda rel: tmp_path / rel.replace("/", "\\"),
    )
    cfg = {
        "concept_text": "neon heartbreak on a Seoul overpass",
        "audio": {"language": "ko"},
    }

    bootstrap_guard.apply_input_defaults(cfg)

    assert cfg["audio"]["language"] == "ko"
