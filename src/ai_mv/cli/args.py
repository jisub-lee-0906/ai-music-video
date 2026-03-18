from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-mv")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start")
    start.add_argument("--run-id", default=None)
    start.add_argument("--profile", default=None)

    sub.add_parser("doctor")

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--run-id", default=None)
    preflight.add_argument("--profile", default=None)

    prompt_extract = sub.add_parser("prompt-extract")
    prompt_extract.add_argument("--run-id", default=None)
    prompt_extract.add_argument("--profile", default=None)

    status = sub.add_parser("status")
    status.add_argument("--run-id", required=True)
    return parser
