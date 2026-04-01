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

    ref_v2_probe = sub.add_parser("ref-v2-probe")
    ref_v2_probe.add_argument("--run-id", default=None)
    ref_v2_probe.add_argument("--brief", default=None)
    ref_v2_probe.add_argument("--ref", required=True)
    ref_v2_probe.add_argument("--prompt", required=True)
    ref_v2_probe.add_argument("--shot-id", default="ref_probe")
    ref_v2_probe.add_argument("--frame-name", default="end")

    ref_v2_probe_batch = sub.add_parser("ref-v2-probe-batch")
    ref_v2_probe_batch.add_argument("--run-id", default=None)
    ref_v2_probe_batch.add_argument("--brief", default=None)
    ref_v2_probe_batch.add_argument("--ref", required=True)
    ref_v2_probe_batch.add_argument("--prompts-file", required=True)
    ref_v2_probe_batch.add_argument("--shot-id-prefix", default="ref_batch")
    ref_v2_probe_batch.add_argument("--frame-name", default="end")

    sub.add_parser("doctor")

    preflight_v2 = sub.add_parser("preflight-v2")
    preflight_v2.add_argument("--run-id", default=None)
    preflight_v2.add_argument("--brief", default=None)

    status = sub.add_parser("status")
    status.add_argument("--run-id", required=True)
    return parser
