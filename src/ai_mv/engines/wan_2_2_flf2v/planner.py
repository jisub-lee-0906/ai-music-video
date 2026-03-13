from __future__ import annotations

from ai_mv.engines.common.clip_timing import read_max_clip_sec
from ai_mv.core.contracts.prompt_normalize import normalize_wan_clips
from ai_mv.core.contracts.prompt_schema import wan_schema
from ai_mv.core.prompt_digests import lyrics_digest, negative_digest, style_digest, visual_digest
from ai_mv.infra.codex_cli_client import generate_structured
from ai_mv.engines.visual_bridge.brief_views import compact_section_atoms, compact_world_atoms
from ai_mv.utils.bool_utils import parse_bool
from ai_mv.utils.text_utils import parse_target


def build_wan_plan(config: dict, payload: dict) -> dict:
    fps = parse_target(config["video"]["target"])[2]
    clips = [_item_to_clip(item, fps) for item in payload["uso_images"]]
    clips = _chain_clip_starts(clips)
    if not clips:
        raise RuntimeError("WAN clips empty")
    _enforce_clip_cap(config, clips, fps)
    spec = _plan_with_llm(config, payload, clips)
    prompts = normalize_wan_clips(spec["clips"], clips)
    clips = [_apply_prompt(x, prompts[x["shot_id"]]) for x in clips]
    return {"clips": clips}


def _plan_with_llm(config: dict, payload: dict, clips: list[dict]) -> dict:
    batch_size = _wan_planner_batch_size(config, len(clips))
    strict = _strict_id_match(config)
    if len(clips) <= batch_size:
        return {"clips": _plan_chunk_rows(config, payload, clips, "", strict)}
    out: list[dict] = []
    carry = ""
    for i in range(0, len(clips), batch_size):
        chunk = clips[i : i + batch_size]
        rows = _plan_chunk_rows(config, payload, chunk, carry, strict)
        out.extend(rows)
        carry = _carry_hint(rows)
    return {"clips": out}


def _plan_chunk_rows(config: dict, payload: dict, chunk: list[dict], carry: str, strict: bool) -> list[dict]:
    prompt = _planner_prompt(config, payload, chunk, carry)
    raw = generate_structured(config, prompt, wan_schema())
    return _coerce_clip_ids(raw.get("clips", []), chunk, strict)


