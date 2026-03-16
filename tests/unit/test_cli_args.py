from ai_mv.core.orchestration.config_defaults import default_config
from ai_mv.cli.args import build_parser


def test_parser_has_commands():
    parser = build_parser()
    assert parser is not None
    names = parser._subparsers._group_actions[0].choices.keys()  # type: ignore[attr-defined]
    assert "start" in names


def test_start_accepts_profile():
    parser = build_parser()
    args = parser.parse_args(["start", "--profile", "citypop_glimmer"])
    assert args.profile == "citypop_glimmer"


def test_default_config_available():
    cfg = default_config()
    assert isinstance(cfg, dict)
    assert "integrations" in cfg

