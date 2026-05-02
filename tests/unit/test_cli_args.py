import pytest
from pathlib import Path

from ai_mv.cli.args import build_parser
from ai_mv.core.orchestration.config_defaults import default_config
from ai_mv.core.workflow_names import FLUX2_KEYFRAME_WORKFLOW, FLUX2_STILL_WORKFLOW



def test_parser_exposes_only_canonical_public_commands():
    parser = build_parser()
    names = set(parser._subparsers._group_actions[0].choices.keys())  # type: ignore[attr-defined]
    assert names == {"start", "preflight", "doctor", "status", "validate-latest"}



def test_default_config_uses_concept_text_not_profile():
    cfg = default_config()
    assert "concept_text" in cfg
    assert "profile" not in cfg
    assert "city pop" not in str(cfg["concept_text"]).lower()



def test_default_config_sets_flux2_size_and_flux_workflows_for_stills():
    cfg = default_config()
    assert cfg["render"]["flux2_size"] == "1280x720"
    assert "flux2_negative" not in cfg["render"]
    assert FLUX2_STILL_WORKFLOW == "image_flux2_text_to_image.json"
    assert FLUX2_KEYFRAME_WORKFLOW == "image_flux2.json"



def test_default_config_exposes_only_current_video_controls_in_current_canon():
    cfg = default_config()
    assert cfg["render"]["flux2_size"] == "1280x720"
    assert cfg["render"]["ltx_ia2v_size"] == "1280x720"
    assert cfg["render"]["ltx_fps"] == 24
    assert cfg["render"]["ltx_default_shot_sec"] == 4.0
    assert cfg["render"]["ltx_negative"] == "pc game, console game, video game, cartoon, childish, ugly"
    assert set(cfg["render"]) == {"flux2_size", "ltx_ia2v_size", "ltx_fps", "ltx_default_shot_sec", "ltx_negative"}
    assert cfg["planning"] == {
        "enable_ia2v": True,
        "max_shot_sec": 8.0,
        "max_ia2v_shots": 2,
        "ia2v_min_sec": 4.0,
        "ia2v_max_sec": 8.0,
    }



def test_sample_config_uses_flux2_keys_and_matches_current_video_schema():
    text = Path("docs/sample-config.yaml").read_text(encoding="utf-8")
    assert "flux2_size:" in text
    assert "qwen_size:" not in text
    assert "qwen_negative:" not in text
    assert "ltx_ia2v_size:" in text
    assert "max_ia2v_shots:" in text



def test_sample_config_does_not_hardcode_lyrics_language_or_override_default_concept_bias():
    text = Path("docs/sample-config.yaml").read_text(encoding="utf-8")
    assert 'language: "ja"' not in text
    assert 'language: ""' in text
    assert 'city pop' not in text.lower()
    assert 'citypop' not in text.lower()



def test_preflight_accepts_concept_text():
    parser = build_parser()
    args = parser.parse_args(["preflight", "--concept-text", "city pop night drive"])
    assert args.concept_text == "city pop night drive"



def test_preflight_rejects_legacy_brief_flags():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["preflight", "--brief", "director brief"])

    with pytest.raises(SystemExit):
        parser.parse_args(["preflight", "--audio-brief", "music-facing brief"])

    with pytest.raises(SystemExit):
        parser.parse_args(["preflight", "--audio-hook-brief", "title-grade hook"])



def test_start_accepts_concept_text():
    parser = build_parser()
    args = parser.parse_args(["start", "--concept-text", "city pop night drive"])
    assert args.concept_text == "city pop night drive"



def test_start_rejects_legacy_brief_flags():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["start", "--brief", "director brief"])

    with pytest.raises(SystemExit):
        parser.parse_args(["start", "--audio-brief", "music-facing brief"])

    with pytest.raises(SystemExit):
        parser.parse_args(["start", "--audio-hook-brief", "title-grade hook"])
