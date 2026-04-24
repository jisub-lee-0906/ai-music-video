from __future__ import annotations

import json
from pathlib import Path

from ai_mv.utils.time_utils import ffprobe_duration


RUBRIC_WEIGHTS = {
    "hook_memorability": 20,
    "section_contrast_payoff": 15,
    "genre_fit": 15,
    "vocal_lyric_delivery": 15,
    "mix_cleanliness": 15,
    "mv_cue_strength": 10,
    "replay_value": 10,
}

REASON_CODES = [
    "weak_hook",
    "generic_genre_hit",
    "muddy_vocals",
    "pronunciation_artifacts",
    "flat_section_contrast",
    "weak_chorus_lift",
    "weak_mv_cues",
    "low_replay_value",
]


def build_audio_review_packet_manifest(
    *,
    music_path: str | Path,
    output_dir: str | Path,
    audio_plan: dict | None = None,
    sections: list[dict] | None = None,
    duration_sec: float | None = None,
    duration_fn=ffprobe_duration,
) -> dict[str, object]:
    output_root = Path(output_dir)
    resolved_music_path = str(Path(music_path))
    normalized_sections = _normalize_sections(sections or [])
    resolved_duration = _resolve_duration(music_path, duration_sec, duration_fn)
    segments = _build_segments(normalized_sections, resolved_duration)
    normalized_audio_plan = dict(audio_plan or {}) if isinstance(audio_plan, dict) else {}
    return {
        "music_path": resolved_music_path,
        "duration_sec": resolved_duration,
        "section_count": len(normalized_sections),
        "sections": normalized_sections,
        "audio_plan": normalized_audio_plan,
        "segments": segments,
        "reviewer_summary": f"Audio review packet with {len(segments)} listening segments",
        "rubric_path": str(output_root / "audio-review-rubric.json"),
        "reviewer_notes_path": str(output_root / "audio-review-notes.md"),
    }


