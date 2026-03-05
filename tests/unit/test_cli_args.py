from ai_mv.cli.args import build_parser


def test_parser_has_commands():
    parser = build_parser()
    assert parser is not None
    names = parser._subparsers._group_actions[0].choices.keys()  # type: ignore[attr-defined]
    assert "start" in names
