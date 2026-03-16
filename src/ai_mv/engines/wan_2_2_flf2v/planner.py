from __future__ import annotations

from ai_mv.engines.common.clip_timing import read_max_clip_sec
from ai_mv.engines.visual_story_bible.brief_views import compact_section_atoms, compact_world_atoms
from ai_mv.utils.text_utils import parse_target

_BASE_NEGATIVE = (
    "overexposed, static frame, unclear details, subtitle, watermark, logo, "
    "low quality, jpeg artifacts, ugly, defective, extra fingers, poorly drawn hands, "
    "poorly drawn face, deformed anatomy, disfigured limbs, fused fingers, cluttered background"
)


def build_wan_plan(config: dict, payload: dict) -> dict:
    fps = parse_target(config["video"]["target"])[2]
    clips = [_route_to_clip(item, payload.get("flux2_ref_images", []), fps) for item in payload["clip_routes"]]
    clips = _chain_clip_starts(clips)
    if not clips:
        raise RuntimeError("WAN clips empty")
    _enforce_clip_cap(config, clips, fps)
    rendered = [_apply_prompt(clip, payload["visual_story_bible"]) for clip in clips]
    return {"clips": rendered}


def _planner_prompt(config: dict, payload: dict, clips: list[dict], carry: str) -> str:
    world = compact_world_atoms(payload["visual_story_bible"])
    clip_ids = _clip_ids(clips)
    summary = _clip_summary(clips)
    carry_clause = f"carry={carry}; " if carry else ""
    payoff = " Final Chorus should feel like the motion payoff." if any("final chorus" in str(clip.get("section_label", "")).lower() for clip in clips) else ""
    return f"deterministic wan composer; {carry_clause}hero={world['hero_identity']}; world={world['world_rules']}; clip_ids={clip_ids}; clips={summary}.{payoff}"


