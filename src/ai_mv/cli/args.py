from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-mv")
    sub = parser.add_subparsers(dest="command", required=True)

    start_cmd = sub.add_parser("start")
    start_cmd.add_argument("--run-id", default=None)
    start_cmd.add_argument("--concept-text", dest="concept_text", default=None)

    sub.add_parser("doctor")

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--run-id", default=None)
    preflight.add_argument("--concept-text", dest="concept_text", default=None)

    status = sub.add_parser("status")
    status.add_argument("--run-id", required=True)

    validate_latest = sub.add_parser("validate-latest")
    validate_latest.add_argument("--output-dir", dest="output_dir", required=True)
    validate_latest.add_argument("--sample-count", dest="sample_count", type=int, default=8)
    validate_latest.add_argument("--shot-id", dest="shot_ids", action="append", default=[])
    return parser
