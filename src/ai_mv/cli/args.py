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

    extract_frames = sub.add_parser("extract-frames")
    extract_frames.add_argument("--video", required=True)
    extract_frames.add_argument("--output-dir", dest="output_dir", required=True)
    extract_frames.add_argument("--kind", choices=("clip", "final"), default="clip")
    extract_frames.add_argument("--sample-count", dest="sample_count", type=int, default=6)

    quality_findings = sub.add_parser("quality-findings-template")
    quality_findings.add_argument("--shot-id", dest="shot_ids", action="append", required=True)
    quality_findings.add_argument("--output", required=True)

    review_packet = sub.add_parser("review-packet")
    review_packet.add_argument("--video", required=True)
    review_packet.add_argument("--output-dir", dest="output_dir", required=True)
    review_packet.add_argument("--kind", choices=("clip", "final"), default="clip")
    review_packet.add_argument("--sample-count", dest="sample_count", type=int, default=6)
    review_packet.add_argument("--shot-id", dest="shot_ids", action="append", default=[])

    audio_review_packet = sub.add_parser("audio-review-packet")
    audio_review_packet.add_argument("--music-file", dest="music_file", required=True)
    audio_review_packet.add_argument("--output-dir", dest="output_dir", required=True)
    audio_review_packet.add_argument("--sections-json", dest="sections_json", default="[]")
    audio_review_packet.add_argument("--audio-plan-json", dest="audio_plan_json", default="{}")

    audio_reroll_preflight = sub.add_parser("audio-reroll-preflight")
    audio_reroll_preflight.add_argument("--rubric-path", dest="rubric_path", required=True)
    audio_reroll_preflight.add_argument("--run-id", dest="run_id", default=None)
    audio_reroll_preflight.add_argument("--concept-text", dest="concept_text", default=None)
    audio_reroll_preflight.add_argument("--scope", choices=("run", "preflight"), default="run")

    audio_reroll_start = sub.add_parser("audio-reroll-start")
    audio_reroll_start.add_argument("--rubric-path", dest="rubric_path", required=True)
    audio_reroll_start.add_argument("--run-id", dest="run_id", default=None)
    audio_reroll_start.add_argument("--concept-text", dest="concept_text", default=None)
    audio_reroll_start.add_argument("--scope", choices=("run", "preflight"), default="run")

    audio_review_score = sub.add_parser("audio-review-score")
    audio_review_score.add_argument("--rubric-path", dest="rubric_path", required=True)
    audio_review_score.add_argument("--segment-id", dest="segment_id", required=True)
    audio_review_score.add_argument("--scores-json", dest="scores_json", default="{}")
    audio_review_score.add_argument("--reason-codes-json", dest="reason_codes_json", default="[]")
    audio_review_score.add_argument("--notes", dest="notes", default="")
    audio_review_score.add_argument("--verdict", dest="verdict", default="")
    audio_review_score.add_argument("--next-action", dest="next_action", default="")

    audio_review_batch_score = sub.add_parser("audio-review-batch-score")
    audio_review_batch_score.add_argument("--rubric-path", dest="rubric_path", required=True)
    audio_review_batch_score.add_argument("--updates-json", dest="updates_json", required=True)
    audio_review_batch_score.add_argument("--verdict", dest="verdict", default="")
    audio_review_batch_score.add_argument("--next-action", dest="next_action", default="")

    validate_latest = sub.add_parser("validate-latest")
    validate_latest.add_argument("--output-dir", dest="output_dir", required=True)
    validate_latest.add_argument("--sample-count", dest="sample_count", type=int, default=8)
    validate_latest.add_argument("--shot-id", dest="shot_ids", action="append", default=[])
    return parser
