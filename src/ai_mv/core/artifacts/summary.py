from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.utils.json_utils import write_json


def write_summary(state: dict, payload: dict) -> None:
    scope = str(state.get("scope", "run"))
    anchors = payload.get("anchors", [])
    clips = payload.get("clips", [])
    routes = payload.get("clip_routes", [])
    lyric_metrics = _lyric_metrics(payload)
    summary = {
        "run_id": state["run_id"],
        "completed_stages": list(state.get("completed_stages", [])),
        "current_stage": str(state.get("current_stage", "")),
        "failure_reason": str(state.get("failure_reason", "")),
        "keys": sorted(payload.keys()),
        "shots": len(anchors) if isinstance(anchors, list) else 0,
        "clips": len(clips) if isinstance(clips, list) else 0,
        "tti_only_shots": _tti_only_count(routes),
        "ref_assisted_shots": _ref_assisted_count(routes),
        "lyric_beat_count": lyric_metrics["lyric_beat_count"],
        "shot_to_lyric_coverage": lyric_metrics["shot_to_lyric_coverage"],
        "repeated_hook_variation": lyric_metrics["repeated_hook_variation"],
        "unmapped_lyric_lines": lyric_metrics["unmapped_lyric_lines"],
    }
    write_json(run_file(state["run_id"], "summary.json", scope), summary)
    write_json(latest_file("summary.json", scope), summary)
    if str(state.get("status", "")) == "done":
        write_json(latest_success_file("summary.json", scope), summary)


def _tti_only_count(routes: object) -> int:
    if not isinstance(routes, list):
        return 0
    return sum(1 for row in routes if isinstance(row, dict) and not bool(row.get("use_ref", False)))


def _ref_assisted_count(routes: object) -> int:
    if not isinstance(routes, list):
        return 0
    return sum(1 for row in routes if isinstance(row, dict) and bool(row.get("use_ref", False)))


def _lyric_metrics(payload: dict) -> dict:
    timeline = payload.get("lyrics_timeline", {})
    shot_timeline = payload.get("shot_timeline", {})
    beat_ids = {
        str(beat.get("beat_id", "")).strip()
        for section in timeline.get("sections", [])
        if isinstance(section, dict)
        for beat in section.get("lyric_beats", [])
        if isinstance(beat, dict) and str(beat.get("beat_id", "")).strip()
    }
    shot_beat_ids = {
        str(row.get("lyric_beat_id", "")).strip()
        for row in shot_timeline.get("shots", [])
        if isinstance(row, dict) and str(row.get("lyric_beat_id", "")).strip()
    }
    total_lines = sum(
        len([line for line in section.get("lines", []) if isinstance(line, dict)])
        for section in timeline.get("sections", [])
        if isinstance(section, dict)
    )
    mapped_lines = sum(
        len([ref for ref in beat.get("line_refs", []) if int(ref) > 0])
        for section in timeline.get("sections", [])
        if isinstance(section, dict)
        for beat in section.get("lyric_beats", [])
        if isinstance(beat, dict) and str(beat.get("beat_id", "")).strip() in shot_beat_ids
    )
    repeat_scores = []
    groups: dict[tuple[int, ...], list[dict]] = {}
    for section in timeline.get("sections", []):
        if not isinstance(section, dict):
            continue
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            refs = tuple(int(x) for x in beat.get("line_refs", []) if int(x) > 0)
            if refs:
                groups.setdefault(refs, []).append(beat)
    for beats in groups.values():
        if len(beats) <= 1:
            continue
        signatures = {
            (str(beat.get("visible_action", "")).strip().lower(), str(beat.get("payoff_role", "")).strip().lower())
            for beat in beats
        }
        repeat_scores.append(len(signatures) / float(len(beats)))
    return {
        "lyric_beat_count": len(beat_ids),
        "shot_to_lyric_coverage": round((len(beat_ids & shot_beat_ids) / len(beat_ids)) if beat_ids else 1.0, 3),
        "repeated_hook_variation": round((sum(repeat_scores) / len(repeat_scores)) if repeat_scores else 1.0, 3),
        "unmapped_lyric_lines": max(0, total_lines - mapped_lines),
    }