def _planner_prompt(config: dict, payload: dict, clips: list[dict], carry: str) -> str:
    guidance = style_digest(payload.get("audio_map", {}), 1) or _style_guidance(config, payload)
    visual = visual_digest(payload.get("audio_map", {}), 1)
    negative = negative_digest(payload.get("audio_map", {}), 1)
    lyrics = lyrics_digest(payload.get("audio_map", {}).get("lyrics", ""), 3)
    brief = _brief_summary(payload["visual_brief"])
    clip_ids = _clip_ids(clips)
    summary = _clip_summary(clips)
    carry_clause = f"Continuity carry={carry}. " if carry else ""
    return (
        "You are a senior first-last-frame video prompt director for WAN FLF2V. "
        "Return strict JSON only: {\"clips\":[...]}. No prose outside JSON. "
        "Each clip item must include shot_id,subject_motion,camera_relation,environment_detail,negative_prompt,energy. "
        "Use shot_id values exactly from ClipIds list, without creating new ids. "
        "shot_id must be exactly one token from ClipIds with no suffix, prefix, or punctuation changes. "
        "Clip suffixes such as _C01, _C02, _C03 are part of the required shot_id and must be preserved exactly. "
        "Clip item count must match the number of ClipIds exactly. "
        "Do not write the final positive_prompt prose. Return short motion-ready fragments only. "
        "subject_motion must combine the visible starting state and the main body motion in one short natural clause. "
        "Good subject_motion examples: She pauses by the rain-marked glass and turns into the crossing; She moves through the lane and lifts her eyes toward the station light; She holds at the curb and then steps forward with a calmer chest line. "
        "Bad subject_motion examples: emotional chorus arrival; cleaner visual payoff; stronger confidence; cinematic motion energy. "
        "camera_relation must be one short framing or camera phrase describing how the shot holds, follows, glides, tracks, drifts, or frames the subject motion. "
        "Good camera_relation examples: glides backward in front of her; holds a close side profile; follows just behind her shoulder; keeps a frontal tracking frame. "
        "Bad camera_relation examples: brighter reflections on the glass; more dramatic atmosphere; stronger visual confidence. "
        "environment_detail is optional and must stay short, concrete, and visual. "
        "Good environment_detail examples: wet stripes brighten underfoot; sodium reflections tremble across the glass; storefront glow slides along her coat hem. "
        "Bad environment_detail examples: the scene feels more emotional; the world becomes more cinematic; the atmosphere grows stronger. "
        "Use the visual brief and section rules to preserve hero identity, palette, lighting, and atmosphere during motion. "
        "Honor section story_beat and location_anchor from the visual brief so consecutive clips feel like progression inside a small recurring world rather than location swapping. "
        "Honor space_relation from the shot blueprint so left-right geometry, glass position, storefront side, and reflection side remain stable across the clip unless the action explicitly crosses the frame. "
        "Prefer one clear motion arc, stable readable subject framing, and deliberate pacing. "
        "For consecutive clips from the same shot series, treat the previous clip end as the immediate starting state of the next clip, not a visual reset. "
        "Think like a completed music video sequence: vary frontal, three-quarter, profile, reflected, and silhouette-friendly motion views across the song instead of keeping every clip face-on. "
        "Build motion like coverage for a finished edit, not a loop of glamour poses: some clips should sell travel, passing space, or the lead subject's relation to the environment more than direct face presentation. "
        "Use section labels to shape escalation: Chorus 2 should feel like a stronger return than Chorus, and Final Chorus should feel like the motion payoff while staying inside the same visual grammar. "
        "For Chorus 2 and Final Chorus, express the lift through clearer posture, cleaner camera relation, stronger reflection response, or a more resolved facial turn rather than generic statements about bigger emotion. "
        "Final Chorus should read like the lead subject and the world have finally locked into the same beat, with one readable motion payoff rather than extra spectacle. "
        "Avoid frantic camera swings, hyperactive subject motion, over-cranked action, or too many simultaneous movements. "
        "Keep the lead subject readable in every sentence: face, posture, silhouette, and clear camera relation should stay understandable. "
        "Verse and transition clips should often move through profile travel, side-on glide, shoulder-led turns, reflective passes, or silhouette walk-throughs instead of defaulting to direct front-facing motion. "
        "Bridge clips should usually introduce distance or suspended breath: slowed walk-through, reflective separation, lateral drift with negative space, profile pause, or a partially obscured hold are stronger than another frontal beauty move. "
        "Final Chorus can return to a more direct hero relation, but it should feel earned as the payoff angle rather than the default angle for the whole song. "
        "Outro clips should resolve by leaving a lingering residue image or motion, not by restating the same hero beat again. "
        "Preserve the same master palette and lighting baseline; section palette_hint and lighting_hint are accents, not resets. "
        "Do not describe multiple competing action arcs in one clip. "
        "Avoid generic wording like cinematic motion, dynamic energy, dramatic atmosphere, or stylish movement unless tied to a concrete body, camera, or environment action. "
        "negative_prompt must be a comma-separated suppression list for artifacts and defects. "
        "Always include: overexposed, static frame, unclear details, subtitle, watermark, logo, low quality, jpeg artifacts, ugly, defective, extra fingers, poorly drawn hands, poorly drawn face, deformed anatomy, disfigured limbs, fused fingers, cluttered background. "
        "Set energy as low, normal, or high based on motion intensity and pacing. "
        f"{carry_clause}Style lane={guidance}; Visual direction={visual}; "
        f"Avoid={negative}; "
        f"Visual brief={brief}; Lyrics context={lyrics}; "
        f"Exact ClipIds={clip_ids}; ClipSummary={summary}."
    )


