from ai_mv.cli.args import build_parser


def test_parser_has_commands():
    parser = build_parser()
    assert parser is not None
    names = parser._subparsers._group_actions[0].choices.keys()  # type: ignore[attr-defined]
    assert "start" in names


def test_start_accepts_profile():
    parser = build_parser()
    args = parser.parse_args(["start", "--config", "configs/default.yaml", "--profile", "jpop_citypop"])
    assert args.profile == "jpop_citypop"

