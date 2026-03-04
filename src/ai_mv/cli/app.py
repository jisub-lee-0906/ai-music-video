from __future__ import annotations

from ai_mv.cli.args import build_parser
from ai_mv.cli.commands import dispatch


def main() -> int:
    parser = build_parser()
    args = vars(parser.parse_args())
    command = args.pop("command")
    return dispatch(command, **args)


if __name__ == "__main__":
    raise SystemExit(main())