def _style_guidance(config: dict, payload: dict) -> str:
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    guided = str(audio_map.get("style_guidance", "")).strip() if isinstance(audio_map, dict) else ""
    if guided:
        return guided
    style = config.get("style", {}) if isinstance(config, dict) else {}
    return str(style.get("guidance", "")).strip() if isinstance(style, dict) else ""

def _brief_summary(brief: dict) -> str:
    world = compact_world_atoms(brief)
    return (
        f"hero={world['hero_identity']}; world={world['world_rules']}; "
        f"sections={_section_briefs(brief)}"
    )


def _section_briefs(brief: dict) -> str:
    rows = []
    names = [str(row.get("section_name", "")).strip() for row in brief.get("section_briefs", [])]
    for name in names:
        row = compact_section_atoms(brief, name)
        rows.append(
            f"{row['section_name']}|{row['story_beat']}|{row['location_anchor']}"
        )
    return ", ".join(rows)


def _coerce_clip_ids(rows: list[dict], clips: list[dict], strict: bool) -> list[dict]:
    pool = [x for x in rows if isinstance(x, dict)]
    keyed = {str(x.get("shot_id", "")): x for x in pool if str(x.get("shot_id", "")).strip()}
    out: list[dict] = []
    idx = 0
    for clip in clips:
        sid = str(clip["shot_id"])
        row = keyed.get(sid)
        if row is None:
            if strict:
                raise RuntimeError(f"WAN planner shot_id mismatch: missing {sid}")
            row = _next_row(pool, idx)
            idx += 1
        out.append(_with_shot_id(row, sid))
    return out


def _next_row(pool: list[dict], idx: int) -> dict:
    if idx >= len(pool):
        raise RuntimeError("WAN planner returned fewer clips than required")
    return pool[idx]


def _with_shot_id(row: dict, shot_id: str) -> dict:
    out = dict(row)
    out["shot_id"] = shot_id
    return out


def _clip_summary(clips: list[dict]) -> str:
    return ", ".join(_clip_summary_row(c) for c in clips)


def _clip_summary_row(clip: dict) -> str:
    sid = str(clip["shot_id"])
    section = str(clip.get("section_name", "section"))
    label = str(clip.get("section_label", section))
    camera = str(clip.get("camera_language", "")).strip() or "clean framing"
    relation = str(clip.get("space_relation", "")).strip() or "space stays stable"
    motion = str(clip.get("motion_hint", "")).strip() or "steady motion"
    return f"{sid}({section}|{label}|{camera}|{motion}|{relation})"


def _clip_ids(clips: list[dict]) -> str:
    ids = [str(clip["shot_id"]) for clip in clips]
    if not ids:
        raise RuntimeError("WAN clips missing for planner prompt")
    return ", ".join(ids)


def _item_to_clip(item: dict, fps: int) -> dict:
    frames = max(_frame_floor(fps), int(round(float(item["duration_sec"]) * fps)))
    return {
        "shot_id": str(item["shot_id"]),
        "start": item["start"],
        "end": item["end"],
        "fps": fps,
        "frames": int(frames),
        "section_name": str(item.get("section_name", "section")),
        "section_label": str(item.get("section_label", item.get("section_name", "section"))),
        "shot_type": str(item.get("shot_type", "CHAR_MASTER")),
        "is_chorus": bool(item.get("is_chorus", False)),
        "camera_language": str(item.get("camera_language", "")),
        "pose_delta": str(item.get("pose_delta", "")),
        "emotion": str(item.get("emotion", "")),
        "scene_detail": str(item.get("scene_detail", "")),
        "motion_hint": str(item.get("motion_hint", "")),
        "space_relation": str(item.get("space_relation", "")),
    }


def _chain_clip_starts(clips: list[dict]) -> list[dict]:
    out: list[dict] = []
    prev_end: dict[str, str] = {}
    for clip in clips:
        item = dict(clip)
        key = _clip_series_key(str(item["shot_id"]))
        if key in prev_end:
            item["start"] = prev_end[key]
        prev_end[key] = str(item["end"])
        out.append(item)
    return out


