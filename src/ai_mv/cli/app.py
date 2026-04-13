from __future__ import annotations

import sys
from ai_mv.cli.args import build_parser
from ai_mv.cli.commands import dispatch


def main() -> int:
    parser = build_parser()
    args = vars(parser.parse_args())
    command = args.pop("command")
    try:
        return dispatch(command, **args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

