from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-mv")
    sub = parser.add_subparsers(dest="command", required=True)

    start_v2 = sub.add_parser("start-v2")
    start_v2.add_argument("--run-id", default=None)
    start_v2.add_argument("--brief", default=None)

    tti_v2 = sub.add_parser("tti-v2")
    tti_v2.add_argument("--run-id", default=None)
    tti_v2.add_argument("--brief", default=None)

    sub.add_parser("doctor")

    preflight_v2 = sub.add_parser("preflight-v2")
    preflight_v2.add_argument("--run-id", default=None)
    preflight_v2.add_argument("--brief", default=None)

    status = sub.add_parser("status")
    status.add_argument("--run-id", required=True)
    return parser
