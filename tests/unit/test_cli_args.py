from ai_mv.cli.args import build_parser


def test_parser_has_commands():
    parser = build_parser()
    assert parser is not None