def _route_to_clip(item: dict, ref_images: list[dict], fps: int) -> dict:
    ref_map = {str(row.get("shot_id", "")): row for row in ref_images if isinstance(row, dict)}
    use_ref = bool(item.get("use_ref", False))
    ref_row = ref_map.get(str(item["shot_id"]))
    start = str(item["anchor"])
    end = str(item["anchor"])
    if use_ref:
        if ref_row is None:
            raise RuntimeError(f"WAN missing ref-assisted clip: {item['shot_id']}")
        start = str(ref_row["start"])
        end = str(ref_row["end"])
    frames = max(_frame_floor(fps), int(round(float(item["duration_sec"]) * fps)))
    return {
        "shot_id": str(item["shot_id"]),
        "start": start,
        "end": end,
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
        "route_reason": str(item.get("route_reason", "")),
        "use_ref": use_ref,
        "clip_index": int(item.get("clip_index", 1)),
        "clip_count": int(item.get("clip_count", 1)),
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


def _carry_hint(rows: list[dict]) -> str:
    if not rows:
        return ""
    last = rows[-1]
    return " | ".join(
        part
        for part in (
            str(last.get("subject_motion", "")).strip(),
            str(last.get("camera_relation", "")).strip(),
            str(last.get("environment_detail", "")).strip(),
        )
        if part
    )[:120]


def _clip_ids(clips: list[dict]) -> str:
    ids = [str(clip["shot_id"]) for clip in clips]
    if not ids:
        raise RuntimeError("WAN clips missing for planner prompt")
    return ", ".join(ids)


def _clip_summary(clips: list[dict]) -> str:
    return ", ".join(_clip_summary_row(c) for c in clips)


def _clip_summary_row(clip: dict) -> str:
    sid = str(clip["shot_id"])
    relation = str(clip.get("space_relation", "")).strip() or "space stays stable"
    motion = str(clip.get("motion_hint", "")).strip() or "steady motion"
    label = str(clip.get("section_label", clip.get("section_name", "section")))
    return f"{sid}({label}|{motion}|{relation})"


def _apply_prompt(clip: dict, brief: dict) -> dict:
    section = _beat_atoms(brief, clip)
    subject_motion = _subject_motion(clip, section)
    camera_relation = _camera_relation(clip, section)
    environment_detail = _environment_detail(clip, section, brief)
    row = {
        "subject_motion": subject_motion,
        "camera_relation": camera_relation,
        "environment_detail": environment_detail,
        "negative_prompt": _negative_prompt(clip, brief),
        "energy": _energy_policy(clip, _suggested_energy(clip, section)),
    }
    out = dict(clip)
    out["subject_motion"] = row["subject_motion"]
    out["camera_relation"] = row["camera_relation"]
    out["environment_detail"] = row["environment_detail"]
    out["positive_prompt"] = _compose_positive_prompt(row)
    out["negative_prompt"] = row["negative_prompt"]
    out["energy"] = row["energy"]
    return out


def _subject_motion(clip: dict, section: dict) -> str:
    phase = _clip_phase(clip)
    beat = str(section.get("story_beat", "")).strip() or str(clip.get("motion_hint", "")).strip() or "holds the beat"
    axis = str(section.get("motion_axis", "")).strip() or "pose shift"
    action = _action_fragment(beat, axis)
    if phase == "establish":
        return _sentence_clause(f"She sets the {axis} with {action}")
    if phase == "resolve":
        return _sentence_clause(f"She lands the {axis} with {action}")
    if phase == "advance":
        return _sentence_clause(f"She carries the {axis} forward with {action}")
    return _sentence_clause(f"She moves through {action}")


def _camera_relation(clip: dict, section: dict) -> str:
    camera = str(clip.get("camera_language", "")).strip()
    escalation = str(section.get("escalation_level", "")).strip().lower()
    if camera:
        return _trim_words(camera, 12)
    if escalation == "interrupt":
        return "holds a restrained lateral relation"
    if escalation == "residue":
        return "glides back and leaves space behind her"
    return "glides without breaking alignment"


def _environment_detail(clip: dict, section: dict, brief: dict) -> str:
    palette = str(section.get("palette_hint", "")).strip()
    lighting = str(section.get("lighting_hint", "")).strip()
    location = (
        str(section.get("location_family", "")).strip()
        or str(section.get("location_anchor", "")).strip()
        or str(clip.get("scene_detail", "")).strip()
    )
    world = compact_world_atoms(brief)
    world_rules = str(world.get("world_rules", "")).strip()
    text = ", ".join(part for part in (location, palette, lighting or world_rules) if part)
    return _trim_words(text, 16)


def _negative_prompt(clip: dict, brief: dict) -> str:
    world = compact_world_atoms(brief)
    relation = str(clip.get("space_relation", "")).strip().lower()
    extra = []
    if "glass" in relation:
        extra.append("warped reflections")
    if bool(clip.get("use_ref", False)):
        extra.append("identity drift")
    if "world_rules" in world and "night" in str(world.get("world_rules", "")).lower():
        extra.append("daylight mismatch")
    combined = ", ".join(part for part in (_BASE_NEGATIVE, ", ".join(extra)) if part).strip(", ")
    return combined


def _suggested_energy(clip: dict, section: dict) -> str:
    escalation = str(section.get("escalation_level", "")).strip().lower()
    if escalation == "payoff":
        return "high"
    if escalation in {"interrupt", "residue"}:
        return "low"
    return "normal"


def _compose_positive_prompt(row: dict) -> str:
    subject_motion = _sentence(_clause(row.get("subject_motion", "")))
    second_sentence = _compose_second_sentence(
        _clause(row.get("camera_relation", "")),
        _clause(row.get("environment_detail", "")),
    )
    if not subject_motion or not second_sentence:
        raise RuntimeError("empty composed WAN prompt")
    return f"{subject_motion} {second_sentence}".strip()


def _clause(text: object) -> str:
    return " ".join(str(text).strip().rstrip(". ").split())


def _sentence(text: str) -> str:
    cleaned = str(text).strip().rstrip(". ")
    if not cleaned:
        return ""
    return f"{_capitalize_first(cleaned)}."


def _sentence_clause(text: str) -> str:
    cleaned = " ".join(str(text).strip().split())
    if cleaned.lower().startswith("she she "):
        cleaned = cleaned[4:]
    return cleaned


def _action_fragment(beat: str, axis: str) -> str:
    cleaned = _beat_fragment(beat)
    if cleaned:
        return cleaned
    axis_low = str(axis).strip().lower()
    if axis_low == "travel line":
        return "a measured forward drift"
    if axis_low == "gaze shift":
        return "a direct lift of her gaze"
    if axis_low == "stillness hold":
        return "a controlled held pause"
    return "a clear body adjustment"


def _beat_fragment(beat: str) -> str:
    cleaned = " ".join(str(beat).strip().rstrip(". ").split())
    if not cleaned:
        return ""
    low = cleaned.lower()
    prefixes = (
        "she ",
        "the heroine ",
        "our heroine ",
    )
    for prefix in prefixes:
        if low.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            low = cleaned.lower()
            break
    if low.startswith("lets "):
        return _gerund_phrase(cleaned)
    first = cleaned.split(" ", 1)[0].lower() if cleaned else ""
    if first in {
        "slows",
        "passes",
        "checks",
        "steps",
        "turns",
        "moves",
        "pauses",
        "returns",
        "stands",
        "holds",
        "eases",
        "glances",
        "lingers",
        "walks",
    }:
        return _gerund_phrase(cleaned)
    return cleaned[:1].lower() + cleaned[1:]


def _gerund_phrase(text: str) -> str:
    cleaned = " ".join(str(text).strip().split())
    if not cleaned:
        return ""
    parts = cleaned.split(" ", 1)
    verb = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    irregular = {
        "slows": "slowing",
        "passes": "passing",
        "checks": "checking",
        "steps": "stepping",
        "turns": "turning",
        "moves": "moving",
        "pauses": "pausing",
        "returns": "returning",
        "stands": "standing",
        "holds": "holding",
        "eases": "easing",
        "glances": "glancing",
        "lingers": "lingering",
        "walks": "walking",
        "lets": "letting",
    }
    lead = irregular.get(verb.lower(), verb.lower())
    return f"{lead} {rest}".strip()


def _compose_second_sentence(camera_relation: str, environment_detail: str) -> str:
    if environment_detail and _camera_relation_is_weak(camera_relation):
        return _sentence(environment_detail)
    if not camera_relation:
        return ""
    relation = _clean_relation(camera_relation)
    if environment_detail:
        return _sentence(f"{relation}, while {_lowercase_first(environment_detail)}")
    return _sentence(relation)


def _clean_relation(text: str) -> str:
    cleaned = str(text).strip()
    if not cleaned:
        return ""
    cleaned = _naturalize_relation(cleaned)
    low = cleaned.lower()
    if low.startswith("the camera "):
        return cleaned
    if low.startswith("camera "):
        return cleaned
    return _capitalize_first(cleaned)


def _capitalize_first(text: str) -> str:
    cleaned = str(text)
    if not cleaned:
        return ""
    return cleaned[:1].upper() + cleaned[1:]


def _lowercase_first(text: str) -> str:
    cleaned = str(text).strip()
    if not cleaned:
        return ""
    return cleaned[:1].lower() + cleaned[1:]


def _camera_relation_is_weak(text: str) -> bool:
    low = str(text).strip().lower()
    if not low:
        return True
    technical_subjects = (
        "the frame ",
        "the track ",
        "the side track ",
        "the follow ",
    )
    if low.startswith(technical_subjects):
        return True
    dynamic = ("glide", "glides", "follow", "follows", "track", "tracks", "push", "pushes", "pull", "pulls", "drift", "drifts")
    if not any(word in low for word in dynamic):
        return True
    weak_starts = ("a gentle retreat", "a steady retreat", "the glide", "the backward tracking", "the arc")
    return low.startswith(weak_starts)


def _naturalize_relation(text: str) -> str:
    cleaned = " ".join(str(text).strip().split())
    replacements = (
        ("keeps her centered", "stays centered on her"),
        ("keeps close to her", "stays close to her"),
        ("keeps her aligned", "stays aligned with her"),
        ("gives her space", "gives her a little space"),
        ("stays before her", "stays just ahead of her"),
        ("stays before her.", "stays just ahead of her."),
    )
    out = cleaned
    low = out.lower()
    for source, target in replacements:
        src_low = source.lower()
        if src_low in low:
            idx = low.index(src_low)
            out = out[:idx] + target + out[idx + len(source) :]
            low = out.lower()
    return out


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


def _clip_phase_from_id(shot_id: str) -> str:
    if "_C" not in shot_id:
        return "single"
    try:
        suffix = int(shot_id.rsplit("_C", 1)[1])
    except Exception:
        return "single"
    if suffix <= 1:
        return "establish"
    return "advance"


def _clip_phase(clip: dict) -> str:
    count = int(clip.get("clip_count", 1))
    index = int(clip.get("clip_index", 1))
    if count <= 1:
        return "single"
    if index <= 1:
        return "establish"
    if index >= count:
        return "resolve"
    return "advance"


def _frame_floor(fps: int) -> int:
    return max(1, int(round(max(1, fps) * 0.25)))


def _clip_series_key(shot_id: str) -> str:
    return str(shot_id).split("_C", 1)[0]


def _trim_words(text: str, max_words: int) -> str:
    words = [word for word in str(text).replace(",", " ,").split() if word]
    return " ".join(words[: max_words]).replace(" ,", ",").strip(" ,")


def _beat_atoms(brief: dict, clip: dict) -> dict:
    beat_id = str(clip.get("lyric_beat_id", "")).strip()
    if beat_id:
        for beat in brief.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            if str(beat.get("beat_id", "")).strip() == beat_id:
                return dict(beat)
    return compact_section_atoms(brief, str(clip.get("section_name", "")))