def _enforce_clip_cap(config: dict, clips: list[dict], fps: int) -> None:
    sec = read_max_clip_sec(config)
    max_frames = max(_frame_floor(fps), int(round(sec * fps)))
    for clip in clips:
        frames = int(clip["frames"])
        if frames > max_frames:
            raise RuntimeError(f"WAN clip exceeds cap: {clip['shot_id']} frames={frames} cap={max_frames}")


def _wan_planner_batch_size(config: dict, count: int) -> int:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    raw = render.get("wan_planner_batch_size", 20) if isinstance(render, dict) else 20
    try:
        n = int(raw)
    except Exception:
        n = 20
    return max(1, min(max(1, count), n))


def _strict_id_match(config: dict) -> bool:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    raw = render.get("strict_prompt_id_match", True) if isinstance(render, dict) else True
    return parse_bool(raw, default=True)


def _carry_hint(rows: list[dict]) -> str:
    if not rows:
        return ""
    last = rows[-1]
    parts = [
        str(last.get("subject_motion", "")).strip(),
        str(last.get("camera_relation", "")).strip(),
        str(last.get("environment_detail", "")).strip(),
    ]
    return " | ".join(part for part in parts if part)[:120]


def _frame_floor(fps: int) -> int:
    return max(1, int(round(max(1, fps) * 0.25)))


def _clip_series_key(shot_id: str) -> str:
    return str(shot_id).split("_C", 1)[0]


def _apply_prompt(clip: dict, row: dict) -> dict:
    out = dict(clip)
    out["subject_motion"] = str(row["subject_motion"])
    out["camera_relation"] = str(row["camera_relation"])
    out["environment_detail"] = str(row["environment_detail"])
    out["positive_prompt"] = _compose_positive_prompt(row)
    out["negative_prompt"] = str(row["negative_prompt"])
    out["energy"] = _energy_policy(clip, str(row["energy"]))
    return out


def _compose_positive_prompt(row: dict) -> str:
    subject_motion = _sentence(_clause(row.get("subject_motion", "")))
    camera_relation = _compose_camera_sentence(
        _clause(row.get("camera_relation", "")),
        _clause(row.get("environment_detail", "")),
    )
    if not subject_motion or not camera_relation:
        raise RuntimeError("empty composed WAN prompt")
    return f"{subject_motion} {camera_relation}".strip()


def _clause(text: object) -> str:
    return " ".join(str(text).strip().rstrip(". ").split())


def _sentence(text: str) -> str:
    cleaned = str(text).strip().rstrip(". ")
    return f"{cleaned}." if cleaned else ""


def _compose_camera_sentence(camera_relation: str, environment_detail: str) -> str:
    if not camera_relation:
        return ""
    relation = _camera_clause(camera_relation)
    if environment_detail:
        return _sentence(f"{relation}, while {environment_detail}")
    return _sentence(relation)


def _camera_clause(text: str) -> str:
    low = text.lower()
    if low.startswith("the camera "):
        return text
    if low.startswith("camera "):
        return f"The {text}"
    return f"The camera {text}"


def _energy_policy(clip: dict, suggested: str) -> str:
    sec = _section_token(clip)
    label = _section_label(clip)
    if "final chorus" in label:
        return "high"
    if "chorus 2" in label:
        return "high" if suggested == "high" else "normal"
    if sec == "chorus" or sec.startswith("chorus_"):
        return "high" if suggested == "high" else "normal"
    if sec in {"bridge", "outro"}:
        return "low" if suggested == "low" else "normal"
    if suggested in {"low", "normal", "high"}:
        return suggested
    return "normal"


def _section_token(clip: dict) -> str:
    return str(clip.get("section_name", "")).strip().lower()


def _section_label(clip: dict) -> str:
    return str(clip.get("section_label", clip.get("section_name", ""))).strip().lower()
