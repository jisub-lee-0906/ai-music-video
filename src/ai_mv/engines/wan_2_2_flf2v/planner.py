from __future__ import annotations

from ai_mv.core.workflow_prompt_contracts import clean_prompt_clause, workflow_negative_prompt
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
    clip_ids = _clip_ids(clips)
    summary = _clip_summary(clips)
    return (
        "deterministic wan composer; "
        "compose short motion-first prompts for the workflow positive and negative text fields; "
        "positive prompt formula: camera movement + action verbs + background motion; "
        "negative prompt formula: 3d or realism anti-tags + morphing or anatomy error anti-tags + unwanted motion anti-tags; "
        "do not restate visual style in the positive prompt; "
        f"clip_ids={clip_ids}; clips={summary}."
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
        "workflow_motion_clause": str(item.get("workflow_motion_clause", "")),
        "space_relation": str(item.get("space_relation", "")),
        "start_frame": dict(item.get("start_frame", {})),
        "end_frame": dict(item.get("end_frame", {})),
        "kinetic_transition": str(item.get("kinetic_transition", "")),
        "lighting_fx": str(item.get("lighting_fx", "")),
        "kinetic_intensity": str(item.get("kinetic_intensity", "")),
        "location_family": str(item.get("location_family", "")),
        "symbolic_image": str(item.get("symbolic_image", "")),
        "motif_object": str(item.get("motif_object", "")),
        "edit_device": str(item.get("edit_device", "")),
        "prompt_focus": str(item.get("prompt_focus", "")),
        "space_event": str(item.get("space_event", "")),
        "composition_shape": str(item.get("composition_shape", "")),
        "palette_mode": str(item.get("palette_mode", "")),
        "character_render_mode": str(item.get("character_render_mode", "")),
        "face_exposure_level": str(item.get("face_exposure_level", "")),
        "heroine_visibility": str(item.get("heroine_visibility", "")),
        "continuity_priority": str(item.get("continuity_priority", "")),
        "wardrobe_read": str(item.get("wardrobe_read", "")),
        "continuity_lock": str(item.get("continuity_lock", "")),
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
    focus = str(clip.get("prompt_focus", "")).strip().lower() or "heroine"
    motion = str(clip.get("kinetic_transition", "")).strip() or str(clip.get("motion_hint", "")).strip() or "impact move"
    camera = clean_prompt_clause(str(clip.get("camera_language", "")).strip()) or "camera move"
    bg = clean_prompt_clause(str(clip.get("space_event", "")).strip() or str(clip.get("scene_detail", "")).strip()) or "background motion"
    return f"{sid}({focus}|{motion}|{camera}|{bg})"


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
    action = _planned_motion_clause(clip)
    if action:
        return _sentence_clause(action)
    motion = clean_prompt_clause(str(clip.get("motion_hint", "")).strip())
    if motion:
        return _sentence_clause(motion)
    return "holds the motion"


def _camera_relation(clip: dict, section: dict) -> str:
    camera = str(clip.get("camera_language", "")).strip()
    kinetic_transition = str(clip.get("kinetic_transition", "")).strip().lower()
    intensity = str(clip.get("kinetic_intensity", "")).strip().lower()
    if kinetic_transition == "whip_pan_left":
        return "Camera whips hard left"
    if kinetic_transition == "whip_pan_right":
        return "Camera whips hard right"
    if kinetic_transition == "snap_zoom_in":
        return "Camera snap-zooms in"
    if kinetic_transition == "snap_zoom_out":
        return "Camera snaps back out"
    if kinetic_transition == "crash_push_in":
        return "Camera crashes forward on impact"
    if kinetic_transition == "smash_reframe":
        return "Camera smash-reframes to a new axis"
    if kinetic_transition == "strobe_jump":
        return "Camera jumps forward on the beat"
    if kinetic_transition == "match_cut_pose":
        return "Camera holds the angle and cuts on pose impact"
    if camera:
        return _simple_camera_motion(camera)
    if intensity in {"high", "max"}:
        return "Camera drives fast with no soft drift"
    return "Camera holds the frame"


def _environment_detail(clip: dict, section: dict, brief: dict) -> str:
    scene_event = str(clip.get("space_event", "")).strip()
    scene_detail = str(clip.get("scene_detail", "")).strip()
    if scene_event:
        return clean_prompt_clause(scene_event)
    if scene_detail:
        return clean_prompt_clause(scene_detail)
    location = (
        str(clip.get("location_family", "")).strip()
        or str(section.get("location_family", "")).strip()
        or str(section.get("location_anchor", "")).strip()
    )
    location_text = clean_prompt_clause(location)
    if location_text:
        return f"The {location_text} moves in the background"
    return "Background planes move behind the action"


def _negative_prompt(clip: dict, brief: dict) -> str:
    world = compact_world_atoms(brief)
    relation = str(clip.get("space_relation", "")).strip().lower()
    extra: list[str] = []
    extra.extend(
        [
            "3d render",
            "photorealistic",
            "volumetric lighting",
            "soft shading",
            "morphing",
            "melting limbs",
            "warping limbs",
            "melted guitar shape",
            "slow motion",
            "smooth transitions",
        ]
    )
    if "glass" in relation:
        extra.append("warped reflections")
    if bool(clip.get("use_ref", False)):
        extra.append("identity drift")
    if str(clip.get("prompt_focus", "")).strip().lower() in {"object", "space", "graphic"}:
        extra.extend(
            [
                "generic live-action portrait",
                "photorealistic skin texture",
                "photographic background depth",
                "realistic architecture detail",
                "soft atmospheric bloom",
            ]
        )
    if str(clip.get("face_exposure_level", "")).strip().lower() in {"direct", "soft"}:
        extra.extend(["different person", "age drift", "hairstyle drift", "wardrobe swap", "duplicate subject"])
    if str(clip.get("camera_language", "")).strip().lower() in {"locked", "lockoff", "static"}:
        extra.extend(["camera movement", "zooming", "panning"])
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
    camera_motion = _sentence(_clause(row.get("camera_relation", "")))
    subject_motion = _sentence(_naturalize_wan_action(_clause(row.get("subject_motion", "")), row))
    background_motion = _sentence(_clause(row.get("environment_detail", "")))
    if not camera_motion or not subject_motion or not background_motion:
        raise RuntimeError("empty composed WAN prompt")
    return f"{camera_motion} {subject_motion} {background_motion}".strip()


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


def _simple_camera_motion(camera: str) -> str:
    low = str(camera).strip().lower()
    if not low:
        return "Camera holds the frame"
    if "locked" in low or "lockoff" in low or "static" in low:
        return "Camera stays completely locked off"
    if "tracking" in low or "track" in low or "follow" in low:
        return "Camera tracks with the action"
    if "side-on" in low or "profile" in low:
        return "Camera tracks from the side"
    if "low" in low:
        return "Camera stays low and aggressive"
    if "close" in low or "tight" in low:
        return "Camera pushes in close"
    if "wide" in low:
        return "Camera holds a wide moving frame"
    return "Camera stays with the motion"


def _naturalize_wan_action(text: str, clip: dict) -> str:
    cleaned = clean_prompt_clause(text)
    if not cleaned:
        return "The figure moves through the beat"
    low = cleaned.lower()
    subject = "The girl"
    focus = str(clip.get("prompt_focus", "")).strip().lower()
    if focus == "object":
        subject = "The object"
    elif focus == "space":
        subject = "The figure"
    elif focus == "graphic":
        subject = "The graphic figure"
    if low.startswith(subject.lower()):
        return cleaned
    if low.startswith(("she ", "the girl ", "the figure ", "the object ", "the graphic figure ")):
        return cleaned[:1].upper() + cleaned[1:]
    return f"{subject} {cleaned}"


def _capitalize_first(text: str) -> str:
    cleaned = str(text)
    if not cleaned:
        return ""
    return cleaned[:1].upper() + cleaned[1:]


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


def _beat_atoms(brief: dict, clip: dict) -> dict:
    beat_id = str(clip.get("lyric_beat_id", "")).strip()
    if beat_id:
        for beat in brief.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            if str(beat.get("beat_id", "")).strip() == beat_id:
                return dict(beat)
    return compact_section_atoms(brief, str(clip.get("section_name", "")), beat_id)
def _planned_motion_clause(clip: dict) -> str:
    text = " ".join(str(clip.get("workflow_motion_clause", "")).strip().rstrip(". ").split())
    if not text:
        raise RuntimeError(f"workflow_motion_clause missing for wan shot: {clip.get('shot_id', '')}")
    if text.lower().startswith("she "):
        text = text[4:].strip()
    return text
