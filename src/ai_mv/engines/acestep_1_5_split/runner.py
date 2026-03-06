from __future__ import annotations

from pathlib import Path

from ai_mv.engines.acestep_1_5_split.mapper import audio_required_inputs, map_audio_workflow
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.utils.time_utils import ffprobe_duration

SECTION_FLOW: dict[str, tuple[str, ...]] = {
    "intro": ("intro", "verse_1", "verse", "pre_chorus", "chorus", "bridge", "outro"),
    "verse_1": ("verse_1", "pre_chorus", "chorus", "post_chorus", "verse_2", "bridge", "outro"),
    "verse_2": ("verse_2", "pre_chorus", "chorus", "post_chorus", "bridge", "outro"),
    "verse": ("verse", "pre_chorus", "chorus", "post_chorus", "bridge", "outro"),
    "pre_chorus": ("pre_chorus", "chorus", "post_chorus", "outro"),
    "chorus": ("chorus", "post_chorus", "verse_2", "verse", "bridge", "outro"),
    "post_chorus": ("post_chorus", "chorus", "pre_chorus", "verse_2", "verse", "bridge", "outro"),
    "bridge": ("bridge", "chorus", "post_chorus", "outro"),
    "outro": (),
}


def run_audio_split(config: dict, plan: dict) -> dict:
    wf = map_audio_workflow(config, plan)
    result = run_workflow(config, "audio_ace_step_1_5_tta.api.json", wf, audio_required_inputs())
    music_file = _resolve_audio_file(config, _pick_audio_file(result["files"]))
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
        return _fallback_sections(duration)
    weights = [_block_weight(x) for x in rows]
    mass = sum(weights)
    if mass <= 0:
        return _fallback_sections(duration)
    out: list[dict] = []
    cursor = 0.0
    for i, row in enumerate(rows):
        name = str(row.get("section", "section")).strip().lower()
        seg = duration * (weights[i] / mass)
        end = duration if i == len(rows) - 1 else min(duration, cursor + seg)
        out.append({"name": name, "start_sec": round(cursor, 3), "end_sec": round(end, 3)})
        cursor = end
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


def _fallback_sections(duration: float) -> list[dict]:
    return [
        {"name": "intro", "start_sec": 0.0, "end_sec": duration * 0.15},
        {"name": "verse", "start_sec": duration * 0.15, "end_sec": duration * 0.40},
        {"name": "chorus", "start_sec": duration * 0.40, "end_sec": duration * 0.60},
        {"name": "bridge", "start_sec": duration * 0.60, "end_sec": duration * 0.78},
        {"name": "outro", "start_sec": duration * 0.78, "end_sec": duration},
    ]


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
    if name in SECTION_FLOW:
        return name
    raise RuntimeError(f"lyrics_blocks section invalid: {name}")


def _validate_transitions(names: list[str]) -> None:
    for prev, cur in zip(names, names[1:]):
        allowed = SECTION_FLOW.get(prev, ())
        if cur not in allowed:
            raise RuntimeError(f"lyrics_blocks transition invalid: {prev} -> {cur}")


def _pick_audio_file(files: list[str]) -> str:
    for name in files:
        low = str(name).lower()
        if low.endswith((".wav", ".mp3", ".flac", ".m4a")):
            return name
    raise RuntimeError("audio output file not found")


def _resolve_audio_file(config: dict, name: str) -> str:
    p = Path(str(name))
    if p.exists():
        return str(p.resolve())
    out = Path(str(config["integrations"]["comfyui_output_dir"]).strip())
    cand = out / p
    if cand.exists():
        return str(cand.resolve())
    return str(p)
