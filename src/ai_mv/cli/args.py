from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-mv")
    sub = parser.add_subparsers(dest="command", required=True)

    start_cmd = sub.add_parser("start")
    start_cmd.add_argument("--run-id", default=None)
    start_cmd.add_argument("--brief", default=None)

    tti_cmd = sub.add_parser("tti")
    tti_cmd.add_argument("--run-id", default=None)
    tti_cmd.add_argument("--brief", default=None)

    ref_probe_cmd = sub.add_parser("ref-probe")
    ref_probe_cmd.add_argument("--run-id", default=None)
    ref_probe_cmd.add_argument("--brief", default=None)
    ref_probe_cmd.add_argument("--ref", required=True)
    ref_probe_cmd.add_argument("--prompt", required=True)
    ref_probe_cmd.add_argument("--shot-id", default="ref_probe")
    ref_probe_cmd.add_argument("--frame-name", default="end")

    ref_probe_batch_cmd = sub.add_parser("ref-probe-batch")
    ref_probe_batch_cmd.add_argument("--run-id", default=None)
    ref_probe_batch_cmd.add_argument("--brief", default=None)
    ref_probe_batch_cmd.add_argument("--ref", required=True)
    ref_probe_batch_cmd.add_argument("--prompts-file", required=True)
    ref_probe_batch_cmd.add_argument("--shot-id-prefix", default="ref_batch")
    ref_probe_batch_cmd.add_argument("--frame-name", default="end")

    sub.add_parser("doctor")

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--run-id", default=None)
    preflight.add_argument("--brief", default=None)

    status = sub.add_parser("status")
    status.add_argument("--run-id", required=True)
    return parser