def write_audio_review_packet(
    *,
    music_path: str | Path,
    output_dir: str | Path,
    audio_plan: dict | None = None,
    sections: list[dict] | None = None,
    duration_sec: float | None = None,
    duration_fn=ffprobe_duration,
) -> dict[str, Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest = build_audio_review_packet_manifest(
        music_path=music_path,
        output_dir=output_root,
        audio_plan=audio_plan,
        sections=sections,
        duration_sec=duration_sec,
        duration_fn=duration_fn,
    )
    manifest_path = output_root / "audio-review-packet.json"
    rubric_path = Path(manifest["rubric_path"])
    reviewer_notes_path = Path(manifest["reviewer_notes_path"])
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    rubric_path.write_text(json.dumps(_rubric_template(manifest), indent=2) + "\n", encoding="utf-8")
    reviewer_notes_path.write_text(_reviewer_notes_template(manifest), encoding="utf-8")
    return {
        "manifest_path": manifest_path,
        "rubric_path": rubric_path,
        "reviewer_notes_path": reviewer_notes_path,
    }


def _resolve_duration(music_path: str | Path, duration_sec: float | None, duration_fn) -> float:
    if duration_sec is not None:
        return round(float(duration_sec), 3)
    return round(float(duration_fn(str(music_path))), 3)


def _normalize_sections(sections: list[dict]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for index, row in enumerate(sections, start=1):
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", row.get("section_type", ""))).strip()
        if not name:
            continue
        start = float(row.get("start_sec", 0.0) or 0.0)
        end = float(row.get("end_sec", start) or start)
        normalized.append(
            {
                "section_id": str(row.get("section_id", f"SEC_{index:03d}")).strip() or f"SEC_{index:03d}",
                "name": name,
                "start_sec": round(start, 3),
                "end_sec": round(max(end, start), 3),
                "duration_sec": round(max(end - start, 0.0), 3),
            }
        )
    return normalized


def _build_segments(sections: list[dict[str, object]], duration_sec: float) -> list[dict[str, object]]:
    segments: list[dict[str, object]] = []
    seen: set[str] = set()
    _append_segment(
        segments,
        seen,
        segment_id="opener_window",
        label="Opener window",
        start_sec=0.0,
        end_sec=min(duration_sec, 10.0),
        section_name=_section_name_at_time(sections, 0.0),
        review_axes=["hook_memorability", "vocal_lyric_delivery", "mix_cleanliness"],
        focus="Check whether the opening establishes tone, vocal readability, and basic mix clarity.",
    )
    first_chorus = _find_section(sections, ("chorus", "hook", "refrain"))
    if first_chorus:
        _append_segment(
            segments,
            seen,
            segment_id="first_chorus",
            label="First chorus",
            start_sec=float(first_chorus["start_sec"]),
            end_sec=min(float(first_chorus["end_sec"]), float(first_chorus["start_sec"]) + 12.0),
            section_name=str(first_chorus["name"]),
            review_axes=["hook_memorability", "genre_fit", "mv_cue_strength"],
            focus="Check whether the chorus lifts, lands a memorable hook, and exposes strong edit cues.",
        )
    bridge_section = _find_section(sections, ("bridge", "breakdown", "middle8", "middle_8"))
    if bridge_section:
        _append_segment(
            segments,
            seen,
            segment_id="bridge_window",
            label="Bridge window",
            start_sec=float(bridge_section["start_sec"]),
            end_sec=min(float(bridge_section["end_sec"]), float(bridge_section["start_sec"]) + 10.0),
            section_name=str(bridge_section["name"]),
            review_axes=["section_contrast_payoff", "vocal_lyric_delivery", "replay_value"],
            focus="Check whether the arrangement creates contrast and meaningful payoff before the ending.",
        )
    final_chorus = _find_last_distinct_section(sections, ("chorus", "hook", "refrain"), first_chorus)
    if final_chorus:
        _append_segment(
            segments,
            seen,
            segment_id="final_chorus",
            label="Final chorus",
            start_sec=float(final_chorus["start_sec"]),
            end_sec=min(float(final_chorus["end_sec"]), float(final_chorus["start_sec"]) + 12.0),
            section_name=str(final_chorus["name"]),
            review_axes=["section_contrast_payoff", "mv_cue_strength", "replay_value"],
            focus="Check whether the ending chorus pays off emotionally and feels publishable rather than flat repetition.",
        )
    if duration_sec > 0:
        _append_segment(
            segments,
            seen,
            segment_id="outro_tail",
            label="Outro tail",
            start_sec=max(duration_sec - 8.0, 0.0),
            end_sec=duration_sec,
            section_name=_section_name_at_time(sections, max(duration_sec - 0.5, 0.0)),
            review_axes=["mix_cleanliness", "section_contrast_payoff", "replay_value"],
            focus="Check whether the ending resolves cleanly without awkward decay or collapsed energy.",
        )
    return segments


def _append_segment(
    segments: list[dict[str, object]],
    seen: set[str],
    *,
    segment_id: str,
    label: str,
    start_sec: float,
    end_sec: float,
    section_name: str,
    review_axes: list[str],
    focus: str,
) -> None:
    normalized_start = round(max(start_sec, 0.0), 3)
    normalized_end = round(max(end_sec, normalized_start), 3)
    if normalized_end <= normalized_start or segment_id in seen:
        return
    segments.append(
        {
            "segment_id": segment_id,
            "label": label,
            "start_sec": normalized_start,
            "end_sec": normalized_end,
            "duration_sec": round(normalized_end - normalized_start, 3),
            "section_name": section_name,
            "review_axes": list(review_axes),
            "focus": focus,
        }
    )
    seen.add(segment_id)


def _section_name_at_time(sections: list[dict[str, object]], second: float) -> str:
    for row in sections:
        if float(row["start_sec"]) <= second <= float(row["end_sec"]):
            return str(row["name"])
    return str(sections[0]["name"]) if sections else ""


def _find_section(sections: list[dict[str, object]], names: tuple[str, ...]) -> dict[str, object] | None:
    for row in sections:
        if _section_matches(row, names):
            return row
    return None


def _find_last_distinct_section(
    sections: list[dict[str, object]], names: tuple[str, ...], first_match: dict[str, object] | None
) -> dict[str, object] | None:
    matches = [row for row in sections if _section_matches(row, names)]
    if not matches:
        return None
    if first_match is None:
        return matches[-1]
    if len(matches) == 1:
        return None
    if float(matches[-1]["start_sec"]) == float(first_match["start_sec"]):
        return None
    return matches[-1]


def _section_matches(row: dict[str, object], names: tuple[str, ...]) -> bool:
    lowered = str(row["name"]).strip().lower().replace("-", "_").replace(" ", "_")
    if lowered in {"pre_chorus", "prechorus"} and "chorus" in names:
        return False
    tokens = tuple(token for token in lowered.split("_") if token)
    if lowered in names:
        return True
    return any(name in tokens for name in names)


def _rubric_template(manifest: dict[str, object]) -> dict[str, object]:
    return {
        "music_path": manifest.get("music_path", ""),
        "reviewer_summary": manifest.get("reviewer_summary", ""),
        "scoring": {
            "weights": dict(RUBRIC_WEIGHTS),
            "band_guide": {
                "85_plus": "very strong; lane-representative candidate",
                "75_to_84": "usable; reroll optional",
                "65_to_74": "technically successful but needs another quality loop",
                "below_65": "regenerate or substantially redirect",
            },
        },
        "reason_codes": list(REASON_CODES),
        "segments": [
            {
                "segment_id": row["segment_id"],
                "label": row["label"],
                "start_sec": row["start_sec"],
                "end_sec": row["end_sec"],
                "review_axes": row["review_axes"],
                "scores": {axis: None for axis in row["review_axes"]},
                "reason_codes": [],
                "notes": "",
            }
            for row in manifest.get("segments", [])
            if isinstance(row, dict)
        ],
        "overall": {
            "weighted_score": None,
            "verdict": "",
            "strengths": [],
            "weaknesses": [],
            "recommended_next_action": "",
        },
    }


def _reviewer_notes_template(manifest: dict[str, object]) -> str:
    lines = [
        "# Audio Review Notes",
        "",
        f"- music_path: {manifest.get('music_path', '')}",
        f"- duration_sec: {manifest.get('duration_sec', 0.0)}",
        f"- section_count: {manifest.get('section_count', 0)}",
        "",
        "## Listening queue",
    ]
    for row in manifest.get("segments", []):
        if not isinstance(row, dict):
            continue
        lines.extend(
            [
                f"### {row.get('segment_id', '')}",
                f"- range: {row.get('start_sec', 0.0)}s -> {row.get('end_sec', 0.0)}s",
                f"- section: {row.get('section_name', '')}",
                f"- review_axes: {', '.join(row.get('review_axes', [])) if isinstance(row.get('review_axes'), list) else ''}",
                f"- focus: {row.get('focus', '')}",
                "- notes: ",
                "",
            ]
        )
    lines.extend(
        [
            "## Overall verdict",
            "- weighted_score: ",
            "- verdict: ",
            "- recommended_next_action: ",
        ]
    )
    return "\n".join(lines) + "\n"
