from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-mv")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start")
    start.add_argument("--run-id", default=None)
    start.add_argument("--profile", default=None)

    doctor = sub.add_parser("doctor")

    status = sub.add_parser("status")
    status.add_argument("--run-id", required=True)
    return parser
