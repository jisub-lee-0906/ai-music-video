from __future__ import annotations

from ai_mv.core.workflow_prompt_contracts import compact_prompt_clause, workflow_negative_prompt
from ai_mv.engines.common.clip_timing import read_max_clip_sec
from ai_mv.engines.visual_story_bible.brief_views import compact_section_atoms, compact_world_atoms
from ai_mv.utils.text_utils import parse_target

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
    return (
        "deterministic wan composer; "
        "compose short motion-first prompts for the workflow positive and negative text fields; "
        f"{carry_clause}hero={world['hero_identity']}; world={world['world_rules']}; clip_ids={clip_ids}; clips={summary}."
    )


def _route_to_clip(item: dict, ref_images: list[dict], fps: int) -> dict:
    ref_map = {_ref_chain_key(row): row for row in ref_images if isinstance(row, dict)}
    use_ref = bool(item.get("use_ref", False))
    ref_row = ref_map.get(_ref_chain_key(item))
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
        "start_frame": dict(item.get("start_frame", {})),
        "end_frame": dict(item.get("end_frame", {})),
        "kinetic_transition": str(item.get("kinetic_transition", "")),
        "lighting_fx": str(item.get("lighting_fx", "")),
        "kinetic_intensity": str(item.get("kinetic_intensity", "")),
        "route_reason": str(item.get("route_reason", "")),
        "use_ref": use_ref,
        "clip_index": int(item.get("clip_index", 1)),
        "clip_count": int(item.get("clip_count", 1)),
        "timeline_index": int(item.get("timeline_index", 0)),
        "chain_key": _ref_chain_key(item),
    }


def _chain_clip_starts(clips: list[dict]) -> list[dict]:
    out: list[dict] = []
    prev_end_path = ""
    prev_clip: dict | None = None
    for clip in clips:
        item = dict(clip)
        if prev_end_path and not _chain_break(item, prev_clip):
            item["start"] = prev_end_path
            item["start_source"] = "previous_end"
            item["prev_chain_key"] = str(prev_clip.get("chain_key", "")) if isinstance(prev_clip, dict) else ""
        else:
            item["start_source"] = "rendered_start"
            item["prev_chain_key"] = ""
        prev_end_path = str(item["end"])
        prev_clip = item
        out.append(item)
    return out


def _chain_break(clip: dict, prev_clip: dict | None) -> bool:
    if not isinstance(prev_clip, dict):
        return True
    if str(clip.get("kinetic_transition", "")).strip().lower() == "smash_reframe":
        return True
    if _starts_new_major_section(clip, prev_clip) and int(clip.get("clip_index", 1)) <= 1:
        return True
    return False


def _starts_new_major_section(clip: dict, prev_clip: dict) -> bool:
    current = _section_token(clip)
    previous = _section_token(prev_clip)
    if not current or current == previous:
        return False
    return _is_major_reset_section(current)


def _section_token(clip: dict) -> str:
    return str(clip.get("section_name", clip.get("section_label", ""))).strip().lower()


def _is_major_reset_section(section: str) -> bool:
    sec = str(section).strip().lower()
    return "verse" in sec or sec == "chorus"


def _ref_chain_key(row: dict) -> str:
    return f"{str(row.get('shot_id', '')).strip()}:{int(row.get('clip_index', 1))}"


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
    motion = str(clip.get("kinetic_transition", "")).strip() or str(clip.get("motion_hint", "")).strip() or "impact move"
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
    beat = str(section.get("story_beat", "")).strip() or str(clip.get("motion_hint", "")).strip() or "hits the beat"
    axis = _workflow_axis(section, clip)
    action = _action_fragment(beat, axis, clip)
    if phase == "establish":
        return _sentence_clause(_join_motion("She sets the move", action))
    if phase == "resolve":
        return _sentence_clause(_join_motion("She lands the move", action))
    if phase == "advance":
        return _sentence_clause(_join_motion("She carries the move", action))
    return _sentence_clause(_single_motion_sentence(action))


def _camera_relation(clip: dict, section: dict) -> str:
    camera = str(clip.get("camera_language", "")).strip()
    kinetic_transition = str(clip.get("kinetic_transition", "")).strip().lower()
    intensity = str(clip.get("kinetic_intensity", "")).strip().lower()
    escalation = str(section.get("escalation_level", "")).strip().lower()
    if camera:
        return compact_prompt_clause(camera, 12)
    if kinetic_transition == "whip_pan_left":
        return "whips hard left across her line"
    if kinetic_transition == "whip_pan_right":
        return "whips hard right across her line"
    if kinetic_transition == "snap_zoom_in":
        return "snap zooms straight into her face"
    if kinetic_transition == "snap_zoom_out":
        return "snaps back out of the frame"
    if kinetic_transition == "crash_push_in":
        return "crashes straight toward her on impact"
    if kinetic_transition == "smash_reframe":
        return "smash reframes to a new axis mid-beat"
    if kinetic_transition == "strobe_jump":
        return "jumps forward through strobe hits"
    if kinetic_transition == "match_cut_pose":
        return "cuts on pose impact without easing"
    if intensity in {"high", "max"}:
        return "drives fast with no soft drift"
    if escalation == "interrupt":
        return "cuts sideways and locks on impact"
    if escalation == "residue":
        return "jerks back and leaves a hard after-image"
    return "stays aggressive and close to impact"


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
    lighting_fx = str(clip.get("lighting_fx", "")).strip()
    text = ", ".join(part for part in (location, palette, lighting_fx or lighting or world_rules) if part)
    return compact_prompt_clause(text, 16)


