from __future__ import annotations

from ai_mv.core.workflow_names import AUDIO_WORKFLOW
from ai_mv.engines.acestep_1_5_split.mapper import audio_required_inputs, map_audio_workflow
from ai_mv.infra.comfy_outputs import pick_audio_file
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.utils.path_utils import resolve_generated_file
from ai_mv.utils.time_utils import ffprobe_duration

ALLOWED_SECTIONS = {"intro", "verse", "verse_1", "verse_2", "pre_chorus", "chorus", "post_chorus", "bridge", "outro"}


def run_audio_split(config: dict, plan: dict) -> dict:
    wf = map_audio_workflow(config, plan)
    result = run_workflow(config, AUDIO_WORKFLOW, wf, audio_required_inputs())
    music_file = _resolve_audio_file(config, pick_audio_file(result["files"]))
    duration = ffprobe_duration(music_file)
    if duration <= 0:
        raise RuntimeError(f"invalid audio duration: {music_file}")
    return {
        "duration_sec": duration,
        "bpm_estimate": int(plan["bpm"]),
        "sections": _sections(duration, plan.get("lyrics_blocks", [])),
        "music_file": music_file,
    }


def _sections(duration: float, blocks: list[dict]) -> list[dict]:
    rows = [x for x in blocks if isinstance(x, dict)] if isinstance(blocks, list) else []
    rows = _limit_section_rows(rows)
    rows = _validate_and_fix_order(rows)
    if not rows:
        raise RuntimeError("lyrics_blocks empty after validation")
    weights = [_block_weight(x) for x in rows]
    mass = sum(weights)
    if mass <= 0:
        raise RuntimeError("invalid lyrics block weights")
    out: list[dict] = []
    cursor = 0.0
    for i, row in enumerate(rows):
        name = str(row.get("section", "section")).strip().lower()
        label = str(row.get("label", "")).strip() or name
        seg = duration * (weights[i] / mass)
        end = duration if i == len(rows) - 1 else min(duration, cursor + seg)
        out.append({"name": name, "label": label, "start_sec": round(cursor, 3), "end_sec": round(end, 3)})
        cursor = end
    if not out:
        raise RuntimeError("sections build produced no rows")
    return out


def _block_weight(row: dict) -> float:
    section = str(row.get("section", "section")).lower()
    lines = row.get("lines", [])
    line_cnt = len([x for x in lines if str(x).strip()]) if isinstance(lines, list) else 0
    base = 1.0 + (0.35 * max(1, line_cnt))
    if "chorus" in section:
        return base * 1.25
    if "bridge" in section:
        return base * 1.1
    if "outro" in section:
        return base * 0.9
    if "intro" in section:
        return base * 0.8
    return base


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
