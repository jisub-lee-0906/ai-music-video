from ai_mv.cli.args import build_parser
from ai_mv.core.orchestration.config_defaults import default_config
from ai_mv.core.workflow_names import QWEN_STILL_WORKFLOW


def test_parser_has_clean_commands():
    parser = build_parser()
    names = parser._subparsers._group_actions[0].choices.keys()  # type: ignore[attr-defined]
    assert "start" in names
    assert "preflight" in names
    assert "doctor" in names


def test_default_config_uses_concept_text_not_profile():
    cfg = default_config()
    assert "concept_text" in cfg
    assert "profile" not in cfg


def test_default_config_sets_qwen_negative_for_single_keyframe_stills():
    cfg = default_config()
    negative = str(cfg["render"]["qwen_negative"])
    assert cfg["render"]["qwen_size"] == "1280x720"
    assert QWEN_STILL_WORKFLOW == "template_qwen_image_illustration_lora.json"
    assert "comic panel" in negative
    assert "contact sheet" in negative
    assert "collage" in negative
    assert "split screen" in negative
    assert "storyboard" in negative
    assert "inset frame" in negative
    assert "picture-in-picture" in negative


def test_preflight_accepts_concept_text():
    parser = build_parser()
    args = parser.parse_args(["preflight", "--concept-text", "city pop night drive"])
    assert args.concept_text == "city pop night drive"


def test_preflight_accepts_audio_specific_briefs():
    parser = build_parser()
    args = parser.parse_args(
        [
            "preflight",
            "--audio-brief",
            "music-facing brief",
            "--audio-hook-brief",
            "title-grade hook",
        ]
    )
    assert args.audio_brief == "music-facing brief"
    assert args.audio_hook_brief == "title-grade hook"


def test_start_accepts_concept_text():
    parser = build_parser()
    args = parser.parse_args(["start", "--concept-text", "city pop night drive"])
    assert args.concept_text == "city pop night drive"


def test_start_accepts_audio_specific_briefs():
    parser = build_parser()
    args = parser.parse_args(
        [
            "start",
            "--audio-brief",
            "music-facing brief",
            "--audio-hook-brief",
            "title-grade hook",
        ]
    )
    assert args.audio_brief == "music-facing brief"
    assert args.audio_hook_brief == "title-grade hook"