def _negative_prompt(clip: dict, brief: dict) -> str:
    world = compact_world_atoms(brief)
    relation = str(clip.get("space_relation", "")).strip().lower()
    extra: list[str] = []
    if "glass" in relation:
        extra.append("warped reflections")
    if bool(clip.get("use_ref", False)):
        extra.append("identity drift")
    if "world_rules" in world and "night" in str(world.get("world_rules", "")).lower():
        extra.append("daylight mismatch")
    return workflow_negative_prompt(extra)


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


def _action_fragment(beat: str, axis: str, clip: dict) -> str:
    cleaned = _beat_fragment(beat)
    if cleaned:
        return cleaned
    kinetic_transition = str(clip.get("kinetic_transition", "")).strip().lower()
    if kinetic_transition == "snap_zoom_in":
        return "a sudden forward snap"
    if kinetic_transition == "snap_zoom_out":
        return "a violent pullback hit"
    if kinetic_transition in {"whip_pan_left", "whip_pan_right"}:
        return "a whip-fast directional break"
    if kinetic_transition == "crash_push_in":
        return "a full-speed impact push"
    if kinetic_transition == "smash_reframe":
        return "a hard reframing strike"
    if kinetic_transition == "strobe_jump":
        return "a strobe-synced jump cut burst"
    if kinetic_transition == "match_cut_pose":
        return "a pose-locked impact match cut"
    axis_low = str(axis).strip().lower()
    if axis_low == "travel line":
        return "a hard forward charge"
    if axis_low == "gaze shift":
        return "a fast eye-line snap"
    if axis_low == "stillness hold":
        return "a locked impact hold"
    return "a sharp body strike"


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
        "takes",
        "strikes",
        "stays",
        "slows",
        "passes",
        "checks",
        "steps",
        "turns",
        "moves",
        "advances",
        "surges",
        "repeats",
        "rises",
        "lifts",
        "pauses",
        "returns",
        "stands",
        "holds",
        "keeps",
        "remains",
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
        "takes": "taking",
        "strikes": "striking",
        "stays": "staying",
        "advances": "advancing",
        "surges": "surging",
        "repeats": "repeating",
        "rises": "rising",
        "lifts": "lifting",
        "keeps": "keeping",
        "remains": "remaining",
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
    dynamic = ("whip", "snap", "crash", "slam", "smash", "jump", "track", "tracks", "push", "pushes", "pull", "pulls", "glide", "glides")
    if not any(word in low for word in dynamic):
        return True
    weak_starts = ("a gentle retreat", "a steady retreat", "the glide", "the backward tracking", "the arc")
    return low.startswith(weak_starts)


def _kinetic_axis(clip: dict) -> str:
    transition = str(clip.get("kinetic_transition", "")).strip().lower()
    mapping = {
        "snap_zoom_in": "forward snap",
        "snap_zoom_out": "recoil pullback",
        "whip_pan_left": "left whip line",
        "whip_pan_right": "right whip line",
        "crash_push_in": "impact push",
        "smash_reframe": "reframe break",
        "strobe_jump": "strobe burst",
        "match_cut_pose": "pose impact",
    }
    return mapping.get(transition, "impact move")


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


def _workflow_axis(section: dict, clip: dict) -> str:
    raw = compact_prompt_clause(section.get("motion_axis", ""), 4)
    if raw and "," not in raw and "." not in raw:
        return raw
    return _kinetic_axis(clip)


def _join_motion(prefix: str, action: str) -> str:
    text = str(action).strip()
    if not text:
        return str(prefix).strip()
    first = text.split(" ", 1)[0].lower()
    if first in {"staying", "holding", "remaining", "keeping"}:
        linker = "while"
    elif first.endswith("ing"):
        linker = "by"
    elif first in {"under", "over", "through", "into", "across", "inside", "between", "before", "after", "while", "as"}:
        linker = "as"
    elif first in {"a", "an", "the"}:
        linker = "through"
    else:
        linker = "with"
    return f"{str(prefix).strip()} {linker} {text}".strip()


def _single_motion_sentence(action: str) -> str:
    text = str(action).strip()
    if not text:
        return "She holds the beat"
    first = text.split(" ", 1)[0].lower()
    if first in {"staying", "holding", "remaining", "keeping"}:
        lead_map = {
            "staying": "stays",
            "holding": "holds",
            "remaining": "remains",
            "keeping": "keeps",
        }
        rest = text.split(" ", 1)[1] if " " in text else ""
        return f"She {lead_map.get(first, first)} {rest}".strip()
    if first.endswith("ing"):
        return f"She follows through by {text}"
    if first in {"a", "an", "the"}:
        return f"She hits through {text}"
    return f"She {text}"
