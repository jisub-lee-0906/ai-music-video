from ai_mv.cli.args import build_parser
from ai_mv.core.orchestration.config_defaults import default_config


def test_parser_has_v2_commands_only():
    parser = build_parser()
    names = parser._subparsers._group_actions[0].choices.keys()  # type: ignore[attr-defined]
    assert "start-v2" in names
    assert "preflight-v2" in names
    assert "start" not in names
    assert "preflight" not in names


def test_default_config_uses_brief_not_profile():
    cfg = default_config()
    assert "brief" in cfg
    assert "profile" not in cfg


def test_preflight_v2_accepts_brief():
    parser = build_parser()
    args = parser.parse_args(["preflight-v2", "--brief", "director_brief_example"])
    assert args.brief == "director_brief_example"


def test_start_v2_accepts_brief():
    parser = build_parser()
    args = parser.parse_args(["start-v2", "--brief", "director_brief_example"])
    assert args.brief == "director_brief_example"
