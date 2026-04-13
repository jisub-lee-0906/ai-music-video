from __future__ import annotations

from ai_mv.core.workflow_names import AUDIO_WORKFLOW
from ai_mv.engines.acestep_1_5_aio.mapper import audio_required_inputs, map_audio_workflow
from ai_mv.engines.acestep_1_5_aio.policy import build_song_timing, compute_section_windows
from ai_mv.infra.comfy_outputs import pick_audio_file
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.utils.path_utils import resolve_generated_file
from ai_mv.utils.audio_timing import analyze_audio_timing
from ai_mv.utils.time_utils import ffprobe_duration

ALLOWED_SECTIONS = {"intro", "verse", "verse_1", "verse_2", "pre_chorus", "chorus", "post_chorus", "bridge", "outro"}


def run_audio_split(config: dict, plan: dict) -> dict:
    wf = map_audio_workflow(config, plan)
    result = run_workflow(config, AUDIO_WORKFLOW, wf, audio_required_inputs())
    music_file = _resolve_audio_file(config, pick_audio_file(result["files"]))
    duration = ffprobe_duration(music_file)
    if duration <= 0:
        raise RuntimeError(f"invalid audio duration: {music_file}")
    timing = analyze_audio_timing(
        music_file,
        bpm_hint=int(plan.get("bpm", 0) or 0),
        beats_per_bar=int(plan.get("beats_per_bar", 4) or 4),
    )
    timing_bundle = build_song_timing(
        duration,
        plan.get("lyrics_blocks", []),
        int(plan.get("bpm", 0)),
        int(plan.get("beats_per_bar", 4)),
        plan.get("section_bars", {}),
        detected_beat_times=timing.get("beat_times_sec", []),
        detected_bpm=int(timing.get("detected_bpm", 0) or 0),
    )
    return {
        "duration_sec": duration,
        "bpm_estimate": int(timing_bundle["timing"]["detected_bpm"]),
        "sections": timing_bundle["sections"],
        "timing": timing_bundle["timing"],
        "music_file": music_file,
    }


def _sections(
    duration: float,
    blocks: list[dict],
    bpm: int = 0,
    beats_per_bar: int = 4,
    section_bars: dict | None = None,
) -> list[dict]:
    rows = [x for x in blocks if isinstance(x, dict)] if isinstance(blocks, list) else []
    rows = _limit_section_rows(rows)
    rows = _validate_and_fix_order(rows)
    if not rows:
        raise RuntimeError("lyrics_blocks empty after validation")
    timing_bundle = build_song_timing(
        float(duration),
        rows,
        int(bpm),
        int(beats_per_bar),
        section_bars or {},
    )
    return timing_bundle["sections"]


def _limit_section_rows(rows: list[dict]) -> list[dict]:
    return rows[:16] if len(rows) > 16 else rows


def _validate_and_fix_order(rows: list[dict]) -> list[dict]:
    if not rows:
        return rows
    out = [dict(x) for x in rows]
    names = [_canonical_section(str(x.get("section", "")).strip().lower()) for x in out]
    for i, name in enumerate(names):
        out[i]["section"] = name
    if "verse_1" in names and "verse_2" in names:
        i1, i2 = names.index("verse_1"), names.index("verse_2")
        if i2 < i1:
            out[i1], out[i2] = out[i2], out[i1]
            names[i1], names[i2] = names[i2], names[i1]
    if "intro" in names and names[0] != "intro":
        raise RuntimeError("lyrics_blocks order invalid: intro must be first")
    if "outro" in names and names[-1] != "outro":
        raise RuntimeError("lyrics_blocks order invalid: outro must be last")
    _validate_transitions(names)
    return out


def _canonical_section(name: str) -> str:
    if name in ALLOWED_SECTIONS:
        return name
    raise RuntimeError(f"lyrics_blocks section invalid: {name}")


def _validate_transitions(names: list[str]) -> None:
    seen_verse_1 = False
    for idx, cur in enumerate(names):
        if cur == "intro" and idx != 0:
            raise RuntimeError("lyrics_blocks transition invalid: intro must be first")
        if cur == "outro" and idx != len(names) - 1:
            raise RuntimeError("lyrics_blocks transition invalid: outro must be last")
        if cur == "verse_1":
            seen_verse_1 = True
        if cur == "verse_2" and not seen_verse_1:
            raise RuntimeError("lyrics_blocks transition invalid: verse_2 before verse_1")


def _resolve_audio_file(config: dict, name: str) -> str:
    path = resolve_generated_file(config, name, {".wav", ".mp3", ".flac", ".m4a"}, "audio")
    return str(path)
