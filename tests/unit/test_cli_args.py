from ai_mv.cli.args import build_parser
from ai_mv.core.orchestration.config_defaults import default_config


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


def test_preflight_accepts_concept_text():
    parser = build_parser()
    args = parser.parse_args(["preflight", "--concept-text", "city pop night drive"])
    assert args.concept_text == "city pop night drive"


def test_start_accepts_concept_text():
    parser = build_parser()
    args = parser.parse_args(["start", "--concept-text", "city pop night drive"])
    assert args.concept_text == "city pop night drive"

