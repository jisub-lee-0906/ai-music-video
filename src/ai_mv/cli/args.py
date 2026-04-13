from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-mv")
    sub = parser.add_subparsers(dest="command", required=True)

    start_cmd = sub.add_parser("start")
    start_cmd.add_argument("--run-id", default=None)
    start_cmd.add_argument("--concept-text", dest="concept_text", default=None)
    start_cmd.add_argument("--brief", dest="legacy_brief", default=None)

    sub.add_parser("doctor")

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--run-id", default=None)
    preflight.add_argument("--concept-text", dest="concept_text", default=None)
    preflight.add_argument("--brief", dest="legacy_brief", default=None)

    status = sub.add_parser("status")
    status.add_argument("--run-id", required=True)
    return parser
